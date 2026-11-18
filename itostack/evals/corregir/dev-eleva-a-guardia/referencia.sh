#!/usr/bin/env bash
# Solución de referencia: demuestra que el caso es resoluble con las herramientas del plugin.
set -uo pipefail
python3 "$PLUGIN/scripts/registrar_correccion.py" pendientes
python3 "$PLUGIN/scripts/registrar_correccion.py" proponer --clave espera-scraper-waitfortimeout --nivel 2 --artefacto "guardias/lint_itosturre.py (regla IT007)" --descripcion "Prohibir waitForTimeout: esperar por condición observable."
echo "Propuesta en .itostack/mejora/propuesta.md (nivel 2: lint)." > "$MENSAJE"
