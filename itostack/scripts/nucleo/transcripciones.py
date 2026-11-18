"""Lectura tolerante de transcripciones JSONL de Claude Code (~/.claude/projects/*/*.jsonl)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass
class Mensaje:
    rol: str
    textos: list[str] = field(default_factory=list)
    usos_herramienta: list[dict] = field(default_factory=list)
    resultados_herramienta: list[dict] = field(default_factory=list)
    uso_tokens: dict = field(default_factory=dict)
    marca_tiempo: str = ""
    sesion: str = ""


def _texto_de(contenido) -> str:
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        partes = []
        for parte in contenido:
            if isinstance(parte, dict):
                partes.append(_texto_de(parte.get("text", parte.get("content", ""))))
            else:
                partes.append(str(parte))
        return "\n".join(partes)
    return "" if contenido is None else str(contenido)


def leer(ruta: Path) -> Iterator[Mensaje]:
    with open(ruta, encoding="utf-8", errors="replace") as manejador:
        for linea in manejador:
            linea = linea.strip()
            if not linea:
                continue
            try:
                evento = json.loads(linea)
            except json.JSONDecodeError:
                continue
            if evento.get("type") not in {"user", "assistant"}:
                continue
            mensaje = evento.get("message") or {}
            resultado = Mensaje(
                rol=mensaje.get("role") or evento["type"],
                uso_tokens=mensaje.get("usage") or {},
                marca_tiempo=evento.get("timestamp", ""),
                sesion=evento.get("sessionId", ""),
            )
            contenido = mensaje.get("content")
            if isinstance(contenido, str):
                resultado.textos.append(contenido)
            elif isinstance(contenido, list):
                for bloque in contenido:
                    if not isinstance(bloque, dict):
                        continue
                    tipo = bloque.get("type")
                    if tipo == "text":
                        resultado.textos.append(bloque.get("text", ""))
                    elif tipo == "tool_use":
                        resultado.usos_herramienta.append({"nombre": bloque.get("name", ""), "entrada": bloque.get("input") or {}})
                    elif tipo == "tool_result":
                        resultado.resultados_herramienta.append(
                            {"texto": _texto_de(bloque.get("content")), "error": bool(bloque.get("is_error"))}
                        )
            yield resultado


def ultimo_texto_asistente(ruta: Path) -> str:
    ultimo = ""
    for mensaje in leer(ruta):
        if mensaje.rol == "assistant" and any(t.strip() for t in mensaje.textos):
            ultimo = "\n".join(mensaje.textos)
    return ultimo


def textos_resultados(ruta: Path) -> list[str]:
    return [r["texto"] for m in leer(ruta) for r in m.resultados_herramienta]


def es_prompt_humano(mensaje: Mensaje) -> bool:
    """Distingue un prompt escrito por la persona de un resultado de herramienta devuelto como 'user'."""
    return mensaje.rol == "user" and not mensaje.resultados_herramienta and any(t.strip() for t in mensaje.textos)
