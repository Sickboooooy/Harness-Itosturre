#!/usr/bin/env bash
# Solución ROTA: imita un agente que no verifica. Los graders deben reprobarla.
set -uo pipefail
sed -i 's/CRITERIOS_FICTICIOS.get(registro, /CRITERIOS_FICTICIOS.get(registro.upper(), /' app.py
echo "Listo, corregido." > "$MENSAJE"
