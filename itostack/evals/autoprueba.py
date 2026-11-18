#!/usr/bin/env python3
"""Autoprueba de la suite de evals («la eval de la eval»), sin gastar tokens.

Para cada caso con `referencia.sh`:
  1. Prepara un espacio aislado con el mismo `preparar.sh` que usa `claude plugin eval --scaffold`.
  2. Ejecuta la solución de referencia: debe obtener 1.0 en los graders evaluables localmente.
  3. Si existe `referencia_rota.sh` (un agente que no verifica), debe REPROBAR (< 1.0).
Graders evaluables aquí: regex (last_message, trace, files, archivo) y file_exists; tool_used se aproxima
sobre la traza de bash -x; llm, baseline y tool_order se omiten (requieren un agente real).

Uso: autoprueba.py [--caso GLOB] [--conservar] [--verboso]
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("autoprueba requiere PyYAML: pip install pyyaml (en Ubuntu: sudo apt install python3-yaml)")

EVALS = Path(__file__).resolve().parent
PLUGIN = EVALS.parent
BANDERAS = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL}


@dataclass
class Calificacion:
    puntaje: float
    detalle: list[tuple[str, str]]


def _texto(ruta: Path) -> str | None:
    try:
        return ruta.read_text(encoding="utf-8", errors="replace")
    except (FileNotFoundError, IsADirectoryError):
        return None


def _archivos_texto(espacio: Path) -> str:
    partes = []
    for ruta in espacio.rglob("*"):
        if ".git" in ruta.parts or "evidencia" in ruta.parts or not ruta.is_file() or ruta.stat().st_size > 2_000_000:
            continue
        if ruta.suffix.lower() in {".png", ".db", ".pyc"}:
            continue
        partes.append(_texto(ruta) or "")
    return "\n".join(partes)


def _objetivo(grader: dict, espacio: Path, mensaje: str, traza: str, clave: str = "target") -> str | None:
    objetivo = grader.get(clave, "last_message")
    if isinstance(objetivo, dict):
        return _texto(espacio / objetivo["path"])
    return {"last_message": mensaje, "trace": traza, "files": _archivos_texto(espacio)}.get(objetivo, "")


def calificar(graders: list[dict], espacio: Path, mensaje: str, traza: str) -> Calificacion:
    total = obtenido = 0.0
    detalle: list[tuple[str, str]] = []
    comandos = [l[l.index("+") + 1:].strip() for l in traza.splitlines() if l.lstrip().startswith("+")]
    for grader in graders:
        tipo, peso, nombre = grader["type"], float(grader.get("weight", 1)), grader["name"]
        if tipo == "regex":
            texto = _objetivo(grader, espacio, mensaje, traza)
            if texto is None:
                ok = False
            else:
                banderas = 0
                for letra in grader.get("flags", ""):
                    banderas |= BANDERAS.get(letra, 0)
                coincidencias = len(re.findall(grader["pattern"], texto, banderas))
                modo = grader.get("match", "contains")
                ok = coincidencias > 0 if modo == "contains" else coincidencias == 0 if modo == "not_contains" else coincidencias == int(modo.split(":")[1])
        elif tipo == "file_exists":
            existe = (espacio / grader["path"]).exists()
            ok = existe == grader.get("exists", True)
        elif tipo == "tool_used" and grader.get("tool") == "Bash":
            patron = grader.get("input_match") or "."
            usos = sum(1 for c in comandos if re.search(patron, c))
            ok = usos >= grader.get("min", 1) and (grader.get("max") is None or usos <= grader["max"])
        else:
            detalle.append((nombre, "omitido (requiere agente)"))
            continue
        total += peso
        obtenido += peso if ok else 0
        detalle.append((nombre, "✔" if ok else "✘"))
    return Calificacion(obtenido / total if total else 1.0, detalle)


def ejecutar(caso_dir: Path, script: str, conservar: bool) -> tuple[Calificacion, Path]:
    datos = yaml.safe_load((caso_dir / "case.yaml").read_text(encoding="utf-8"))
    espacio = Path(tempfile.mkdtemp(prefix="ws-"))
    entorno = {k: v for k, v in os.environ.items() if not k.startswith("ITOSTACK_")}
    andamiaje = datos.get("context", {}).get("scaffold_script")
    if andamiaje:
        subprocess.run(["bash", str(caso_dir / andamiaje)], cwd=espacio, env=entorno, check=True, capture_output=True, text=True)
    mensaje_ruta = espacio.parent / f"{espacio.name}.mensaje"
    entorno.update({"PLUGIN": str(PLUGIN), "MENSAJE": str(mensaje_ruta)})
    proceso = subprocess.run(["bash", "-x", str(caso_dir / script)], cwd=espacio, env=entorno, capture_output=True, text=True, timeout=900)
    traza = proceso.stdout + "\n" + proceso.stderr
    mensaje = _texto(mensaje_ruta) or ""
    calificacion = calificar(datos["graders"], espacio, mensaje, traza)
    if not conservar:
        shutil.rmtree(espacio, ignore_errors=True)
        mensaje_ruta.unlink(missing_ok=True)
    return calificacion, espacio


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("--caso", default="*", help="filtro glob sobre skill/caso, p. ej. 'verificar-cita/*'")
    analizador.add_argument("--conservar", action="store_true")
    analizador.add_argument("--verboso", action="store_true")
    args = analizador.parse_args()

    casos = sorted(p.parent for p in EVALS.glob("*/*/case.yaml") if not p.parent.parent.name.startswith(("_", "fixtures", "results")))
    casos = [c for c in casos if fnmatch.fnmatch(f"{c.parent.name}/{c.name}", args.caso)]
    fallas = 0
    print(f"{'CASO':<52} {'REFERENCIA':>10} {'ROTA':>8}")
    for caso in casos:
        etiqueta = f"{caso.parent.name}/{caso.name}"
        if not (caso / "referencia.sh").is_file():
            print(f"{etiqueta:<52} {'sin ref.':>10}")
            continue
        referencia, espacio = ejecutar(caso, "referencia.sh", args.conservar)
        rota_txt = "—"
        rota = None
        if (caso / "referencia_rota.sh").is_file():
            rota, _ = ejecutar(caso, "referencia_rota.sh", False)
            rota_txt = f"{rota.puntaje:.2f}"
        ok = referencia.puntaje == 1.0 and (rota is None or rota.puntaje < 1.0)
        fallas += 0 if ok else 1
        print(f"{etiqueta:<52} {referencia.puntaje:>10.2f} {rota_txt:>8}  {'OK' if ok else '✘ REVISAR'}")
        if args.verboso or not ok:
            for nombre, estado in referencia.detalle:
                print(f"    ref  {estado:<28} {nombre}")
            if rota:
                for nombre, estado in rota.detalle:
                    print(f"    rota {estado:<28} {nombre}")
            if args.conservar:
                print(f"    espacio conservado: {espacio}")
    print(f"\nautoprueba: {len(casos) - fallas}/{len(casos)} casos coherentes")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(principal())
