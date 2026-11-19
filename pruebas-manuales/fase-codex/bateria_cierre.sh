#!/usr/bin/env bash
# Batería determinista del cierre de 0.1.2 (paso 4 del protocolo). Cada paso imprime PASS/FAIL con su salida final.
# Uso (Git Bash, desde la raíz del repo): bash pruebas-manuales/fase-codex/bateria_cierre.sh
set -u
RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
PLUGIN="$RAIZ/itostack"
export PYTHONUTF8=1
unset ITOSTACK_PROYECTO ITOSTACK_MODO
fallos=0

paso() {
  local nombre="$1"; shift
  local salida codigo
  salida="$("$@" 2>&1)"; codigo=$?
  if [ $codigo -eq 0 ]; then echo "PASS  $nombre"; else echo "FAIL  $nombre (código $codigo)"; fallos=$((fallos + 1)); fi
  printf '%s\n' "$salida" | tail -n 4 | sed 's/^/      /'
}

cd "$PLUGIN" || exit 2
echo "itostack $(python -c 'import json;print(json.load(open(".claude-plugin/plugin.json",encoding="utf-8"))["version"])' 2>/dev/null) · $(date -u +%Y-%m-%dT%H:%M:%SZ)"
paso "pytest (suite completa)" python -m pytest tests -q -p no:cacheprovider
paso "autoprueba (casos de eval con andamiaje real)" python evals/autoprueba.py
paso "lint completo (scripts hooks guardias evals)" python guardias/lint_itosturre.py scripts hooks guardias evals
paso "lint --diff (cobertura informada)" python guardias/lint_itosturre.py --diff
paso "tsc --noEmit" bash -c "cd scripts && ./node_modules/.bin/tsc --noEmit -p ."
paso "claude plugin validate" claude plugin validate "$PLUGIN"
echo
if [ $fallos -eq 0 ]; then echo "BATERÍA: PASS"; else echo "BATERÍA: FAIL ($fallos paso(s))"; fi
exit $fallos
