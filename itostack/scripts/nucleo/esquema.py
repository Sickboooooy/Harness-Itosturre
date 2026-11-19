"""Validador mínimo de JSON Schema (biblioteca estándar): el subconjunto que usan los esquemas de evals/esquemas/.

Soporta: type (uno o varios), const, enum, required, properties, additionalProperties: false, items, minItems,
minimum, maximum, minLength, pattern y $ref a #/$defs/. Es más estricto que JSON Schema en un punto deliberado:
«integer» exige un entero JSON de verdad (ni booleano ni decimal como 1.0). Las pruebas lo comparan con `jsonschema`
como oráculo independiente; los scripts de uso diario no dependen de esa biblioteca.
"""

from __future__ import annotations

import re

_TIPOS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: type(v) is int,
    "number": lambda v: type(v) in (int, float),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def errores(valor, esquema: dict, raiz: dict | None = None, ruta: str = "$") -> list[str]:
    """Todos los incumplimientos de `valor` frente a `esquema` (vacío = cumple)."""
    raiz = raiz if raiz is not None else esquema
    if "$ref" in esquema:
        nombre = esquema["$ref"].removeprefix("#/$defs/")
        return errores(valor, raiz["$defs"][nombre], raiz, ruta)
    tipos = esquema.get("type")
    if tipos is not None:
        tipos = [tipos] if isinstance(tipos, str) else tipos
        if not any(_TIPOS[t](valor) for t in tipos):
            return [f"{ruta}: se esperaba {' o '.join(tipos)}"]
    salida: list[str] = []
    if "const" in esquema and not _igual(valor, esquema["const"]):
        salida.append(f"{ruta}: debe valer {esquema['const']!r}")
    if "enum" in esquema and not any(_igual(valor, opcion) for opcion in esquema["enum"]):
        salida.append(f"{ruta}: {valor!r} no está en {esquema['enum']}")
    if isinstance(valor, dict):
        propiedades = esquema.get("properties", {})
        salida += [f"{ruta}.{campo}: falta" for campo in esquema.get("required", []) if campo not in valor]
        if esquema.get("additionalProperties") is False:
            salida += [f"{ruta}.{campo}: campo no previsto" for campo in valor if campo not in propiedades]
        for campo, subesquema in propiedades.items():
            if campo in valor:
                salida += errores(valor[campo], subesquema, raiz, f"{ruta}.{campo}")
    if isinstance(valor, list):
        if len(valor) < esquema.get("minItems", 0):
            salida.append(f"{ruta}: menos de {esquema['minItems']} elementos")
        if "items" in esquema:
            for i, elemento in enumerate(valor):
                salida += errores(elemento, esquema["items"], raiz, f"{ruta}[{i}]")
    if type(valor) in (int, float):
        if "minimum" in esquema and valor < esquema["minimum"]:
            salida.append(f"{ruta}: menor que {esquema['minimum']}")
        if "maximum" in esquema and valor > esquema["maximum"]:
            salida.append(f"{ruta}: mayor que {esquema['maximum']}")
    if isinstance(valor, str):
        if len(valor) < esquema.get("minLength", 0):
            salida.append(f"{ruta}: más corto que {esquema['minLength']}")
        if "pattern" in esquema and not re.search(esquema["pattern"], valor):
            salida.append(f"{ruta}: no cumple el patrón {esquema['pattern']}")
    return salida


def _igual(a, b) -> bool:
    """Igualdad JSON: un booleano no es igual a 1 ni a 0."""
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    return a == b
