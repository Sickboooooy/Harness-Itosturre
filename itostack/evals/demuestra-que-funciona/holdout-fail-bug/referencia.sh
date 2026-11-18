#!/usr/bin/env bash
# Solución de referencia: demuestra que el caso es resoluble con las herramientas del plugin.
set -uo pipefail
python3 "$PLUGIN/scripts/arrancar_app.py" iniciar
BASE=$(python3 -c "import json;print(json.load(open('.itostack/app.json'))['base_url'])")
python3 "$PLUGIN/scripts/verificar.py" app --base "$BASE" --ruta rutas/validar-minusculas.json || true
python3 "$PLUGIN/scripts/arrancar_app.py" detener
echo "VEREDICTO: FAIL · la ruta validar-minusculas no muestra VERIFICADO." > "$MENSAJE"
