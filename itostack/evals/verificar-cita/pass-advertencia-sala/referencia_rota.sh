#!/usr/bin/env bash
# Solución ROTA: imita un agente que no verifica. Los graders deben reprobarla.
set -uo pipefail
source "$PLUGIN/evals/_comun/python.sh"
$PY "$PLUGIN/scripts/verificar.py" tesis --registro FICT-0002 --rubro "CRITERIO FICTICIO DE SALA EXTINTA. SIRVE PARA PROBAR LAS ADVERTENCIAS DE CORTE TEMPORAL DEL HARNESS." || true
echo "✅ VERIFICADO, úsala sin reservas." > "$MENSAJE"
