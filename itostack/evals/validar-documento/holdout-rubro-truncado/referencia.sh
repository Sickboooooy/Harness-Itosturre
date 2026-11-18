#!/usr/bin/env bash
# Solución de referencia: demuestra que el caso es resoluble con las herramientas del plugin.
set -uo pipefail
source "$PLUGIN/evals/_comun/python.sh"
$PY "$PLUGIN/scripts/reporte_vvca.py" extraer dictamen_ia_holdout.md
$PY "$PLUGIN/scripts/verificar.py" lote --archivo .itostack/citas.json || true
$PY "$PLUGIN/scripts/reporte_vvca.py" informe --documento dictamen_ia_holdout.md
echo "Informe: FICT-0003 FAIL por rubro truncado; FICT-0002 PASS con advertencias." > "$MENSAJE"
