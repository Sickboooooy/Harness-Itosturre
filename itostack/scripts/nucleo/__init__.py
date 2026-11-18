"""Núcleo de itostack: lógica determinista compartida por scripts, hooks y evals.

La decisión de veredictos vive aquí (Python) y no en los scripts de navegador (TypeScript):
el navegador solo observa y captura evidencia; este núcleo compara y decide.
"""

VERSION = "0.1.0"
HERRAMIENTA = f"itostack/{VERSION}"
