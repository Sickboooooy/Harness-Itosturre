#!/usr/bin/env python3
"""Consulta y auditoría del almacén de evidencia forense.

Uso:
  evidencia_db.py recientes [--limite 20]
  evidencia_db.py consultar --tipo tesis --id 2025432
  evidencia_db.py vigente --tipo tesis --id 2025432 [--dias 30]   (salida 0 si hay PASS vigente e íntegro)
  evidencia_db.py auditar                                          (recalcula SHA-256 de toda la evidencia)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nucleo import config as cfg  # noqa: E402
from nucleo.evidencia import AlmacenEvidencia  # noqa: E402


def modos_validos(config: dict) -> tuple[str, ...]:
    return ("real", "fixture") if config["modo"] == "fixture" else ("real",)


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = analizador.add_subparsers(dest="accion", required=True)
    p_rec = sub.add_parser("recientes")
    p_rec.add_argument("--limite", type=int, default=20)
    for nombre in ("consultar", "vigente"):
        p = sub.add_parser(nombre)
        p.add_argument("--tipo", choices=["tesis", "url", "app"], default="tesis")
        p.add_argument("--id", required=True)
        p.add_argument("--dias", type=int)
    sub.add_parser("auditar")
    args = analizador.parse_args()

    config = cfg.cargar()
    almacen = AlmacenEvidencia(cfg.ruta_en_proyecto(config, config["evidencia"]["base_datos"]))
    if args.accion == "recientes":
        for fila in almacen.recientes(args.limite):
            print(f"#{fila['id']} {fila['creado_en']} {fila['tipo']} {fila['identificador']} {fila['veredicto']} [{fila['modo_fuente']}] {fila['motivo']}")
        return 0
    if args.accion == "auditar":
        problemas = almacen.auditar()
        for identificador, lista in problemas:
            print(f"#{identificador}: " + "; ".join(lista))
        print("Integridad: OK" if not problemas else f"Integridad: {len(problemas)} registro(s) con problemas")
        return 0 if not problemas else 1
    if args.accion == "consultar":
        fila = almacen.ultimo(args.tipo, args.id, modos_validos(config))
        print(json.dumps(fila, ensure_ascii=False, indent=2) if fila else "sin registros")
        return 0 if fila else 1
    dias = args.dias or config["evidencia"]["vigencia_dias"]
    fila = almacen.vigente(args.tipo, args.id, dias, modos_validos(config))
    print(f"VIGENTE: {fila['ruta_resultado']}" if fila else "SIN EVIDENCIA VIGENTE")
    return 0 if fila else 1


if __name__ == "__main__":
    sys.exit(principal())
