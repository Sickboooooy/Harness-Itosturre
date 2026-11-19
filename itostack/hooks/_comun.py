"""Utilidades compartidas por los hooks de itostack (solo biblioteca estándar)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

RAIZ_PLUGIN = Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or Path(__file__).resolve().parent.parent)
sys.path.insert(0, str(RAIZ_PLUGIN / "scripts"))
sys.path.insert(0, str(RAIZ_PLUGIN / "guardias"))

from nucleo import config as cfg  # noqa: E402


def leer_entrada() -> dict:
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return {}


def proyecto(entrada: dict) -> Path:
    return cfg.raiz_proyecto(entrada.get("cwd") or os.getcwd())


def configuracion(entrada: dict) -> dict:
    return cfg.cargar(proyecto(entrada))


def tiene_itostack(entrada: dict) -> bool:
    return (proyecto(entrada) / cfg.DIR_ITOSTACK).is_dir()


def modos_validos(config: dict) -> tuple[str, ...]:
    return ("real", "fixture") if config["modo"] == "fixture" else ("real",)


def _emitir(datos: dict) -> None:
    sys.stdout.write(json.dumps(datos, ensure_ascii=False))
    sys.stdout.flush()


def denegar(razon: str) -> None:
    _emitir({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": f"itostack: {razon}"}})


def preguntar(razon: str) -> None:
    _emitir({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": f"itostack: {razon}"}})


# Modos de permiso en los que el anfitrión SÍ muestra la pregunta al operador. En los demás (auto, dontAsk,
# bypassPermissions, sin dato) un «ask» se resuelve solo: así pasó el push a main de B-02 sin que nadie lo viera.
MODOS_QUE_PREGUNTAN = {"default", "acceptEdits", "plan"}


def compuerta_humana(entrada: dict, razon: str) -> None:
    """Pide confirmación humana solo donde el anfitrión de verdad pregunta; en otro modo, deniega (falla cerrado)."""
    modo = entrada.get("permission_mode")
    if modo in MODOS_QUE_PREGUNTAN:
        preguntar(razon)
        return
    denegar(
        f"{razon} En el modo de permisos «{modo or 'desconocido'}» el anfitrión aprueba las preguntas sin mostrarlas, "
        "así que la compuerta humana deniega. Que el operador lo haga él mismo, o que cambie al modo default para confirmarlo."
    )


def contexto(evento: str, texto: str) -> None:
    _emitir({"hookSpecificOutput": {"hookEventName": evento, "additionalContext": texto}})


def bloquear_cierre(razon: str) -> None:
    _emitir({"decision": "block", "reason": f"itostack: {razon}"})


def ejecutar(principal, evento: str = "PreToolUse", falla: str = "cerrado") -> int:
    """Corre un hook sin dejar que una excepción se convierta en permiso.

    Guardias (PreToolUse, falla cerrado): cualquier error interno deniega la acción.
    Hooks informativos (falla abierto): el error se reporta por stderr y la sesión sigue.
    """
    try:
        principal()
    except Exception as error:  # noqa: BLE001 — aquí se captura todo a propósito
        detalle = f"{type(error).__name__}: {error}"
        if falla == "cerrado" and evento == "PreToolUse":
            denegar(f"la guardia falló internamente ({detalle}); falla cerrado: acción bloqueada.")
        else:
            sys.stderr.write(f"itostack: hook omitido por error interno ({detalle})\n")
    return 0
