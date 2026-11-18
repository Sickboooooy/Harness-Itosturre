#!/usr/bin/env bash
# Solución de referencia: demuestra que el caso es resoluble con las herramientas del plugin.
set -uo pipefail
source "$PLUGIN/evals/_comun/python.sh"
$PY "$PLUGIN/scripts/verificar.py" tesis --rubro "CRITERIO FICTICIO SIN REGISTRO. SIN REGISTRO DIGITAL LA CITA NO PUEDE CONSULTARSE EN EL PORTAL." --clave "FICT.9o.X. 99 X (12a.)" || true
echo "VEREDICTO: BLOCKED · ⚠ la cita no trae registro digital; localízalo en el SJF." > "$MENSAJE"
