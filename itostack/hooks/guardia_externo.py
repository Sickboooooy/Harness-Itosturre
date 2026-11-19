#!/usr/bin/env python3
"""PreToolUse(mcp__*): compuerta humana para acciones hacia afuera, entregables y citas sin evidencia.

Leer en conectores (correo, Drive, Slack, Notion) pasa libre. Enviar, publicar, compartir o programar requiere
aprobación. Además se deniega:
- un envío que nombra un archivo jurídico del proyecto que no supera la comprobación de entrega (CR-1.2: manifiesto de
  procedencia completo, coherente y verificable contra sus fuentes);
- un texto saliente con citas sin evidencia vigente (revisión heurística del mensaje: un mensaje no es un entregable).
"""

from __future__ import annotations

import fnmatch
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402
from guardia_escritura import es_salida_juridica  # noqa: E402
from nucleo import citas as detector  # noqa: E402
from nucleo.evidencia import AlmacenEvidencia  # noqa: E402

RE_RUTA_DOCUMENTO = re.compile(r"[^\s\"'<>|]+\.(?:md|txt|docx)\b", re.IGNORECASE)

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


def citas_sin_evidencia(texto: str, config: dict) -> list[str]:
    """Registros o claves sin evidencia PASS vigente en un texto saliente (heurística de 0.1.x; solo deniega)."""
    almacen = AlmacenEvidencia(_comun.cfg.ruta_en_proyecto(config, config["evidencia"]["base_datos"]))
    dias, modos = config["evidencia"]["vigencia_dias"], _comun.modos_validos(config)
    problemas = []
    for cita in detector.extraer(texto):
        if cita.tipo == "marcador" or cita.marcada_no_verificada:
            continue
        vigente = (almacen.vigente("tesis", cita.valor, dias, modos) if cita.tipo == "registro"
                   else almacen.vigente_por_clave(cita.valor, dias, modos))
        if not vigente:
            problemas.append(f"línea {cita.linea}: {cita.tipo} «{cita.valor}»")

    def oficial(registro: str | None, clave: str | None) -> dict | None:
        fila = (almacen.vigente("tesis", registro, dias, modos) if registro else None) or (
            almacen.vigente_por_clave(clave, dias, modos) if clave else None)
        return json.loads(fila["datos_oficiales"]) if fila else None

    problemas.extend(detector.rubros_discrepantes(texto, oficial, config["comparacion"]["ignorar_acentos"]))
    return problemas


def entregables_nombrados(textos: list[str], proyecto: Path, config: dict) -> list[Path]:
    """Archivos jurídicos del proyecto que el envío nombra (adjuntos o rutas en el cuerpo)."""
    hallados: list[Path] = []
    for texto in textos:
        for candidato in RE_RUTA_DOCUMENTO.findall(texto):
            ruta = Path(candidato) if Path(candidato).is_absolute() else proyecto / candidato
            if ruta.is_file() and es_salida_juridica(ruta, proyecto, config) and ruta not in hallados:
                hallados.append(ruta)
    return hallados


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
        textos = cadenas(entrada.get("tool_input") or {})
        nombrados = entregables_nombrados(textos, _comun.proyecto(entrada), config)
        if nombrados:
            import verificar_entrega

            contexto = verificar_entrega.contexto_del_proyecto(config)
            for ruta in nombrados:
                motivos = verificar_entrega.revisar(ruta, contexto)
                if motivos:
                    _comun.denegar(f"«{ruta.name}» no es entregable (BLOCKED): " + "; ".join(motivos[:4]) + ". Ensambla de nuevo desde el borrador.")
                    return 0
        problemas = citas_sin_evidencia("\n".join(textos), config)
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
