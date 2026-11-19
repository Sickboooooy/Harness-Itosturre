#!/usr/bin/env python3
"""Prueba de humo de las guardias de una candidata (CR-2, verificación previa del ejecutor aislado).

Ejecuta el comando EXACTO de la guardia PreToolUse de Bash declarado en `<plugin>/hooks/hooks.json`, con el shell
POSIX con el que Claude Code corre los hooks, ante dos acciones:
- una que la guardia debe denegar (un push forzado): exige una decisión «deny» EMITIDA POR LA GUARDIA (salida 0 con
  JSON). Una salida 2 no basta: es el respaldo «falla cerrado» (p. ej., sin node), que deniega TODO; evaluar así
  mediría otra cosa;
- una inocua (control): no debe denegarse. Una guardia que deniega todo tampoco funciona.
No sustituye a las pruebas; confirma que en ESTE ejecutor (node, python y bash instalados) las guardias evalúan.
Uso: humo_guardias.py <raíz del plugin> [--bash <ruta>]   · código 0 PASS · 1 FAIL
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ACCION_PROHIBIDA = "git push --force origin main"
ACCION_INOCUA = "echo itostack-humo"


def comando_guardia_bash(plugin: Path) -> str | None:
    try:
        configuracion = json.loads((plugin / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        grupos = [g for g in configuracion["hooks"]["PreToolUse"] if g.get("matcher") == "Bash"]
        comandos = [h["command"] for g in grupos for h in g["hooks"] if h.get("type") == "command"]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
    return comandos[0] if len(comandos) == 1 else None


def _decision(bash: str, comando: str, accion: str, entorno: dict) -> tuple[int, str | None, str]:
    """(código de salida, decisión emitida o None, detalle)."""
    with tempfile.TemporaryDirectory() as proyecto:
        entrada = json.dumps({"tool_name": "Bash", "tool_input": {"command": accion}, "cwd": proyecto, "hook_event_name": "PreToolUse"})
        try:
            salida = subprocess.run([bash, "-c", comando], input=entrada, capture_output=True, text=True, encoding="utf-8",
                                    errors="replace", env=entorno, cwd=proyecto, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as error:
            return -1, None, str(error)
    if salida.returncode != 0 or not salida.stdout.strip():
        return salida.returncode, None, (salida.stderr or salida.stdout).strip()[-200:]
    try:
        return 0, json.loads(salida.stdout)["hookSpecificOutput"]["permissionDecision"], ""
    except (ValueError, KeyError, TypeError):
        return 0, "ilegible", salida.stdout.strip()[:200]


def comprobar(plugin: Path, bash: str | None, entorno_base: dict | None = None) -> list[str]:
    """Problemas; vacío = la guardia de Bash de esta candidata evalúa en este ejecutor (deniega lo prohibido y deja
    pasar lo inocuo)."""
    if not bash:
        return ["no hay bash: los hooks no podrían ejecutarse"]
    comando = comando_guardia_bash(plugin)
    if comando is None:
        return ["hooks.json no declara exactamente una guardia PreToolUse para Bash"]
    entorno = {k: v for k, v in (os.environ if entorno_base is None else entorno_base).items() if not k.startswith("ITOSTACK_")}
    entorno.update({"CLAUDE_PLUGIN_ROOT": plugin.resolve().as_posix(), "PYTHONUTF8": "1"})
    problemas = []
    codigo, decision, detalle = _decision(bash, comando, ACCION_PROHIBIDA, entorno)
    if codigo == 2:
        problemas.append(f"la guardia no evaluó: denegó por el respaldo «falla cerrado» (¿falta node o python?): {detalle}")
    elif decision != "deny":
        problemas.append(f"la guardia no deniega «{ACCION_PROHIBIDA}» (salida {codigo}, decisión {decision!r}) {detalle}".rstrip())
    codigo, decision, detalle = _decision(bash, comando, ACCION_INOCUA, entorno)
    if codigo != 0 or decision in ("deny", "ilegible"):
        problemas.append(f"la guardia no deja pasar la acción inocua «{ACCION_INOCUA}» (salida {codigo}, decisión {decision!r}) {detalle}".rstrip())
    return problemas


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("plugin", type=Path)
    analizador.add_argument("--bash", default=shutil.which("bash"))
    args = analizador.parse_args()
    problemas = comprobar(args.plugin, args.bash)
    for p in problemas:
        print(f"✘ {p}")
    print("guardias: " + ("PASS" if not problemas else "FAIL (no se evalúa)"))
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(principal())
