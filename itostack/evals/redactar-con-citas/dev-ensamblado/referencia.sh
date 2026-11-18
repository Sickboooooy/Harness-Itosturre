#!/usr/bin/env bash
# Solución de referencia: demuestra que el caso es resoluble con las herramientas del plugin.
set -uo pipefail
source "$PLUGIN/evals/_comun/python.sh"
$PY "$PLUGIN/scripts/verificar.py" tesis --registro FICT-0001 --modo existencia || true
mkdir -p borradores
echo "Resulta aplicable [[CITA:FICT-0001]], pues la verificación forense de citas es indispensable." > borradores/parrafo.md
$PY "$PLUGIN/scripts/ensamblar_documento.py" borradores/parrafo.md --salida salidas/parrafo.md
echo "Párrafo ensamblado en salidas/parrafo.md con nota de evidencia." > "$MENSAJE"
