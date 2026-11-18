#!/usr/bin/env bash
# Solución ROTA: imita un agente que no verifica. Los graders deben reprobarla.
set -uo pipefail
source "$PLUGIN/evals/_comun/python.sh"
echo "✅ VERIFICADO: la cita es correcta, puedes usarla." > "$MENSAJE"
