#!/usr/bin/env python3
"""Comprobación de entrega de un documento jurídico (contrato CR-1, itostack/citas@1).

Un documento es entregable solo si su manifiesto de procedencia (<documento>.procedencia.json) existe, su huella
coincide (no se editó después de ensamblar), no declara citas pendientes, no quedan marcadores sin resolver y todo
patrón de cita (registro, clave, «rubro:», marca ⚠/❌) cae dentro de un tramo escrito por el ensamblador.

Uso: verificar_entrega.py salidas/escrito.md [más documentos…]
Código: 0 todos entregables · 1 alguno no lo es · 2 un documento no existe.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nucleo import procedencia  # noqa: E402


def revisar(documento: Path) -> list[str]:
    manifiesto = documento.with_name(documento.name + ".procedencia.json")
    try:
        datos = json.loads(manifiesto.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        datos = None
    return procedencia.verificar_entrega(documento.read_bytes(), datos)


def principal(rutas: list[str]) -> int:
    if not rutas:
        print(__doc__)
        return 2
    codigo = 0
    for ruta in map(Path, rutas):
        if not ruta.is_file():
            print(f"✘ {ruta}: no existe")
            return 2
        problemas = revisar(ruta)
        if problemas:
            codigo = 1
            print(f"✘ {ruta}: NO ENTREGABLE")
            for problema in problemas:
                print(f"    {problema}")
        else:
            print(f"✔ {ruta}: entregable (procedencia verificada)")
    return codigo


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(principal(sys.argv[1:]))
