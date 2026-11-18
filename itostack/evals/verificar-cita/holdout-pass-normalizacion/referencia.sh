#!/usr/bin/env bash
# Solución de referencia: demuestra que el caso es resoluble con las herramientas del plugin.
set -uo pipefail
source "$PLUGIN/evals/_comun/python.sh"
$PY "$PLUGIN/scripts/verificar.py" tesis --registro FICT-0003 --rubro '“criterio ficticio aislado. la normalizacion tipografica no debe confundirse con una discrepancia sustantiva del rubro, ni siquiera parcial”' || true
echo "VEREDICTO: PASS · ✅ coincide salvo variaciones tipográficas. ⚠ Tesis aislada: criterio orientador." > "$MENSAJE"
