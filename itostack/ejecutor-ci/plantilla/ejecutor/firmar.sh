#!/usr/bin/env bash
# Firma el manifiesto con la clave PRIVADA del ejecutor (secreto del environment; nunca en el constructor).
# La clave existe solo durante este paso, con permisos 600, y se borra al salir. Nunca set -x.
set -euo pipefail
: "${CLAVE_FIRMA:?falta la clave de firma}"
clave=$(mktemp)
trap 'rm -f "$clave"' EXIT
chmod 600 "$clave"
printf '%s\n' "$CLAVE_FIRMA" > "$clave"
ssh-keygen -Y sign -f "$clave" -n itostack-holdout salida/manifiesto.json
test -s salida/manifiesto.json.sig
echo "manifiesto firmado"
