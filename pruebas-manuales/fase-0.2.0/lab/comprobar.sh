#!/usr/bin/env bash
# Comprobaciones previas del laboratorio (como «lab», por stdin). Cada línea: PASS/FAIL. Código 0 solo si todas pasan;
# si alguna falla, NO se ejecuta ninguna evaluación.
set -uo pipefail
fallos=0
ok() { echo "PASS  $1"; }
mal() { echo "FAIL  $1"; fallos=$((fallos + 1)); }

[ "$(id -un)" = "lab" ] && ok "corre como «lab», no como root" || mal "no corre como «lab» ($(id -un))"
if id -nG | tr ' ' '\n' | grep -qx sudo; then mal "«lab» pertenece a sudo"; else ok "«lab» sin sudo"; fi
montadas=""
for unidad in /mnt/?; do
  [ -d "$unidad" ] || continue
  if mountpoint -q "$unidad" || [ -n "$(ls -A "$unidad" 2>/dev/null)" ]; then montadas="$montadas $unidad"; fi
done
if grep -qE '^[^ ]+ /mnt/[a-z] ' /proc/mounts; then montadas="$montadas (en /proc/mounts)"; fi
if [ -e /mnt/c/Users ] || [ -e /mnt/c/Windows ]; then montadas="$montadas /mnt/c legible"; fi
[ -z "$montadas" ] && ok "ninguna unidad de Windows montada ni legible (los directorios /mnt/<letra> existen vacíos)" || mal "unidades de Windows accesibles:$montadas"
if [ -e /proc/sys/fs/binfmt_misc/WSLInterop ] && grep -q enabled /proc/sys/fs/binfmt_misc/WSLInterop 2>/dev/null; then mal "interoperabilidad con Windows activa"; else ok "interoperabilidad con Windows desactivada"; fi
if command -v cmd.exe >/dev/null 2>&1 || command -v powershell.exe >/dev/null 2>&1; then mal "ejecutables de Windows en el PATH"; else ok "sin ejecutables de Windows en el PATH"; fi
credenciales=$(env | grep -iE '^(AWS_|AZURE_|GOOGLE_|GCP_|GITHUB_TOKEN|GH_TOKEN|GITLAB|ANTHROPIC_|CLAUDE_CODE_OAUTH|OPENAI_|HF_TOKEN|NPM_TOKEN)' | cut -d= -f1 | tr '\n' ' ')
[ -z "$credenciales" ] && ok "sin variables de credenciales en el entorno" || mal "variables de credenciales: $credenciales"
encontrados=""
for ruta in ~/.aws ~/.ssh ~/.config/gh ~/.git-credentials ~/.netrc ~/.docker/config.json ~/.npmrc ~/.codex ~/.claude/.credentials.json; do
  [ -e "$ruta" ] && encontrados="$encontrados $ruta"
done
[ -z "$encontrados" ] && ok "sin almacenes de credenciales en el home" || mal "almacenes de credenciales:$encontrados"
archivos=$(find ~/itostack -type f 2>/dev/null | wc -l)
if [ "$archivos" -lt 100 ] || [ ! -f ~/itostack/scripts/nucleo/procedencia.py ] || [ ! -f ~/itostack/.claude-plugin/plugin.json ]; then
  mal "la copia del plugin falta o está incompleta ($archivos archivos)"
else
  holdout=$(find ~/itostack -name 'holdout-*' | wc -l)
  [ "$holdout" = "0" ] && ok "copia del plugin completa ($archivos archivos) y sin casos holdout" || mal "la copia contiene $holdout entradas holdout"
fi
echo
[ $fallos -eq 0 ] && echo "COMPROBACIONES: PASS" || echo "COMPROBACIONES: FAIL ($fallos)"
exit $fallos
