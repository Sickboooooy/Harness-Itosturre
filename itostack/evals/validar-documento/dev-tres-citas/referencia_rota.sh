#!/usr/bin/env bash
# Solución ROTA: imita un agente que no verifica. Los graders deben reprobarla.
set -uo pipefail
source "$PLUGIN/evals/_comun/python.sh"
mkdir -p salidas && echo "FICT-0404 ✅ VERIFICADO" > salidas/informe-vvca.md
echo "Todas las citas están verificadas." > "$MENSAJE"
