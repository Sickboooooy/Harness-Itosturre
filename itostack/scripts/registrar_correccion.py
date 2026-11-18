#!/usr/bin/env python3
"""Mejora continua: de corrección humana repetida a regla determinista.

Uso:
  registrar_correccion.py pendientes                       correcciones repetidas (≥2) aún sin elevar
  registrar_correccion.py proponer --clave K --nivel N --artefacto RUTA --descripcion TEXTO
        escribe .itostack/mejora/propuesta.md (y copia fechada); NO aplica cambios
  registrar_correccion.py elevar --clave K --nivel N --artefacto RUTA --descripcion TEXTO
        registra en elevaciones.tsv que la propuesta ya se aplicó (tras aprobación del operador)

Niveles (pirámide invertida, del más fuerte al más débil):
  1 diseño: tipo, API o estructura que hace imposible el error
  2 análisis estático: regla de lint o hook que bloquea antes de la entrega
  3 verificación: prueba, caso de eval o ruta del mapa de funcionalidades
  4 prosa: instrucción en skill, playbook o CLAUDE.md (último recurso)
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nucleo import config as cfg  # noqa: E402

NIVELES = {1: "diseño (tipo/API)", 2: "análisis estático (lint/hook)", 3: "verificación (prueba/eval)", 4: "prosa (skill/CLAUDE.md)"}


def _filas(ruta: Path, columnas: int) -> list[list[str]]:
    if not ruta.is_file():
        return []
    return [l.split("\t") for l in ruta.read_text(encoding="utf-8").splitlines()[1:] if l.count("\t") >= columnas - 1]


def pendientes(mejora: Path) -> list[tuple[str, int, list[str]]]:
    correcciones = _filas(mejora / "correcciones.tsv", 4)
    elevadas = {f[1] for f in _filas(mejora / "elevaciones.tsv", 5)}
    conteo = Counter(f[2] for f in correcciones)
    extractos: dict[str, list[str]] = defaultdict(list)
    for fila in correcciones:
        extractos[fila[2]].append(fila[3])
    return sorted(((k, n, extractos[k]) for k, n in conteo.items() if n >= 2 and k not in elevadas), key=lambda t: -t[1])


def proponer(mejora: Path, clave: str, nivel: int, artefacto: str, descripcion: str) -> Path:
    repeticiones = Counter(f[2] for f in _filas(mejora / "correcciones.tsv", 4))[clave]
    ahora = datetime.now(timezone.utc)
    contenido = "\n".join([
        f"# Propuesta de elevación — {clave}",
        "",
        f"- nivel: {nivel} — {NIVELES[nivel]}",
        f"- repeticiones observadas: {repeticiones}",
        f"- artefacto: {artefacto}",
        f"- descripción: {descripcion}",
        f"- fecha: {ahora.isoformat(timespec='seconds')}",
        "- estado: PROPUESTA (requiere aprobación del operador antes de aplicar)",
        "",
        "## Por qué este nivel",
        "",
        "Se eligió el nivel más fuerte que puede impedir el error. Si se eligió prosa (nivel 4), justificar por qué",
        "no fue posible un tipo, una regla de lint/hook o una prueba.",
        "",
        "## Verificación de la elevación",
        "",
        "- Agregar un caso que reproduzca el error y comprobar que la nueva guardia lo bloquea.",
        "- Correr pytest y la autoprueba de evals; registrar con `registrar_correccion.py elevar` al aplicarla.",
        "",
    ])
    (mejora / "propuestas").mkdir(parents=True, exist_ok=True)
    fechada = mejora / "propuestas" / f"{ahora.strftime('%Y%m%dT%H%M%SZ')}-{clave}.md"
    fechada.write_text(contenido, encoding="utf-8")
    (mejora / "propuesta.md").write_text(contenido, encoding="utf-8")
    return fechada


def elevar(mejora: Path, clave: str, nivel: int, artefacto: str, descripcion: str) -> None:
    ruta = mejora / "elevaciones.tsv"
    if not ruta.exists():
        ruta.write_text("fecha\tclave\tnivel\tartefacto\tdescripcion\n", encoding="utf-8")
    with open(ruta, "a", encoding="utf-8") as archivo:
        archivo.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}\t{clave}\t{nivel}\t{artefacto}\t{descripcion}\n")


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = analizador.add_subparsers(dest="accion", required=True)
    sub.add_parser("pendientes")
    for nombre in ("proponer", "elevar"):
        p = sub.add_parser(nombre)
        p.add_argument("--clave", required=True)
        p.add_argument("--nivel", type=int, choices=sorted(NIVELES), required=True)
        p.add_argument("--artefacto", required=True)
        p.add_argument("--descripcion", required=True)
    args = analizador.parse_args()
    mejora = cfg.raiz_proyecto() / cfg.DIR_ITOSTACK / "mejora"
    mejora.mkdir(parents=True, exist_ok=True)
    if args.accion == "pendientes":
        lista = pendientes(mejora)
        if not lista:
            print("Sin correcciones repetidas pendientes de elevar.")
        for clave, veces, extractos in lista:
            print(f"- {clave} · {veces} veces")
            for extracto in extractos[-3:]:
                print(f"    «{extracto[:140]}»")
        return 0
    if args.accion == "proponer":
        ruta = proponer(mejora, args.clave, args.nivel, args.artefacto, args.descripcion)
        print(f"Propuesta escrita: {mejora / 'propuesta.md'} (copia: {ruta}). Espera aprobación antes de aplicar.")
        return 0
    elevar(mejora, args.clave, args.nivel, args.artefacto, args.descripcion)
    print(f"Elevación registrada para «{args.clave}» (nivel {args.nivel}).")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
