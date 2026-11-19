#!/usr/bin/env python3
"""Valida la reserva holdout del ejecutor (CR-2: X8 y X9) antes de cualquier corrida.

Estructura: reserva/<skill>/<caso>/case.yaml (más su andamiaje) y reserva/aprobaciones.json, una lista de
{"caso": "<skill>/<caso>", "sha256_caso", "autor", "aprobado_por", "fecha", "datos_sinteticos": true}.
Cada caso debe tener su aprobación; el autor (revisor humano independiente) y quien aprueba (el operador) deben ser
personas distintas; el caso debe declararse sintético (sin datos jurídicos reales); y su huella debe ser la aprobada:
un caso cambiado después de aprobarse no corre. Biblioteca estándar; código 0 válida · 1 inválida.
Uso: validar_reserva.py <reserva> <skill>
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def huella_caso(directorio: Path) -> str:
    resumen = hashlib.sha256()
    for archivo in sorted(p for p in directorio.rglob("*") if p.is_file()):
        resumen.update(archivo.relative_to(directorio).as_posix().encode())
        resumen.update(archivo.read_bytes())
    return resumen.hexdigest()


def validar(reserva: Path, skill: str) -> list[str]:
    casos = sorted(p.parent for p in (reserva / skill).glob("*/case.yaml"))
    if not casos:
        return [f"la reserva no tiene casos para «{skill}»"]
    try:
        aprobaciones = json.loads((reserva / "aprobaciones.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ["no hay aprobaciones.json legible"]
    if not isinstance(aprobaciones, list) or not all(isinstance(a, dict) for a in aprobaciones):
        return ["aprobaciones.json debe ser una lista de objetos"]
    por_caso: dict = {}
    for a in aprobaciones:
        por_caso.setdefault(a.get("caso"), []).append(a)
    problemas = []
    for directorio in casos:
        clave = f"{skill}/{directorio.name}"
        registros = por_caso.get(clave, [])
        if len(registros) != 1:
            problemas.append(f"{clave}: {'sin aprobación' if not registros else 'aprobaciones repetidas'}")
            continue
        a = registros[0]
        autor, aprueba = a.get("autor"), a.get("aprobado_por")
        if not isinstance(autor, str) or not autor.strip() or not isinstance(aprueba, str) or not aprueba.strip():
            problemas.append(f"{clave}: falta el autor o quien aprueba")
        elif autor.strip().casefold() == aprueba.strip().casefold():
            problemas.append(f"{clave}: el autor y quien aprueba son la misma persona")
        if a.get("datos_sinteticos") is not True:
            problemas.append(f"{clave}: no declara datos sintéticos")
        if not isinstance(a.get("fecha"), str) or not a["fecha"].strip():
            problemas.append(f"{clave}: falta la fecha de aprobación")
        if a.get("sha256_caso") != huella_caso(directorio):
            problemas.append(f"{clave}: el caso cambió después de aprobarse (o la huella no es la suya)")
    sobrantes = sorted(c for c in por_caso if isinstance(c, str) and c.startswith(f"{skill}/") and not (reserva / c).is_dir())
    problemas += [f"{c}: aprobación de un caso que no existe" for c in sobrantes]
    return problemas


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    errores = validar(Path(sys.argv[1]), sys.argv[2])
    for error in errores:
        print(f"✘ {error}")
    print("reserva: " + ("válida" if not errores else "INVÁLIDA (no se evalúa)"))
    sys.exit(1 if errores else 0)
