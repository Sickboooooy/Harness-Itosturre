#!/usr/bin/env python3
"""Revisor adversarial local (otra familia de modelos, 100 % en la máquina) vía Ollama.

Sirve a dos skills: /interrogar (revisión cruzada de un diff o escrito) y al juez de evals.
Uso:
  revisar_ollama.py --modelo qwen2.5:14b --archivo escrito.md [--rubrica rubrica.md] [--rol adversarial|juez]
  git diff | revisar_ollama.py --modelo llama3.1:8b --rol adversarial
Rechaza modelos de la familia Claude: el sentido es tener un punto de vista distinto del trabajador.
Es la alternativa 100 % local a revisar_codex.py (la que corresponde en producción). Mismo contrato: nucleo/juez.py.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nucleo import config as cfg  # noqa: E402
from nucleo import juez  # noqa: E402

ENDPOINT = "http://127.0.0.1:11434/api/generate"
HOSTS_LOCALES = {"127.0.0.1", "localhost", "::1"}
LIMITE_CARACTERES = 60_000


class _SinRedirecciones(urllib.request.HTTPRedirectHandler):
    """Una redirección podría llevar el texto fuera de la máquina: se rechaza."""

    def redirect_request(self, *args, **kwargs):
        return None


def endpoint_local(url: str) -> bool:
    """Solo http a 127.0.0.1, localhost o ::1, sin credenciales. «localhost.atacante.example» no es local."""
    try:
        partes = urllib.parse.urlsplit(url)
        partes.port  # noqa: B018 — valida el puerto (lanza ValueError si no es numérico)
    except ValueError:
        return False
    return partes.scheme == "http" and partes.hostname in HOSTS_LOCALES and not partes.username and not partes.password


def consultar(modelo: str, prompt: str, endpoint: str = ENDPOINT, timeout: int = 600) -> dict:
    cuerpo = json.dumps({"model": modelo, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0}}).encode("utf-8")
    solicitud = urllib.request.Request(endpoint, data=cuerpo, headers={"Content-Type": "application/json"})
    # ProxyHandler({}): un http_proxy del entorno sacaría el texto de la máquina aunque el endpoint sea 127.0.0.1.
    with urllib.request.build_opener(urllib.request.ProxyHandler({}), _SinRedirecciones).open(solicitud, timeout=timeout) as respuesta:
        datos = json.loads(respuesta.read().decode("utf-8"))
    return json.loads(datos.get("response") or "{}")


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("--modelo", required=True)
    analizador.add_argument("--archivo", type=Path, action="append", default=[])
    analizador.add_argument("--rubrica", type=Path)
    analizador.add_argument("--rol", choices=sorted(juez.INSTRUCCIONES), default="adversarial")
    analizador.add_argument("--endpoint", default=ENDPOINT)
    analizador.add_argument("--caso", help="caso de eval que se califica (skill.caso); la compuerta exige uno por caso holdout")
    args = analizador.parse_args()
    if juez.es_familia_claude(args.modelo):
        print("El revisor local debe ser de otra familia de modelos (p. ej. qwen, llama, gemma, mistral).", file=sys.stderr)
        return 3
    if not endpoint_local(args.endpoint):
        print("El revisor solo opera contra Ollama local (http://127.0.0.1, localhost o [::1]): los datos no salen de la máquina.", file=sys.stderr)
        return 3
    if args.rol == "juez" and not args.rubrica:
        print("El rol juez exige --rubrica: sin rúbrica congelada no hay contra qué calificar.", file=sys.stderr)
        return 3
    entrada = "" if args.archivo else sys.stdin.read()
    artefactos, huellas = juez.instantanea(args.archivo, entrada)
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
    try:
        resultado = consultar(args.modelo, prompt, args.endpoint)
    except (urllib.error.URLError, OSError) as error:
        print(f"Ollama no responde en {args.endpoint} ({error}). Inícialo con: ollama serve", file=sys.stderr)
        return 2
    except json.JSONDecodeError:
        print("El modelo no devolvió JSON válido; repite con un modelo más capaz.", file=sys.stderr)
        return 2
    contrato = juez.errores_contrato(args.rol, resultado)
    if contrato:
        print("La respuesta del modelo no cumple el contrato: BLOCKED.\n  " + "\n  ".join(contrato[:10]), file=sys.stderr)
        return 2
    if args.rol == "juez":
        resultado = juez.calificar(resultado, esperados, artefactos)
    resultado["juez"] = {"familia": "ollama", "herramienta": "ollama", "modelo": args.modelo, "esfuerzo": None, "version": None, "rol": args.rol}
    resultado["material"] = juez.material(huellas, rubrica_bytes, args.caso)
    juez.anotar_bitacora(cfg.raiz_proyecto(), resultado)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return juez.codigo_salida(args.rol, resultado)


if __name__ == "__main__":
    sys.exit(principal())
