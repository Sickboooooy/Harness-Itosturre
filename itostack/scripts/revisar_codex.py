#!/usr/bin/env python3
"""Revisor y juez de otra familia de modelos con Codex CLI (OpenAI).

Sirve a /interrogar (rol adversarial) y al juez de evals (rol juez), con el mismo contrato de salida que
revisar_ollama.py. Uso:
  revisar_codex.py --archivo escrito.md [--rubrica rubrica.md] [--rol adversarial|juez] [--modelo M] [--esfuerzo E]
  git diff | revisar_codex.py --rol adversarial

Salida: JSON en stdout. Código: 0 aprobado · 1 no aprobado · 2 BLOCKED (Codex no respondió, salida inválida, material
demasiado grande, cobertura incompleta de la rúbrica o nada que calificar) · 3 configuración rechazada.

Reglas (falla cerrado):
- Privacidad (principio privacidad-local): el texto sale a OpenAI. Solo corre con "entorno": "desarrollo" en
  .itostack/config.json; sin ese valor se niega.
- Codex es un agente, no solo un modelo: corre sin herramientas (shell, navegador, apps y plugins desactivados), con
  sandbox de solo lectura, sin sesión persistida y desde un directorio vacío de nombre neutro. Así no puede leer
  soluciones de referencia, casos holdout ni rutas que delaten un examen. Los artefactos van dentro del mensaje,
  numerados, sin su ruta.
- Modelo y esfuerzo fijos desde modelos.json, con la configuración del usuario ignorada: el juez de desarrollo y el
  de holdout son el mismo, y el veredicto registra cuál fue, junto con las huellas de lo que calificó.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nucleo import config as cfg  # noqa: E402
from nucleo import juez  # noqa: E402

LIMITE_CARACTERES = 150_000
# Sin herramientas el juez solo ve el mensaje. El sandbox de solo lectura impide escribir, no leer.
HERRAMIENTAS_DESACTIVADAS = ("shell_tool", "browser_use", "browser_use_external", "computer_use", "in_app_browser", "apps", "plugins")


def ejecutable_codex() -> list[str] | None:
    """Comando base de Codex. En Windows se prefiere codex.exe: pasar argumentos por codex.cmd los expone a cmd.exe."""
    propio = os.environ.get("ITOSTACK_CODEX")
    if propio:
        return [sys.executable, propio] if propio.endswith(".py") else [propio]
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        nativos = sorted(glob.glob(os.path.join(os.environ["LOCALAPPDATA"], "OpenAI", "Codex", "bin", "*", "codex.exe")), key=os.path.getmtime, reverse=True)
        if nativos:
            return [nativos[0]]
    encontrado = shutil.which("codex")
    return [encontrado] if encontrado else None


def version(base: list[str]) -> str:
    try:
        salida = subprocess.run([*base, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return "desconocida"
    return (salida.stdout or salida.stderr).strip() or "desconocida"


def configuracion_juez(modelos: dict, modelo: str | None, esfuerzo: str | None) -> tuple[str | None, str]:
    seccion = modelos.get("codex") or {}
    designado = modelos.get("juez_otra_familia") or ""
    modelo = modelo or seccion.get("modelo") or (designado.split(":", 1)[1] if designado.startswith("codex:") else None)
    return modelo, esfuerzo or seccion.get("esfuerzo") or "high"


def comando(base: list[str], neutro: Path, modelo: str, esfuerzo: str, esquema: Path, salida: Path) -> list[str]:
    desactivar = [opcion for nombre in HERRAMIENTAS_DESACTIVADAS for opcion in ("--disable", nombre)]
    return [
        *base, "exec",
        "-C", str(neutro),
        "-s", "read-only",
        "--skip-git-repo-check",
        "--ephemeral",
        "--ignore-user-config",
        *desactivar,
        "--color", "never",
        "-m", modelo,
        "-c", f"model_reasoning_effort={esfuerzo}",
        "--output-schema", str(esquema),
        "-o", str(salida),
        "-",
    ]


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("--archivo", type=Path, action="append", default=[])
    analizador.add_argument("--rubrica", type=Path)
    analizador.add_argument("--rol", choices=sorted(juez.INSTRUCCIONES), default="adversarial")
    analizador.add_argument("--modelo", help="por omisión, codex.modelo de modelos.json")
    analizador.add_argument("--esfuerzo", help="model_reasoning_effort; por omisión, codex.esfuerzo de modelos.json")
    analizador.add_argument("--tiempo", type=int, default=1800, help="segundos máximos de la corrida")
    analizador.add_argument("--caso", help="caso de eval que se califica (skill.caso); la compuerta exige uno por caso holdout")
    args = analizador.parse_args()

    proyecto = cfg.raiz_proyecto()
    config = cfg.cargar(proyecto)
    if config.get("entorno") != "desarrollo":
        print(
            f"Codex envía el texto a OpenAI y este proyecto está en entorno «{config.get('entorno')}». Solo se permite "
            "con \"entorno\": \"desarrollo\" en .itostack/config.json (principio privacidad-local). En producción usa "
            "revisar_ollama.py.",
            file=sys.stderr,
        )
        return 3
    modelo, esfuerzo = configuracion_juez(juez.cargar_modelos(proyecto), args.modelo, args.esfuerzo)
    if not modelo:
        print("Falta el modelo: define codex.modelo en .itostack/modelos.json o pasa --modelo.", file=sys.stderr)
        return 3
    if juez.es_familia_claude(modelo):
        print("El revisor debe ser de otra familia de modelos que Claude: el sentido es un punto de vista distinto del trabajador.", file=sys.stderr)
        return 3
    if args.rol == "juez" and not args.rubrica:
        print("El rol juez exige --rubrica: sin rúbrica congelada no hay contra qué calificar.", file=sys.stderr)
        return 3
    base = ejecutable_codex()
    if not base:
        print("No se encontró Codex CLI (npm install -g @openai/codex, o la app de Codex).", file=sys.stderr)
        return 2

    entrada = "" if args.archivo else sys.stdin.read()
    artefactos, huellas = juez.instantanea(args.archivo, entrada)
    if not artefactos.strip():
        print("No hay nada que revisar: pasa --archivo o el texto por la entrada estándar.", file=sys.stderr)
        return 3
    rubrica_bytes = args.rubrica.read_bytes() if args.rubrica else None
    rubrica = rubrica_bytes.decode("utf-8") if rubrica_bytes is not None else None
    esperados = len(juez.criterios_de_rubrica(rubrica)) if rubrica is not None else None
    if args.rol == "juez" and not esperados:
        print("La rúbrica no tiene criterios numerados («1. …»): no hay cobertura que exigir.", file=sys.stderr)
        return 3
    try:
        prompt = juez.armar_prompt(args.rol, artefactos, rubrica, LIMITE_CARACTERES)
    except juez.MaterialExcedido as error:
        print(f"BLOCKED: {error}. Un recorte silencioso dejaría material sin revisar.", file=sys.stderr)
        return 2

    neutro = Path(tempfile.mkdtemp(prefix="trabajo-"))
    control = Path(tempfile.mkdtemp(prefix="ctl-"))
    try:
        esquema = control / "esquema.json"
        esquema.write_text(json.dumps(juez.ESQUEMAS[args.rol], ensure_ascii=False), encoding="utf-8")
        salida = control / "respuesta.json"
        try:
            corrida = subprocess.run(comando(base, neutro, modelo, esfuerzo, esquema, salida), input=prompt, capture_output=True,
                                     text=True, encoding="utf-8", errors="replace", timeout=args.tiempo, cwd=neutro)
        except subprocess.TimeoutExpired:
            print(f"Codex no terminó en {args.tiempo} s: BLOCKED.", file=sys.stderr)
            return 2
        try:
            resultado = json.loads(salida.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cola = (corrida.stderr or corrida.stdout or "").strip()[-1500:]
            print(f"Codex no devolvió una respuesta válida (código {corrida.returncode}): BLOCKED.\n{cola}", file=sys.stderr)
            return 2
    finally:
        shutil.rmtree(neutro, ignore_errors=True)
        shutil.rmtree(control, ignore_errors=True)

    contrato = juez.errores_contrato(args.rol, resultado)
    if contrato:
        print("La respuesta de Codex no cumple el contrato: BLOCKED.\n  " + "\n  ".join(contrato[:10]), file=sys.stderr)
        return 2
    if args.rol == "juez":
        resultado = juez.calificar(resultado, esperados, artefactos)
    resultado["juez"] = {"familia": "openai", "herramienta": "codex", "modelo": modelo, "esfuerzo": esfuerzo, "version": version(base), "rol": args.rol}
    resultado["material"] = juez.material(huellas, rubrica_bytes, args.caso)
    juez.anotar_bitacora(proyecto, resultado)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return juez.codigo_salida(args.rol, resultado)


if __name__ == "__main__":
    sys.exit(principal())
