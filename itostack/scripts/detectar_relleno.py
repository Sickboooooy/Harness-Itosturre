#!/usr/bin/env python3
"""«Sin relleno» (unslop en español): detecta muletillas típicas de texto generado por IA.

No toca fórmulas forenses legítimas («en virtud de lo anterior», «por lo expuesto»): solo marca
relleno que diluye un escrito, un PR o un mensaje. Uso: detectar_relleno.py ARCHIVO [--umbral 3]
Salida 0 si el texto está limpio (puntaje < umbral); 1 si requiere poda.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PATRONES: list[tuple[str, str]] = [
    (r"\bes importante (?:destacar|señalar|mencionar|resaltar|notar)\b", "afirma directamente lo importante"),
    (r"\bcabe (?:destacar|mencionar|señalar|resaltar)\b", "elimina la fórmula y di el dato"),
    (r"\bsin lugar a dudas\b|\bsin duda alguna\b", "la certeza se demuestra con la fuente, no con el adverbio"),
    (r"\ben el (?:mundo|panorama|contexto) actual\b|\ben la actualidad\b", "relleno temporal sin contenido"),
    (r"\bjuega un papel (?:crucial|fundamental|clave|importante)\b", "di qué hace exactamente"),
    (r"\bno solo\b[^.]{0,80}\bsino también\b", "estructura enfática de IA; usa una afirmación simple"),
    (r"\b(?:robust[oa]s?|integral(?:es)?|sinergia|potenciar|vanguardia|innovador[a]?)\b", "adjetivo de folleto"),
    (r"\b(?:navegar|adentrarnos en) (?:el|la|los|las)\b", "metáfora vacía"),
    (r"\ben resumen\b|\ben conclusión\b|\ben definitiva\b", "cierre redundante: el lector ya leyó"),
    (r"¡(?:claro|por supuesto|excelente pregunta)!|\bespero que (?:esto )?(?:te |le )?(?:sea de )?ayud", "fórmula conversacional de asistente"),
    (r"\bcomo modelo de lenguaje\b|\bcomo (?:una )?IA\b", "autorreferencia del modelo"),
    (r"\bdelve\b|\btapestry\b|\bleverage\b", "calco del inglés"),
]


def analizar(texto: str) -> list[tuple[int, str, str]]:
    hallazgos = []
    for numero, linea in enumerate(texto.splitlines(), start=1):
        for patron, sugerencia in PATRONES:
            for m in re.finditer(patron, linea, re.IGNORECASE):
                hallazgos.append((numero, m.group(0), sugerencia))
    rayas = texto.count("—")
    palabras = max(len(texto.split()), 1)
    if rayas / palabras > 0.01:
        hallazgos.append((0, f"{rayas} rayas (—)", "abuso de raya; usa comas o punto"))
    return hallazgos


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("archivo", type=Path)
    analizador.add_argument("--umbral", type=int, default=3)
    args = analizador.parse_args()
    hallazgos = analizar(args.archivo.read_text(encoding="utf-8"))
    for linea, fragmento, sugerencia in hallazgos:
        print(f"{args.archivo}:{linea}: «{fragmento}» → {sugerencia}")
    estado = "LIMPIO" if len(hallazgos) < args.umbral else "REQUIERE PODA"
    print(f"sin-relleno: {len(hallazgos)} hallazgo(s) · {estado}")
    return 0 if estado == "LIMPIO" else 1


if __name__ == "__main__":
    sys.exit(principal())
