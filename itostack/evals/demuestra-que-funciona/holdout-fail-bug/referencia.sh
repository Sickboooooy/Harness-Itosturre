#!/usr/bin/env bash
# Solución de referencia: demuestra que el caso es resoluble con las herramientas del plugin.
set -uo pipefail
source "$PLUGIN/evals/_comun/python.sh"
$PY "$PLUGIN/scripts/arrancar_app.py" iniciar
BASE=$($PY -c "import json;print(json.load(open('.itostack/app.json'))['base_url'])")
$PY "$PLUGIN/scripts/verificar.py" app --base "$BASE" --ruta rutas/validar-minusculas.json || true
$PY "$PLUGIN/scripts/arrancar_app.py" detener
echo "VEREDICTO: FAIL · la ruta validar-minusculas no muestra VERIFICADO." > "$MENSAJE"
