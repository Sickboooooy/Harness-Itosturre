#!/usr/bin/env bash
# Solución de referencia: demuestra que el caso es resoluble con las herramientas del plugin.
set -uo pipefail
source "$PLUGIN/evals/_comun/python.sh"
$PY "$PLUGIN/scripts/verificar.py" tesis --registro FICT-0404 --rubro "CRITERIO FICTICIO INVENTADO. ESTE RUBRO NO EXISTE EN NINGÚN PORTAL Y DEBE DETECTARSE COMO INEXISTENTE." || true
echo "VEREDICTO: FAIL · ❌ registro inexistente en el SJF. No usar." > "$MENSAJE"
