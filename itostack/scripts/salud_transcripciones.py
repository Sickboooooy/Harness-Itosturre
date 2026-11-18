#!/usr/bin/env python3
"""transcript-healthcheck: busca fricción recurrente en las transcripciones de Claude Code.

Señales: correcciones humanas, errores de herramientas, bloqueos de guardias itostack, veredictos
BLOCKED y comandos repetidos (candidatos a «construir la palanca»). Solo propone; no cambia nada.
Silencioso si no hay propuestas útiles (no escribe reporte ni imprime nada).

Uso: salud_transcripciones.py [--dias 1] [--proyectos ~/.claude/projects] [--filtro texto] [--min-repeticiones 3]
Programación sugerida (cron, días hábiles 8:44):  44 8 * * 1-5  cd ~/proyecto && python3 <raíz>/scripts/salud_transcripciones.py
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nucleo import config as cfg, transcripciones as tx  # noqa: E402

RE_CORRECCION = re.compile(
    r"^\s*(?:no[,.!\s])|\bte\s+dije\b|\botra\s+vez\b|\beso\s+est[áa]\s+mal\b|\bno\s+inventes\b|\bdeja\s+de\b|\bno\s+hagas\b|\bincorrect[oa]\b",
    re.IGNORECASE,
)


def normalizar_comando(comando: str) -> str:
    comando = re.sub(r"(['\"]).*?\1", "…", comando.strip())
    comando = re.sub(r"\b\d{3,}\b", "N", comando)
    return " ".join(comando.split()[:6])


def analizar(rutas: list[Path], min_repeticiones: int) -> dict:
    correcciones, errores, bloqueos, comandos = [], Counter(), Counter(), Counter()
    blocked = 0
    for ruta in rutas:
        for mensaje in tx.leer(ruta):
            if tx.es_prompt_humano(mensaje):
                texto = " ".join(mensaje.textos)
                if RE_CORRECCION.search(texto) and not texto.lstrip().startswith("<"):
                    correcciones.append(re.sub(r"\s+", " ", texto)[:200])
            for uso in mensaje.usos_herramienta:
                if uso["nombre"] == "Bash":
                    comandos[normalizar_comando(str(uso["entrada"].get("command", "")))] += 1
            for resultado in mensaje.resultados_herramienta:
                texto = resultado["texto"]
                if "itostack:" in texto:
                    bloqueos[texto.split("itostack:", 1)[1].strip()[:90]] += 1
                elif resultado["error"]:
                    errores[texto.strip().splitlines()[0][:90] if texto.strip() else "error sin texto"] += 1
                blocked += texto.count("VEREDICTO: BLOCKED")
    palancas = [(c, n) for c, n in comandos.most_common(10) if n >= min_repeticiones and len(c) > 8]
    return {"correcciones": correcciones, "errores": errores, "bloqueos": bloqueos, "blocked": blocked, "palancas": palancas}


def reporte(datos: dict, rutas: list[Path]) -> str | None:
    propuestas = []
    if len(datos["correcciones"]) >= 2:
        propuestas.append(f"Correcciones humanas: {len(datos['correcciones'])}. Revisar con /corregir y elevar las repetidas a lint/hook/prueba.")
    for error, n in datos["errores"].most_common(5):
        if n >= 3:
            propuestas.append(f"Error de herramienta repetido ({n}×): «{error}». Candidato a script determinista o a mejora de skill.")
    for bloqueo, n in datos["bloqueos"].most_common(5):
        if n >= 3:
            propuestas.append(f"Guardia disparada {n}×: «{bloqueo}». Si es legítima, la skill debe enseñar el camino correcto antes de chocar con ella.")
    for comando, n in datos["palancas"]:
        propuestas.append(f"Comando repetido {n}×: `{comando}`. Construir la palanca: extraerlo a un CLI en scripts/.")
    if datos["blocked"] >= 3:
        propuestas.append(f"{datos['blocked']} veredictos BLOCKED: revisar si falta un dato recurrente (cuenta de prueba, selector, calibración).")
    if not propuestas:
        return None
    lineas = [f"# Salud de transcripciones — {datetime.now(timezone.utc).date().isoformat()}", "", f"Transcripciones analizadas: {len(rutas)}", "", "## Propuestas (esperan selección del operador)", ""]
    lineas += [f"{i}. {p}" for i, p in enumerate(propuestas, start=1)]
    if datos["correcciones"]:
        lineas += ["", "## Correcciones textuales recientes", ""] + [f"- «{c}»" for c in datos["correcciones"][-8:]]
    return "\n".join(lineas) + "\n"


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("--dias", type=float, default=1)
    analizador.add_argument("--proyectos", type=Path, default=cfg.home_real() / ".claude" / "projects")
    analizador.add_argument("--filtro", default="", help="solo carpetas de proyecto cuyo nombre contenga este texto")
    analizador.add_argument("--min-repeticiones", type=int, default=3)
    args = analizador.parse_args()
    limite = time.time() - args.dias * 86400
    rutas = [p for p in args.proyectos.glob("*/*.jsonl") if p.stat().st_mtime >= limite and args.filtro in p.parent.name]
    texto = reporte(analizar(rutas, args.min_repeticiones), rutas)
    if texto is None:
        return 0
    destino = cfg.raiz_proyecto() / cfg.DIR_ITOSTACK / "mejora" / "reportes" / f"salud-{datetime.now(timezone.utc).date().isoformat()}.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(texto, encoding="utf-8")
    print(texto)
    print(f"Reporte: {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
