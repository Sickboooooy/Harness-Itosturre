#!/usr/bin/env bash
# Configura la distribución itostack-lab (se ejecuta como root dentro de ella, por stdin).
# Aislamiento estructural: sin unidades de Windows montadas, sin interoperabilidad (no puede lanzar programas de Windows),
# sin PATH de Windows, usuario «lab» sin contraseña (cuenta bloqueada) y sin sudo. Idempotente.
set -euo pipefail
cat > /etc/wsl.conf <<'CONF'
[automount]
enabled = false
mountFsTab = false

[interop]
enabled = false
appendWindowsPath = false

[user]
default = lab
CONF
if ! id lab >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash lab
fi
passwd --lock lab >/dev/null          # sin contraseña: nadie la conoce ni hay que guardarla
gpasswd --delete lab sudo >/dev/null 2>&1 || true
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 git curl ca-certificates bash >/dev/null
echo "configurado: $(. /etc/os-release && echo "$PRETTY_NAME") · python $(python3 --version | cut -d' ' -f2) · git $(git --version | cut -d' ' -f3)"
