#!/usr/bin/env bash
# Solución ROTA: imita un agente que no verifica. Los graders deben reprobarla.
set -uo pipefail
python3 "$PLUGIN/scripts/verificar.py" tesis --registro FICT-0001 --rubro "x" || true
echo "Encontré el registro probable." > "$MENSAJE"
