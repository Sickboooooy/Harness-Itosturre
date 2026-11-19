#!/usr/bin/env python3
"""PreToolUse(Read|Grep|Glob): la reserva holdout no se lee desde la sesión que mejora las skills (N-08).

Deniega leer un caso `holdout-*`, las búsquedas dirigidas a uno (ruta o glob) y las búsquedas de contenido sobre
`evals/` o `evals/<skill>/`, que la recorren sin nombrarla. El guardia de Bash repite la regla para cat/grep/sed y
similares. Límites conocidos: una búsqueda sobre todo el repositorio o un intérprete (python -c) todavía pueden
tocarla; la protección completa es separar físicamente la reserva del árbol de trabajo (pendiente). El operador la
abre con ITOSTACK_EDITAR_HOLDOUT=1.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402

CAMPOS = {"Read": ("file_path",), "Grep": ("path", "glob"), "Glob": ("pattern", "path")}


def apunta_a_holdout(nombre: str, datos: dict, cwd: str | None = None) -> str | None:
    for campo in CAMPOS.get(nombre, ()):
        valor = str(datos.get(campo) or "")
        if "holdout-" in valor.replace("\\", "/").lower():  # Windows no distingue mayúsculas: HOLDOUT- es lo mismo
            return valor
    if nombre == "Grep":
        # Una búsqueda de contenido sobre evals/ o evals/<skill>/ recorre la reserva aunque no la nombre; sin ruta,
        # Grep busca desde el directorio de trabajo.
        base = Path(str(datos.get("path") or cwd or os.getcwd()))
        base = base if base.is_absolute() else Path(cwd or os.getcwd()) / base
        if base.is_dir() and any(p.name.lower().startswith("holdout-") for p in [*base.glob("*"), *base.glob("*/*")] if p.is_dir()):
            return str(datos.get("path") or base)
    return None


def principal() -> int:
    entrada = _comun.leer_entrada()
    if os.environ.get("ITOSTACK_EDITAR_HOLDOUT") == "1":
        return 0
    valor = apunta_a_holdout(entrada.get("tool_name", ""), entrada.get("tool_input") or {}, entrada.get("cwd"))
    if valor:
        _comun.denegar(
            f"«{valor}» es parte de la reserva holdout: el agente que mejora una skill no puede verla, o el holdout "
            "deja de medir generalización. Trabaja con los casos de desarrollo."
        )
    return 0


if __name__ == "__main__":
    sys.exit(_comun.ejecutar(principal, "PreToolUse", "cerrado"))
