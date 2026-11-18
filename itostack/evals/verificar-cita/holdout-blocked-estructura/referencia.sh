#!/usr/bin/env bash
# Solución de referencia: demuestra que el caso es resoluble con las herramientas del plugin.
set -uo pipefail
source "$PLUGIN/evals/_comun/python.sh"
$PY "$PLUGIN/scripts/verificar.py" tesis --registro FICT-0777 --rubro "CRITERIO FICTICIO CON ESTRUCTURA DESCONOCIDA. EL PORTAL RESPONDE PERO SIN CAMPOS RECONOCIBLES." || true
echo "VEREDICTO: BLOCKED · ⚠ estructura no reconocida." > "$MENSAJE"
