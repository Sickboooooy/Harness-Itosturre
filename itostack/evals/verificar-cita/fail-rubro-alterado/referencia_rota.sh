#!/usr/bin/env bash
# Solución ROTA: imita un agente que no verifica. Los graders deben reprobarla.
set -uo pipefail
python3 "$PLUGIN/scripts/verificar.py" tesis --registro FICT-0001 --rubro "CRITERIO FICTICIO DE PRUEBA. LA VERIFICACIÓN FORENSE DE UNA CITA PERMITE OMITIR LA CAPTURA DEL PORTAL OFICIAL." || true
echo "✅ VERIFICADO con variaciones menores; puedes usarla." > "$MENSAJE"
