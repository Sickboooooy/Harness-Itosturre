#!/usr/bin/env python3
"""PreToolUse(Bash): bloquea exfiltración, fusiones de agente, commits en inglés y atajos sin evidencia."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402

LOCAL = r"(?:127\.0\.0\.1|localhost|\[::1\])"
VERBOS_INGLES = {
    "add", "adds", "added", "fix", "fixes", "fixed", "update", "updates", "updated", "remove", "removes", "removed",
    "refactor", "refactors", "implement", "implements", "create", "creates", "change", "changes", "improve", "improves",
    "initial", "bump", "delete", "deletes", "rename", "move", "use", "make", "set", "clean", "cleanup", "wip", "merge",
    "revert", "support", "allow", "enable", "disable", "handle", "introduce", "upgrade", "tweak", "minor",
}

REGLAS: list[tuple[str, re.Pattern, str]] = [
    ("denegar", re.compile(r"\bgit\s+push\b.*(?:--force(?!-with-lease)|\s-f\b)"),
     "push forzado prohibido: reescribe historia compartida. Usa una rama nueva o pide al operador que lo haga."),
    ("preguntar", re.compile(r"\bgit\s+push\b.*--force-with-lease"),
     "push con --force-with-lease: requiere confirmación humana."),
    ("preguntar", re.compile(r"\bgit\s+push\b[^|;&]*\b(?:main|master)\b"),
     "push directo a la rama principal: requiere confirmación humana."),
    ("denegar", re.compile(r"\bgh\s+pr\s+merge\b"),
     "un agente no fusiona PRs. Deja el PR en borrador con evidencia; la fusión la decide una persona."),
    ("denegar", re.compile(r"\bgit\s+commit\b.*--no-verify|\bgit\s+push\b.*--no-verify"),
     "--no-verify salta las guardias. Corrige lo que el hook señala en lugar de evadirlo."),
    ("denegar", re.compile(r"\brm\s+-[a-zA-Z]*[rR][a-zA-Z]*\s+(?:-[a-zA-Z]+\s+)*(?:/|~|\$HOME|\.\.?)(?:/?\s|/?$)"),
     "borrado recursivo de una raíz (/, ~, ., ..). Borra rutas explícitas dentro del proyecto."),
    ("denegar", re.compile(r"\b(?:scp|sftp|rsync|rclone)\b(?![^|;&]*\b" + LOCAL + r")[^|;&]*(?:@|::|:/|\bremote:)"),
     "copia hacia un host remoto. Los datos legales nunca salen de la máquina."),
    ("denegar", re.compile(r"\bcurl\b(?![^|;&]*" + LOCAL + r")[^|;&]*(?:\s-T\b|--upload-file|\s-F\b|--form\b|--data(?:-binary|-raw|-urlencode)?\s+@|\s-d\s+@)"),
     "envío de archivos con curl a un servidor externo. Los datos legales nunca salen de la máquina."),
    ("denegar", re.compile(r"\bwget\b[^|;&]*--post-file"),
     "envío de archivos con wget. Los datos legales nunca salen de la máquina."),
    ("denegar", re.compile(r"\b(?:gh\s+gist\s+create|aws\s+s3\s+(?:cp|sync|mv)|gsutil\s+(?:cp|rsync)|az\s+storage\s+blob\s+upload)\b"),
     "subida a un servicio en la nube. Los datos legales nunca salen de la máquina."),
    ("denegar", re.compile(r"\b(?:curl|wget|http|httpie|lynx)\b[^|;&]*(?:scjn\.gob\.mx|dof\.gob\.mx|diputados\.gob\.mx)"),
     "consulta a un portal oficial sin captura forense. Usa: python3 <raíz itostack>/scripts/verificar.py (tesis|url) …"),
    ("denegar", re.compile(r"\b(?:pip3?|uv\s+pip|poetry|pipenv)\s+(?:install|add)\b[^|;&]*\b(?:fastapi|psycopg2?|psycopg2-binary|supabase|pymongo)\b"),
     "dependencia fuera del stack del MVP (Flask + SQLite). Consulta al operador antes de cambiar el stack."),
    ("denegar", re.compile(r"\b(?:npm|pnpm|yarn|bun)\s+(?:i|install|add)\b[^|;&]*(?:@supabase/|\bpg\b|\bmongodb\b|\bmysql2?\b)"),
     "dependencia fuera del stack del MVP (SQLite). Consulta al operador antes de cambiar el stack."),
]


def mensajes_commit(comando: str) -> list[str]:
    if not re.search(r"\bgit\s+commit\b", comando):
        return []
    mensajes = re.findall(r"""-m\s+(?:"((?:[^"\\]|\\.)*)"|'([^']*)')""", comando)
    resultado = [doble or simple for doble, simple in mensajes]
    heredoc = re.search(r"<<\s*'?(\w+)'?\s*\n(.*?)\n\1", comando, flags=re.S)
    if heredoc:
        resultado.append(heredoc.group(2))
    return [m.strip() for m in resultado if m.strip()]


def problema_commit(mensaje: str) -> str | None:
    titulo = mensaje.splitlines()[0].strip()
    sin_prefijo = re.sub(r"^\w+(?:\([^)]*\))?!?:\s*", "", titulo)
    primera = re.sub(r"[^a-záéíóúñü]", "", sin_prefijo.split()[0].lower()) if sin_prefijo.split() else ""
    if primera in VERBOS_INGLES:
        return f"commit en inglés («{titulo}»). Escribe commits descriptivos en español: «Agrega…», «Corrige…», «Elimina…»."
    if len(sin_prefijo) < 12:
        return f"mensaje de commit poco descriptivo («{titulo}»). Explica qué cambia y por qué, en español."
    return None


def evaluar(comando: str) -> tuple[str, str] | None:
    for accion, patron, razon in REGLAS:
        if patron.search(comando):
            return accion, razon
    for mensaje in mensajes_commit(comando):
        problema = problema_commit(mensaje)
        if problema:
            return "denegar", problema
    if re.search(r"\bgh\s+pr\s+create\b", comando) and "--draft" not in comando:
        return "denegar", "los PRs de agente se abren en borrador: agrega --draft y adjunta la evidencia de verificación."
    return None


def principal() -> int:
    entrada = _comun.leer_entrada()
    comando = (entrada.get("tool_input") or {}).get("command", "")
    decision = evaluar(comando)
    if decision:
        accion, razon = decision
        (_comun.denegar if accion == "denegar" else _comun.preguntar)(razon)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
