#!/usr/bin/env python3
"""PreToolUse(Write|Edit|MultiEdit): lint de arquitectura, citas sin evidencia y zonas protegidas.

- Código (.py/.ts/.js): aplica las reglas IT00X sobre el texto nuevo.
- Salidas jurídicas: cada registro o clave de tesis debe tener evidencia PASS vigente, venir como
  marcador [[CITA:registro]] o estar marcada explícitamente como ⚠/❌ no verificada.
- Zonas protegidas: evidencia forense, base de datos y casos holdout no se editan a mano.
"""

from __future__ import annotations

import fnmatch
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402
from lint_itosturre import revisar_texto  # noqa: E402
from nucleo import citas as detector  # noqa: E402
from nucleo.evidencia import AlmacenEvidencia  # noqa: E402


def textos_nuevos(nombre: str, entrada: dict) -> list[str]:
    if nombre == "Write":
        return [entrada.get("content", "")]
    if nombre == "Edit":
        return [entrada.get("new_string", "")]
    if nombre == "MultiEdit":
        return [e.get("new_string", "") for e in entrada.get("edits", [])]
    return []


def zona_protegida(ruta: str) -> str | None:
    normalizada = ruta.replace("\\", "/")
    if "/.itostack/evidencia/" in normalizada or normalizada.endswith((".itostack/evidencia_forense.db", "ultimo_resultado.json", "ultimo_lote.json")):
        return "la evidencia forense solo la escribe verificar.py; editarla a mano rompe la cadena de custodia."
    if fnmatch.fnmatch(normalizada, "*/evals/*/holdout-*/*") and os.environ.get("ITOSTACK_EDITAR_HOLDOUT") != "1":
        return "los casos holdout son la reserva de evaluación: el agente que mejora una skill no puede verlos ni editarlos."
    if fnmatch.fnmatch(normalizada, "*/evals/compuerta/*"):
        return "los candidatos congelados y su historial solo los escribe compuerta_holdout.py."
    return None


def es_salida_juridica(ruta: Path, proyecto: Path, config: dict) -> bool:
    try:
        relativa = ruta.resolve().relative_to(proyecto).as_posix()
    except ValueError:
        relativa = ruta.as_posix()
    if any(fnmatch.fnmatch(relativa, patron) for patron in config.get("salidas_juridicas", [])):
        return True
    return bool(config.get("modo_estricto_md")) and ruta.suffix.lower() in {".md", ".txt"}


def citas_sin_evidencia(texto: str, config: dict) -> list[str]:
    almacen = AlmacenEvidencia(_comun.cfg.ruta_en_proyecto(config, config["evidencia"]["base_datos"]))
    dias, modos = config["evidencia"]["vigencia_dias"], _comun.modos_validos(config)
    problemas = []
    for cita in detector.extraer(texto):
        if cita.tipo == "marcador" or cita.marcada_no_verificada:
            continue
        vigente = (
            almacen.vigente("tesis", cita.valor, dias, modos) if cita.tipo == "registro"
            else almacen.vigente_por_clave(cita.valor, dias, modos)
        )
        if not vigente:
            problemas.append(f"línea {cita.linea}: {cita.tipo} «{cita.valor}»")
    return problemas


def principal() -> int:
    entrada = _comun.leer_entrada()
    nombre = entrada.get("tool_name", "")
    datos = entrada.get("tool_input") or {}
    ruta_texto = datos.get("file_path", "")
    if not ruta_texto:
        return 0
    protegida = zona_protegida(ruta_texto)
    if protegida:
        _comun.denegar(protegida)
        return 0

    textos = textos_nuevos(nombre, datos)
    hallazgos = [h for texto in textos for h in revisar_texto(texto, ruta_texto)]
    if hallazgos:
        detalle = "\n".join(f"- {h.codigo} línea {h.linea}: {h.mensaje}" for h in hallazgos[:8])
        _comun.denegar(f"el cambio viola reglas de arquitectura Itosturre:\n{detalle}\nSi es una excepción legítima, agrega '# itostack: permitir IT00X — justificación'.")
        return 0

    if not _comun.tiene_itostack(entrada):
        return 0
    config = _comun.configuracion(entrada)
    ruta = Path(ruta_texto)
    if not es_salida_juridica(ruta, _comun.proyecto(entrada), config):
        return 0
    try:
        problemas = [p for texto in textos for p in citas_sin_evidencia(texto, config)]
    except Exception as error:  # falla cerrado en entregables jurídicos
        _comun.denegar(f"no se pudo comprobar la evidencia de las citas ({error}); no se escribe un entregable jurídico sin esa comprobación.")
        return 0
    if problemas:
        lista = "\n".join(f"- {p}" for p in problemas[:10])
        _comun.denegar(
            "citas sin evidencia vigente en un entregable jurídico:\n"
            f"{lista}\n"
            "Opciones: (1) verifica con /verificar-cita y vuelve a escribir; (2) redacta con el marcador [[CITA:registro]] "
            "y ensambla con ensamblar_documento.py; (3) si reportas una cita ajena, márcala en la misma línea con ⚠ NO VERIFICADO o ❌."
        )
    return 0


if __name__ == "__main__":
    sys.exit(_comun.ejecutar(principal, "PreToolUse", "cerrado"))
