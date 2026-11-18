#!/usr/bin/env bash
# Solución de referencia: demuestra que el caso es resoluble con las herramientas del plugin.
set -uo pipefail
source "$PLUGIN/evals/_comun/python.sh"
$PY "$PLUGIN/scripts/verificar.py" tesis --registro FICT-0001 --rubro "CRITERIO FICTICIO DE PRUEBA. LA VERIFICACIÓN FORENSE DE UNA CITA EXIGE CAPTURA DEL PORTAL OFICIAL Y HUELLA DIGITAL DEL RESULTADO." --clave "FICT.1o.P. J/1 P (12a.)" --epoca "Undécima Época" || true
echo "VEREDICTO: FAIL · ❌ época discrepante: el escrito la cita como Undécima Época y el portal oficial la publica en Duodécima Época. El rubro y la clave sí coinciden; la discrepancia está en la época, de modo que la cita no puede usarse tal como está. Evidencia: .itostack/ultimo_resultado.json" > "$MENSAJE"
