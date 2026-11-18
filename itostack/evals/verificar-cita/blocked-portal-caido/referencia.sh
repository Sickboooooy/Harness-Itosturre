#!/usr/bin/env bash
# Solución de referencia: demuestra que el caso es resoluble con las herramientas del plugin.
set -uo pipefail
source "$PLUGIN/evals/_comun/python.sh"
$PY "$PLUGIN/scripts/verificar.py" tesis --registro FICT-0503 --rubro "CRITERIO FICTICIO QUE NO PUEDE CONSULTARSE PORQUE EL PORTAL NO RESPONDE." || true
echo "VEREDICTO: BLOCKED · ⚠ portal no disponible; no se pudo verificar." > "$MENSAJE"
