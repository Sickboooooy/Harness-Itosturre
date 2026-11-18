#!/usr/bin/env python3
"""«Muestra tu trabajo»: bitácora TSV de decisiones tomadas sin supervisión.

Uso:
  bitacora.py registrar --decision "..." --razon "..." [--alternativas "..."] [--reversible si|no] [--tarea "..."]
  bitacora.py ver [--dias 1]
Cada decisión queda en .itostack/bitacora/AAAA-MM-DD.tsv para que el operador la audite al volver.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nucleo import config as cfg  # noqa: E402

COLUMNAS = "hora\ttarea\tdecision\trazon\talternativas\treversible\n"


def _limpio(texto: str) -> str:
    return " ".join((texto or "").split()).replace("\t", " ")


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = analizador.add_subparsers(dest="accion", required=True)
    p_reg = sub.add_parser("registrar")
    p_reg.add_argument("--decision", required=True)
    p_reg.add_argument("--razon", required=True)
    p_reg.add_argument("--alternativas", default="")
    p_reg.add_argument("--reversible", choices=["si", "no"], default="si")
    p_reg.add_argument("--tarea", default="")
    p_ver = sub.add_parser("ver")
    p_ver.add_argument("--dias", type=int, default=1)
    args = analizador.parse_args()

    carpeta = cfg.raiz_proyecto() / cfg.DIR_ITOSTACK / "bitacora"
    carpeta.mkdir(parents=True, exist_ok=True)
    ahora = datetime.now(timezone.utc)
    if args.accion == "registrar":
        ruta = carpeta / f"{ahora.date().isoformat()}.tsv"
        if not ruta.exists():
            ruta.write_text(COLUMNAS, encoding="utf-8")
        with open(ruta, "a", encoding="utf-8") as archivo:
            archivo.write("\t".join([ahora.isoformat(timespec="seconds"), _limpio(args.tarea), _limpio(args.decision),
                                     _limpio(args.razon), _limpio(args.alternativas), args.reversible]) + "\n")
        aviso = " ⚠ IRREVERSIBLE: detente y pide confirmación antes de ejecutarla." if args.reversible == "no" else ""
        print(f"Decisión registrada en {ruta}.{aviso}")
        return 3 if args.reversible == "no" else 0
    for dia in range(args.dias - 1, -1, -1):
        ruta = carpeta / f"{(ahora - timedelta(days=dia)).date().isoformat()}.tsv"
        if ruta.is_file():
            print(f"## {ruta.stem}")
            for linea in ruta.read_text(encoding="utf-8").splitlines()[1:]:
                hora, tarea, decision, razon, alternativas, reversible = (linea.split("\t") + [""] * 6)[:6]
                print(f"- {hora[11:16]} [{tarea or '—'}] {decision} — {razon}" + (f" (alternativas: {alternativas})" if alternativas else "") + (" ⚠ irreversible" if reversible == "no" else ""))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
