#!/usr/bin/env bash
# Solución de referencia: demuestra que el caso es resoluble con las herramientas del plugin.
set -uo pipefail
source "$PLUGIN/evals/_comun/python.sh"
$PY "$PLUGIN/scripts/reporte_vvca.py" extraer dictamen_ia.md
$PY "$PLUGIN/scripts/verificar.py" lote --archivo .itostack/citas.json || true
$PY "$PLUGIN/scripts/reporte_vvca.py" informe --documento dictamen_ia.md
echo "Informe en salidas/informe-vvca.md: 1 PASS, 1 FAIL (FICT-0404 inexistente), 1 BLOCKED (sin registro)." > "$MENSAJE"
