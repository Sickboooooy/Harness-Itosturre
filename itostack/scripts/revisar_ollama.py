#!/usr/bin/env python3
"""Revisor adversarial local (otra familia de modelos, 100 % en la máquina) vía Ollama.

Sirve a dos skills: /interrogar (revisión cruzada de un diff o escrito) y al juez de evals.
Uso:
  revisar_ollama.py --modelo qwen2.5:14b --archivo escrito.md [--rubrica rubrica.md] [--rol adversarial|juez]
  git diff | revisar_ollama.py --modelo llama3.1:8b --rol adversarial
Rechaza modelos de la familia Claude: el sentido es tener un punto de vista distinto del trabajador.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENDPOINT = "http://127.0.0.1:11434/api/generate"

INSTRUCCIONES = {
    "adversarial": (
        "Eres un revisor adversarial de un despacho jurídico mexicano. Busca errores, no virtudes. Señala: citas sin fuente "
        "verificable, afirmaciones sin sustento, riesgos procesales (plazos, competencia, improcedencia), contradicciones y "
        "atajos técnicos. Responde SOLO JSON: {\"hallazgos\": [{\"gravedad\": \"alta|media|baja\", \"ubicacion\": \"...\", "
        "\"problema\": \"...\", \"sugerencia\": \"...\"}], \"veredicto\": \"aprobar|corregir|rechazar\"}"
    ),
    "juez": (
        "Eres un juez de evaluación. Califica el artefacto SOLO contra la rúbrica congelada que se te da; no premies estilo. "
        "Responde SOLO JSON: {\"puntaje\": 0-10, \"criterios\": [{\"criterio\": \"...\", \"cumple\": true|false, \"evidencia\": \"...\"}], "
        "\"fallos_criticos\": [\"...\"]}"
    ),
}


def consultar(modelo: str, prompt: str, endpoint: str = ENDPOINT, timeout: int = 600) -> dict:
    cuerpo = json.dumps({"model": modelo, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0}}).encode("utf-8")
    solicitud = urllib.request.Request(endpoint, data=cuerpo, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(solicitud, timeout=timeout) as respuesta:
        datos = json.loads(respuesta.read().decode("utf-8"))
    return json.loads(datos.get("response") or "{}")


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("--modelo", required=True)
    analizador.add_argument("--archivo", type=Path, action="append", default=[])
    analizador.add_argument("--rubrica", type=Path)
    analizador.add_argument("--rol", choices=sorted(INSTRUCCIONES), default="adversarial")
    analizador.add_argument("--endpoint", default=ENDPOINT)
    args = analizador.parse_args()
    if "claude" in args.modelo.lower():
        print("El revisor local debe ser de otra familia de modelos (p. ej. qwen, llama, gemma, mistral).", file=sys.stderr)
        return 3
    if not args.endpoint.startswith(("http://127.0.0.1", "http://localhost")):
        print("El revisor solo opera contra Ollama local: los datos no salen de la máquina.", file=sys.stderr)
        return 3
    artefactos = "\n\n".join(f"=== {a} ===\n{a.read_text(encoding='utf-8')}" for a in args.archivo) or sys.stdin.read()
    rubrica = f"\n\nRÚBRICA CONGELADA:\n{args.rubrica.read_text(encoding='utf-8')}" if args.rubrica else ""
    prompt = f"{INSTRUCCIONES[args.rol]}{rubrica}\n\nARTEFACTO:\n{artefactos[:60000]}"
    try:
        resultado = consultar(args.modelo, prompt, args.endpoint)
    except (urllib.error.URLError, OSError) as error:
        print(f"Ollama no responde en {args.endpoint} ({error}). Inícialo con: ollama serve", file=sys.stderr)
        return 2
    except json.JSONDecodeError:
        print("El modelo no devolvió JSON válido; repite con un modelo más capaz.", file=sys.stderr)
        return 2
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    if args.rol == "juez":
        return 0 if resultado.get("puntaje") == 10 and not resultado.get("fallos_criticos") else 1
    return 0 if resultado.get("veredicto") == "aprobar" else 1


if __name__ == "__main__":
    sys.exit(principal())
