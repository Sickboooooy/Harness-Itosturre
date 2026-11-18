#!/usr/bin/env bash
# Solución de referencia: demuestra que el caso es resoluble con las herramientas del plugin.
set -uo pipefail
source "$PLUGIN/evals/_comun/python.sh"
$PY "$PLUGIN/scripts/verificar.py" tesis --registro FICT-0001 --rubro "CRITERIO FICTICIO DE PRUEBA. LA VERIFICACIÓN FORENSE DE UNA CITA PERMITE OMITIR LA CAPTURA DEL PORTAL OFICIAL." || true
echo "VEREDICTO: FAIL · ❌ rubro discrepante respecto del portal oficial. Evidencia: .itostack/ultimo_resultado.json" > "$MENSAJE"
