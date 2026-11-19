#!/usr/bin/env python3
"""PreToolUse(Write|Edit|MultiEdit): lint de arquitectura, contrato de citas (CR-1) y zonas protegidas.

- Código (.py/.ts/.js): aplica las reglas IT00X sobre el texto nuevo.
- Entregables jurídicos (`salidas_juridicas`) y manifiestos de procedencia: solo los escriben los renderizadores
  (ensamblar_documento.py, reporte_vvca.py). El agente redacta un borrador y ensambla; editar un entregable lo invalida.
- Borradores jurídicos (`borradores_juridicos`, y todo .md/.txt con `modo_estricto_md`): el contenido que quedaría debe
  cumplir la gramática de marcadores y no traer citas, «rubro:» ni marcas ⚠/❌/✅ escritas a mano (alarma: solo deniega).
- Zonas protegidas: evidencia forense, base de datos, casos holdout y estado de la compuerta no se editan a mano.
"""

from __future__ import annotations

import fnmatch
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402
from lint_itosturre import revisar_texto  # noqa: E402
from nucleo import procedencia  # noqa: E402

BORRADORES_POR_OMISION = ["borradores/**"]


def textos_nuevos(nombre: str, entrada: dict) -> list[str]:
    if nombre == "Write":
        return [entrada.get("content", "")]
    if nombre == "Edit":
        return [entrada.get("new_string", "")]
    if nombre == "MultiEdit":
        return [e.get("new_string", "") for e in entrada.get("edits", [])]
    return []


def contenido_resultante(nombre: str, entrada: dict, ruta: Path) -> str:
    """El archivo como quedaría tras el cambio: así un marcador partido entre ediciones o una cita armada con varias
    ediciones se revisan completos. Si una edición no aplica (la herramienta fallará), se revisa su texto nuevo."""
    if nombre == "Write":
        return entrada.get("content", "")
    try:
        actual = ruta.read_text(encoding="utf-8") if ruta.is_file() else ""
    except (OSError, UnicodeDecodeError):
        actual = ""
    for edicion in [entrada] if nombre == "Edit" else entrada.get("edits", []):
        viejo, nuevo = edicion.get("old_string", ""), edicion.get("new_string", "")
        if viejo and viejo in actual:
            actual = actual.replace(viejo, nuevo) if edicion.get("replace_all") else actual.replace(viejo, nuevo, 1)
        else:
            actual += "\n" + nuevo
    return actual


def zona_protegida(ruta: str) -> str | None:
    normalizada = ruta.replace("\\", "/")
    if "/.itostack/evidencia/" in normalizada or normalizada.endswith((".itostack/evidencia_forense.db", "ultimo_resultado.json", "ultimo_lote.json")):
        return "la evidencia forense solo la escribe verificar.py; editarla a mano rompe la cadena de custodia."
    if fnmatch.fnmatch(normalizada, "*/evals/*/holdout-*/*") and os.environ.get("ITOSTACK_EDITAR_HOLDOUT") != "1":
        return "los casos holdout son la reserva de evaluación: el agente que mejora una skill no puede verlos ni editarlos."
    if fnmatch.fnmatch(normalizada, "*/evals/compuerta/*") or normalizada.endswith("/evals/reserva.json"):
        return "los candidatos congelados, su historial y el estado de la reserva solo los cambian la compuerta o el operador."
    if normalizada.endswith(".procedencia.json"):
        return "los manifiestos de procedencia solo los escriben ensamblar_documento.py y reporte_vvca.py."
    return None


def _relativa(ruta: Path, proyecto: Path) -> str:
    try:
        return ruta.resolve().relative_to(proyecto.resolve()).as_posix()
    except ValueError:
        return ruta.as_posix()


def es_salida_juridica(ruta: Path, proyecto: Path, config: dict) -> bool:
    return any(fnmatch.fnmatch(_relativa(ruta, proyecto), patron) for patron in config.get("salidas_juridicas", []))


def es_borrador_juridico(ruta: Path, proyecto: Path, config: dict) -> bool:
    relativa = _relativa(ruta, proyecto)
    if any(fnmatch.fnmatch(relativa, patron) for patron in config.get("borradores_juridicos") or BORRADORES_POR_OMISION):
        return True
    return bool(config.get("modo_estricto_md")) and ruta.suffix.lower() in {".md", ".txt"}


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

    hallazgos = [h for texto in textos_nuevos(nombre, datos) for h in revisar_texto(texto, ruta_texto)]
    if hallazgos:
        detalle = "\n".join(f"- {h.codigo} línea {h.linea}: {h.mensaje}" for h in hallazgos[:8])
        _comun.denegar(f"el cambio viola reglas de arquitectura Itosturre:\n{detalle}\nSi es una excepción legítima, agrega '# itostack: permitir IT00X — justificación'.")
        return 0

    if not _comun.tiene_itostack(entrada):
        return 0
    config = _comun.configuracion(entrada)
    proyecto = _comun.proyecto(entrada)
    ruta = Path(ruta_texto) if Path(ruta_texto).is_absolute() else proyecto / ruta_texto
    if es_salida_juridica(ruta, proyecto, config):
        _comun.denegar(
            "un entregable jurídico solo lo escribe un renderizador, con su manifiesto de procedencia: redacta el borrador en "
            "borradores/ con marcadores ([[CITA:registro]], [[CITA_AJENA:referencia|fuente]], [[NO_VERIFICADO:texto]]) y "
            "ensambla con ensamblar_documento.py (o genera el informe con reporte_vvca.py). Editar un entregable lo invalida: "
            "corrige el borrador y vuelve a ensamblar."
        )
        return 0
    if es_borrador_juridico(ruta, proyecto, config):
        problemas = procedencia.problemas_de_borrador(contenido_resultante(nombre, datos, ruta))
        if problemas:
            lista = "\n".join(f"- {p}" for p in problemas[:10])
            _comun.denegar(f"el borrador no cumple el contrato de citas (itostack/citas@1):\n{lista}\n"
                           "Cada cita va en un marcador; las marcas de verificación las escribe el ensamblador, nunca el agente.")
    return 0


if __name__ == "__main__":
    sys.exit(_comun.ejecutar(principal, "PreToolUse", "cerrado"))
