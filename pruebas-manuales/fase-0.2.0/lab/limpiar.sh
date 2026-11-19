#!/usr/bin/env bash
# Limpieza segura de los temporales de `claude plugin eval` del laboratorio (como «lab», por stdin).
# - Solo /tmp/claude-eval-* que sean directorios reales del propio usuario (no enlaces).
# - Abre permisos únicamente sobre DIRECTORIOS encontrados con find -P (no sigue enlaces) y -xdev (no cruza montajes):
#   en Linux el ejecutor sella lo escrito por el agente con modo 000, y sin abrirlo no se puede borrar.
# - Lista los enlaces simbólicos, los borra SIN seguirlos, borra el resto con --one-file-system y verifica que los
#   destinos de los enlaces sigan intactos. No ejecuta git ni nada que cargue configuración desde ahí dentro.
set -uo pipefail
quedan=0
for t in /tmp/claude-eval-*; do
  [ -e "$t" ] || continue
  if [ -L "$t" ] || [ ! -d "$t" ] || [ "$(stat -c %U "$t")" != "$(id -un)" ]; then echo "  omito $t (no es un directorio propio)"; continue; fi
  echo "== $t"
  find -P "$t" -xdev -type d -exec chmod u+rwx {} + 2>/dev/null
  find -P "$t" -xdev -type d -exec chmod u+rwx {} + 2>/dev/null   # segunda pasada: subdirectorios recién abiertos
  echo "  enlaces simbólicos:"
  find -P "$t" -xdev -type l -printf '    %p -> %l\n' | sed "s|$t|.|"
  [ -z "$(find -P "$t" -xdev -type l -print -quit)" ] && echo "    ninguno"
  destinos=$(find -P "$t" -xdev -type l -printf '%l\n' | sort -u)
  huella() { for d in $destinos; do [ -e "$d" ] && find -P "$d" -maxdepth 2 -printf '%p %s %T@\n' 2>/dev/null; done | sha256sum; }
  antes=$(huella)
  find -P "$t" -xdev -type l -delete
  rm -r --one-file-system -- "$t"
  [ "$antes" = "$(huella)" ] && echo "  destinos de los enlaces intactos" || { echo "  FALLA: los destinos cambiaron"; quedan=$((quedan + 1)); }
  [ -e "$t" ] && { echo "  FALLA: el temporal sigue"; quedan=$((quedan + 1)); } || echo "  temporal borrado"
done
exit $quedan
