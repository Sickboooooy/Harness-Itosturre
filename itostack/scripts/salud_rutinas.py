#!/usr/bin/env python3
"""routine-healthcheck: consumo de tokens por sesión y por skill; detecta desperdicio.

Marca sesiones atípicas (> percentil 90 y > umbral absoluto) y estima qué proporción del trabajo
fue verificación vs. generación (por las herramientas usadas). Silencioso si no hay anomalías.
Uso: salud_rutinas.py [--dias 7] [--umbral 400000] [--proyectos ~/.claude/projects] [--filtro texto]
Programación sugerida (cron, lunes 8:49):  49 8 * * 1  cd ~/proyecto && python3 <raíz>/scripts/salud_rutinas.py
"""

from __future__ import annotations

import argparse
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nucleo import config as cfg, transcripciones as tx  # noqa: E402

RE_VERIFICACION = re.compile(r"verificar\.py|pytest|evidencia_web|demuestra|autoprueba|claude plugin eval|lint_itosturre")


def tokens(uso: dict) -> int:
    return sum(int(uso.get(k) or 0) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))


def analizar(rutas: list[Path]) -> dict:
    por_sesion: dict[str, int] = {}
    por_skill: Counter = Counter()
    verificacion = generacion = 0
    for ruta in rutas:
        total = 0
        skill_actual = "sin-skill"
        for mensaje in tx.leer(ruta):
            for uso in mensaje.usos_herramienta:
                if uso["nombre"] == "Skill":
                    skill_actual = str(uso["entrada"].get("skill") or uso["entrada"].get("command") or skill_actual)
            consumo = tokens(mensaje.uso_tokens)
            total += consumo
            por_skill[skill_actual] += consumo
            comandos = " ".join(str(u["entrada"].get("command", "")) for u in mensaje.usos_herramienta if u["nombre"] == "Bash")
            if RE_VERIFICACION.search(comandos):
                verificacion += consumo
            elif mensaje.usos_herramienta:
                generacion += consumo
        por_sesion[ruta.stem] = total
    return {"por_sesion": por_sesion, "por_skill": por_skill, "verificacion": verificacion, "generacion": generacion}


def reporte(datos: dict, umbral: int) -> str | None:
    valores = sorted(datos["por_sesion"].values())
    if not valores:
        return None
    p90 = valores[int(0.9 * (len(valores) - 1))]
    atipicas = [(s, t) for s, t in datos["por_sesion"].items() if t > umbral and (len(valores) < 5 or t >= p90)]
    if not atipicas:
        return None
    total_trabajo = max(datos["verificacion"] + datos["generacion"], 1)
    lineas = [
        f"# Salud de rutinas — {datetime.now(timezone.utc).date().isoformat()}", "",
        f"Sesiones: {len(valores)} · mediana {statistics.median(valores):,.0f} tokens · p90 {p90:,.0f}",
        f"Proporción verificación/generación (aprox.): {100 * datos['verificacion'] / total_trabajo:.0f}% / {100 * datos['generacion'] / total_trabajo:.0f}%", "",
        "## Sesiones atípicas", "",
    ]
    lineas += [f"- `{s}`: {t:,.0f} tokens" for s, t in sorted(atipicas, key=lambda x: -x[1])[:10]]
    lineas += ["", "## Consumo por skill", ""] + [f"- {k}: {v:,.0f}" for k, v in datos["por_skill"].most_common(10)]
    lineas += ["", "## Preguntas para el operador", "",
               "- ¿Alguna skill se usa para ediciones triviales (overhead del modo completo)?",
               "- ¿Algún paso repetido podría ser un script (construir la palanca) en vez de razonamiento?"]
    return "\n".join(lineas) + "\n"


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("--dias", type=float, default=7)
    analizador.add_argument("--umbral", type=int, default=400_000)
    analizador.add_argument("--proyectos", type=Path, default=cfg.home_real() / ".claude" / "projects")
    analizador.add_argument("--filtro", default="")
    args = analizador.parse_args()
    limite = time.time() - args.dias * 86400
    rutas = [p for p in args.proyectos.glob("*/*.jsonl") if p.stat().st_mtime >= limite and args.filtro in p.parent.name]
    texto = reporte(analizar(rutas), args.umbral)
    if texto is None:
        return 0
    destino = cfg.raiz_proyecto() / cfg.DIR_ITOSTACK / "mejora" / "reportes" / f"rutinas-{datetime.now(timezone.utc).date().isoformat()}.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(texto, encoding="utf-8")
    print(texto)
    print(f"Reporte: {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
