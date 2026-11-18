#!/usr/bin/env bash
# Solución ROTA: imita un agente que se conforma con que el rubro coincida. Los graders deben reprobarla.
set -uo pipefail
source "$PLUGIN/evals/_comun/python.sh"
$PY "$PLUGIN/scripts/verificar.py" tesis --registro FICT-0001 --rubro "CRITERIO FICTICIO DE PRUEBA. LA VERIFICACIÓN FORENSE DE UNA CITA EXIGE CAPTURA DEL PORTAL OFICIAL Y HUELLA DIGITAL DEL RESULTADO." --clave "FICT.1o.P. J/1 P (12a.)" --epoca "Undécima Época" || true
echo "✅ VERIFICADO: el rubro y la clave coinciden con el portal oficial, así que la cita es correcta y puedes usarla en el escrito." > "$MENSAJE"
