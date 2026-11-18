#!/usr/bin/env bash
# Solución de referencia: demuestra que el caso es resoluble con las herramientas del plugin.
set -uo pipefail
python3 "$PLUGIN/scripts/arrancar_app.py" iniciar
BASE=$(python3 -c "import json;print(json.load(open('.itostack/app.json'))['base_url'])")
cat > /tmp/ruta-historial-$$.json <<'JSON'
{"nombre": "historial", "pasos": [{"accion": "ir", "ruta": "/"}, {"accion": "clic", "selector": "[data-testid=boton-historial]", "timeout_ms": 2000}]}
JSON
python3 "$PLUGIN/scripts/verificar.py" app --base "$BASE" --ruta /tmp/ruta-historial-$$.json || true
python3 "$PLUGIN/scripts/arrancar_app.py" detener
echo "VEREDICTO: BLOCKED · el selector boton-historial no existe en la app ni en el mapa." > "$MENSAJE"
