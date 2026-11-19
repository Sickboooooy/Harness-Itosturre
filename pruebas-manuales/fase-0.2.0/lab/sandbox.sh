#!/usr/bin/env bash
# Instala el backend de sandbox de Claude Code en Linux (bubblewrap y socat), como root por stdin.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq bubblewrap socat >/dev/null
echo "sandbox: $(bwrap --version) · $(socat -V 2>/dev/null | grep -m1 'socat version' || echo socat)"
