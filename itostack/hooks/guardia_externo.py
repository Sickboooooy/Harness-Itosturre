#!/usr/bin/env python3
"""PreToolUse(mcp__*): compuerta humana para acciones hacia afuera y bloqueo de citas sin evidencia.

Leer en conectores (correo, Drive, Slack, Notion) pasa libre. Enviar, publicar, compartir o
programar requiere aprobación; y si el contenido trae citas sin evidencia vigente, se deniega.
"""

from __future__ import annotations

import fnmatch
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402
from guardia_escritura import citas_sin_evidencia  # noqa: E402

RE_ACCION_EXTERNA = re.compile(
    r"(?:^|_|-)(send|post|reply|forward|publish|schedule|share|upload|comment|create[_-]?draft|update[_-]?draft|create[_-]?event|create[_-]?pages?|deploy|tweet|invite)(?:_|-|$)",
    re.IGNORECASE,
)


def cadenas(valor) -> list[str]:
    if isinstance(valor, str):
        return [valor]
    if isinstance(valor, dict):
        return [t for v in valor.values() for t in cadenas(v)]
    if isinstance(valor, list):
        return [t for v in valor for t in cadenas(v)]
    return []


def principal() -> int:
    entrada = _comun.leer_entrada()
    herramienta = entrada.get("tool_name", "")
    if not herramienta.startswith("mcp__"):
        return 0
    accion = herramienta.split("__")[-1]
    if not RE_ACCION_EXTERNA.search(accion):
        return 0
    permitidas: list[str] = []
    if _comun.tiene_itostack(entrada):
        config = _comun.configuracion(entrada)
        problemas = citas_sin_evidencia("\n".join(cadenas(entrada.get("tool_input") or {})), config)
        if problemas:
            _comun.denegar("el contenido que saldría hacia afuera trae citas sin evidencia vigente: " + "; ".join(problemas[:5]))
            return 0
        permitidas = config.get("acciones_externas_permitidas") or []
    # Lista que cura el operador en .itostack/config.json (p. ej. responderle a él mismo por Telegram).
    if any(fnmatch.fnmatchcase(herramienta, patron) for patron in permitidas):
        return 0
    _comun.compuerta_humana(entrada, f"compuerta humana: «{herramienta}» envía o publica fuera de la máquina. Confirma destinatario y contenido.")
    return 0


if __name__ == "__main__":
    sys.exit(_comun.ejecutar(principal, "PreToolUse", "cerrado"))
