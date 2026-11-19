#!/usr/bin/env bash
# Instala Claude Code en el laboratorio (como «lab», por stdin), fijado a la versión del contrato de CR-3 (P2).
# Instalador oficial; no inicia sesión: el laboratorio corre SIN credenciales.
set -euo pipefail
VERSION=2.1.327
curl -fsSL https://claude.ai/install.sh | bash -s "$VERSION" >/tmp/instalacion.log 2>&1 || { tail -20 /tmp/instalacion.log; exit 1; }
export PATH="$HOME/.local/bin:$PATH"
echo "instalado: $(claude --version)"
