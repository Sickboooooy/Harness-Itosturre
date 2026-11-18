#!/usr/bin/env bash
# Andamiaje común de los casos (scaffold_script de claude plugin eval y de autoprueba.py).
# Corre con cwd = espacio de trabajo aislado del caso.
# Uso: preparar.sh DIR_DEL_CASO [juridico|desarrollo] [documento.md ...]
set -euo pipefail
CASO="$1"
PERFIL="${2:-juridico}"
shift 2 || true
PLUGIN="$(cd "$CASO/../../.." && pwd)"

python3 "$PLUGIN/scripts/inicializar.py" --proyecto . --perfil "$PERFIL" --modo fixture \
  --sjf-fixture "$PLUGIN/evals/fixtures/sjf/basico.json" --silencioso

if [ "$PERFIL" = "desarrollo" ]; then
  cp -R "$PLUGIN/evals/fixtures/app_flask_simulada/." .
fi
for documento in "$@"; do
  cp "$PLUGIN/evals/fixtures/documentos/$documento" .
done
if [ -d "$CASO/archivos" ]; then
  cp -R "$CASO/archivos/." .
fi

git init -q
git add -A
git -c user.name=itostack-eval -c user.email=eval@localhost commit -qm "Estado inicial del caso" >/dev/null 2>&1 || true
