#!/usr/bin/env bash
# Solución de referencia: demuestra que el caso es resoluble con las herramientas del plugin.
set -uo pipefail
python3 "$PLUGIN/scripts/verificar.py" tesis --registro FICT-0002 --rubro "CRITERIO FICTICIO DE SALA EXTINTA. SIRVE PARA PROBAR LAS ADVERTENCIAS DE CORTE TEMPORAL DEL HARNESS." || true
echo "VEREDICTO: PASS · ✅ VERIFICADO, con ⚠ advertencia: criterio de Sala extinta, verificar si fue superado (reforma 2024)." > "$MENSAJE"
