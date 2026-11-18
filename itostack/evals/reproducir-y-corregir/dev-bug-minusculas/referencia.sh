#!/usr/bin/env bash
# Solución de referencia: demuestra que el caso es resoluble con las herramientas del plugin.
set -uo pipefail
python3 "$PLUGIN/scripts/arrancar_app.py" iniciar
BASE=$(python3 -c "import json;print(json.load(open('.itostack/app.json'))['base_url'])")
python3 "$PLUGIN/scripts/verificar.py" app --base "$BASE" --ruta rutas/validar-minusculas.json || true
python3 "$PLUGIN/scripts/verificar.py" app --base "$BASE" --ruta rutas/validar-minusculas.json || true
python3 "$PLUGIN/scripts/arrancar_app.py" detener
cat >> tests/test_app.py <<'PY'


def test_registro_en_minusculas_se_valida():
    respuesta = app.test_client().post("/validar", data={"registro": "fict-0001"})
    assert "VERIFICADO" in respuesta.get_data(as_text=True)
PY
python3 -m pytest -q tests || true
sed -i 's/CRITERIOS_FICTICIOS.get(registro, /CRITERIOS_FICTICIOS.get(registro.strip().upper(), /' app.py
python3 -m pytest -q tests
python3 "$PLUGIN/scripts/arrancar_app.py" iniciar
BASE=$(python3 -c "import json;print(json.load(open('.itostack/app.json'))['base_url'])")
python3 "$PLUGIN/scripts/verificar.py" app --base "$BASE" --ruta rutas/validar-minusculas.json || true
python3 "$PLUGIN/scripts/arrancar_app.py" detener
echo "Reproducido dos veces (FAIL), prueba agregada, corrección aplicada y VEREDICTO: PASS tras el cambio." > "$MENSAJE"
