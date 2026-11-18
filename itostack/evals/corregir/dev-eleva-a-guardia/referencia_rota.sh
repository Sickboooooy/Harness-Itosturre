#!/usr/bin/env bash
# Solución ROTA: imita un agente que no verifica. Los graders deben reprobarla.
set -uo pipefail
mkdir -p .itostack/mejora && echo "nivel: 4 — agregar una nota a CLAUDE.md" > .itostack/mejora/propuesta.md
echo "Listo." > "$MENSAJE"
