#!/usr/bin/env bash
# Obtiene la candidata EXACTA (un commit) del repositorio del constructor con una clave de despliegue de SOLO LECTURA.
# La clave llega por env solo a este paso, se escribe con permisos 600 y se borra al salir. Nunca set -x.
set -euo pipefail
: "${CLAVE_DESPLIEGUE:?falta la clave de despliegue}" "${REPO_CONSTRUCTOR:?falta vars.REPO_CONSTRUCTOR}" "${CANDIDATA:?falta la candidata}"
clave=$(mktemp)
trap 'rm -f "$clave"' EXIT
chmod 600 "$clave"
printf '%s\n' "$CLAVE_DESPLIEGUE" > "$clave"
export GIT_SSH_COMMAND="ssh -i $clave -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$PWD/ejecutor/ejecutor/known_hosts"
git init -q candidata
git -C candidata fetch -q --depth 1 "git@github.com:${REPO_CONSTRUCTOR}.git" "$CANDIDATA"
git -C candidata checkout -q FETCH_HEAD
[ "$(git -C candidata rev-parse HEAD)" = "$CANDIDATA" ] || { echo "el commit obtenido no es la candidata pedida"; exit 1; }
# Los casos holdout contaminados del constructor nunca participan: la reserva es la de ESTE repositorio.
find candidata -type d -name 'holdout-*' -prune -exec rm -rf {} +
echo "candidata ${CANDIDATA} obtenida"
