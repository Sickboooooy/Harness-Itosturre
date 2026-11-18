"""Núcleo de itostack: lógica determinista compartida por scripts, hooks y evals.

La decisión de veredictos vive aquí (Python) y no en los scripts de navegador (TypeScript):
el navegador solo observa y captura evidencia; este núcleo compara y decide.
"""

import sys

VERSION = "0.1.1"
HERRAMIENTA = f"itostack/{VERSION}"

# En Windows, sin modo UTF-8, una tubería usa cp1252 y truena al imprimir ✅ ⚠ ❌ o al leer JSON con acentos.
for _flujo in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
