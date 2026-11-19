#!/usr/bin/env python3
"""Comprobación de entrega de un documento jurídico (contrato CR-1, itostack/citas@1).

Un documento es entregable (PASS) solo si su manifiesto de procedencia (<documento>.procedencia.json) existe y es
completo y coherente, su huella coincide (no se editó después de generarse), no declara citas pendientes, no quedan
marcadores sin resolver, todo patrón de cita cae dentro de un tramo del renderizador y cada tramo se puede volver a
verificar contra las fuentes vivas del proyecto: la evidencia vigente de cada cita, la fuente de cada cita ajena y el
documento auditado de un informe. Cualquier otra cosa es BLOCKED.

Uso: verificar_entrega.py salidas/escrito.md [más documentos…]
Código: 0 PASS (todos entregables) · 2 BLOCKED (alguno no lo es) · 3 uso (sin argumentos o un documento no existe).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nucleo import config as cfg  # noqa: E402
from nucleo import procedencia  # noqa: E402
from nucleo.evidencia import AlmacenEvidencia  # noqa: E402


def ruta_manifiesto(documento: Path) -> Path:
    return documento.with_name(documento.name + ".procedencia.json")


def contexto_del_proyecto(config: dict) -> procedencia.Contexto:
    """Fuentes vivas del proyecto: evidencia PASS vigente (con la vigencia y los modos de la configuración) y documentos."""
    almacen = AlmacenEvidencia(cfg.ruta_en_proyecto(config, config["evidencia"]["base_datos"]))
    dias = config["evidencia"]["vigencia_dias"]
    modos = ("real", "fixture") if config["modo"] == "fixture" else ("real",)
    return procedencia.Contexto(lambda registro: almacen.vigente("tesis", registro, dias, modos),
                                procedencia.lector_de_fuentes(Path(config["_proyecto"])))


def revisar(documento: Path, contexto: procedencia.Contexto | None) -> list[str]:
    """Motivos de BLOCKED de un documento; vacío = PASS. Un derivado (.docx) vale si su origen .md vale y no cambió."""
    try:
        datos = json.loads(ruta_manifiesto(documento).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        datos = None
    contenido = documento.read_bytes()
    if isinstance(datos, dict) and datos.get("tipo_documento") == "derivado":
        esperados = {"contrato", "version_plugin", "tipo_documento", "derivado_de", "sha256_documento", "sha256_origen"}
        if set(datos) != esperados or datos.get("contrato") != procedencia.CONTRATO or not isinstance(datos.get("derivado_de"), str):
            return ["manifiesto de derivado incompleto o inconsistente"]
        if procedencia.sha256(contenido) != datos["sha256_documento"]:
            return ["el derivado cambió después de generarse"]
        origen = documento.with_name(Path(datos["derivado_de"]).name)
        if not origen.is_file() or procedencia.sha256(origen.read_bytes()) != datos["sha256_origen"]:
            return [f"el documento de origen «{origen.name}» no existe o cambió"]
        return [f"origen «{origen.name}»: {p}" for p in revisar(origen, contexto)]
    return procedencia.verificar_entrega(contenido, datos, contexto)


def principal(rutas: list[str]) -> int:
    if not rutas:
        print(__doc__)
        return 3
    contexto = contexto_del_proyecto(cfg.cargar())
    codigo = 0
    for ruta in map(Path, rutas):
        if not ruta.is_file():
            print(f"✘ {ruta}: no existe")
            return 3
        problemas = revisar(ruta, contexto)
        if problemas:
            codigo = 2
            print(f"✘ {ruta}: BLOCKED — no es entregable")
            for problema in problemas:
                print(f"    {problema}")
        else:
            print(f"✔ {ruta}: PASS — entregable (procedencia verificada contra sus fuentes)")
    return codigo


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(principal(sys.argv[1:]))
