#!/usr/bin/env bash
set -euo pipefail
CASO="$(cd "$(dirname "$0")" && pwd)"
exec bash "$CASO/../../_comun/preparar.sh" "$CASO" juridico dictamen_ia_holdout.md
