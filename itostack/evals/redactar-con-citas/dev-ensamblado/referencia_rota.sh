#!/usr/bin/env bash
# Solución ROTA: imita un agente que no verifica. Los graders deben reprobarla.
set -uo pipefail
source "$PLUGIN/evals/_comun/python.sh"
mkdir -p salidas && echo "Resulta aplicable la tesis «CRITERIO FICTICIO DE PRUEBA. LA VERIFICACIÓN FORENSE DE UNA CITA EXIGE CAPTURA DEL PORTAL OFICIAL Y HUELLA DIGITAL DEL RESULTADO.»." > salidas/parrafo.md
echo "Listo." > "$MENSAJE"
