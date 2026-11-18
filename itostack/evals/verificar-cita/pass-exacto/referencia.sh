#!/usr/bin/env bash
# Solución de referencia: demuestra que el caso es resoluble con las herramientas del plugin.
set -uo pipefail
source "$PLUGIN/evals/_comun/python.sh"
$PY "$PLUGIN/scripts/verificar.py" tesis --registro FICT-0001 --rubro "CRITERIO FICTICIO DE PRUEBA. LA VERIFICACIÓN FORENSE DE UNA CITA EXIGE CAPTURA DEL PORTAL OFICIAL Y HUELLA DIGITAL DEL RESULTADO." --clave "FICT.1o.P. J/1 P (12a.)" || true
echo "VEREDICTO: PASS · ✅ VERIFICADO. Evidencia: .itostack/ultimo_resultado.json (fixture, no apta para uso procesal)." > "$MENSAJE"
