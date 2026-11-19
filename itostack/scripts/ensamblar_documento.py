#!/usr/bin/env python3
"""Ensamblado de escritos con citas resueltas desde la evidencia (capa 1 de la pirámide; contrato CR-1).

El agente redacta con marcadores y nunca escribe rubros, claves ni marcas de verificación a mano:
  [[CITA:registro]] o [[CITA:registro|forma]]   cita verificada (formas: completa · rubro · clave · corta)
  [[CITA_AJENA:referencia|fuente]]              cita de un tercero; la referencia debe aparecer literal en la fuente
  [[NO_VERIFICADO:texto]]                       afirmación propia no verificada, con advertencia visible
Este script sustituye cada marcador con los datos OFICIALES capturados, añade una nota de evidencia y escribe junto al
documento su manifiesto de procedencia (<salida>.procedencia.json). Falla cerrado: sin evidencia vigente, con una cita
escrita a mano o con un marcador inválido no entrega nada; y antes de escribir comprueba su propia salida con
verificar_entrega.py.

Uso:
  ensamblar_documento.py BORRADOR.md --salida salidas/escrito.md [--permitir-pendientes] [--docx]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nucleo import config as cfg  # noqa: E402
from nucleo import procedencia  # noqa: E402
from nucleo.evidencia import AlmacenEvidencia  # noqa: E402

ADVERTENCIA_FIJA = procedencia.ADVERTENCIA_FIJA
formatear = procedencia.formatear


def modos_validos(config: dict) -> tuple[str, ...]:
    return ("real", "fixture") if config["modo"] == "fixture" else ("real",)


def ruta_manifiesto(salida: Path) -> Path:
    return salida.with_name(salida.name + ".procedencia.json")


def lector_de_fuentes(proyecto: Path):
    """Documentos del expediente para CITA_AJENA: solo archivos de texto dentro del proyecto."""
    raiz = proyecto.resolve()

    def leer(ruta: str):
        destino = (raiz / ruta).resolve()
        if not destino.is_file() or not destino.is_relative_to(raiz):
            return None
        datos = destino.read_bytes()
        try:
            return datos.decode("utf-8"), procedencia.sha256(datos)
        except UnicodeDecodeError:
            return None

    return leer


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("borrador", type=Path)
    analizador.add_argument("--salida", type=Path, required=True)
    analizador.add_argument("--permitir-pendientes", action="store_true", help="entrega un borrador con marcas ⚠ (no apto para presentar; su manifiesto lo declara no entregable)")
    analizador.add_argument("--docx", action="store_true", help="además genera .docx con pandoc si está instalado")
    args = analizador.parse_args()

    config = cfg.cargar()
    proyecto = Path(config["_proyecto"])
    almacen = AlmacenEvidencia(cfg.ruta_en_proyecto(config, config["evidencia"]["base_datos"]))
    dias, modos = config["evidencia"]["vigencia_dias"], modos_validos(config)
    texto = args.borrador.read_text(encoding="utf-8")

    resultado = procedencia.ensamblar(texto, lambda registro: almacen.vigente("tesis", registro, dias, modos), lector_de_fuentes(proyecto),
                                      args.permitir_pendientes)
    if resultado.errores:
        for problema in resultado.errores:
            print(f"✘ {problema}")
        for registro in resultado.pendientes:
            print(f"  verifica: python3 {Path(__file__).parent / 'verificar.py'} tesis --registro {registro} --modo existencia")
        print("ENSAMBLADO: BLOCKED — no se escribió ningún archivo.")
        return 2

    version = json.loads((cfg.RAIZ_PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")).get("version", "?")
    manifiesto = procedencia.manifiesto(resultado.texto, texto, resultado, version)
    datos = resultado.texto.encode("utf-8")
    # El ensamblador se somete a la misma comprobación que cualquier entregable antes de escribir.
    problemas = [p for p in procedencia.verificar_entrega(datos, manifiesto) if not (args.permitir_pendientes and "pendientes" in p)]
    if problemas:
        for problema in problemas:
            print(f"✘ {problema}")
        print("ENSAMBLADO: BLOCKED — la salida no supera la comprobación de entrega; no se escribió ningún archivo.")
        return 2

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_bytes(datos)
    ruta_manifiesto(args.salida).write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    citas = sum(1 for t in resultado.tramos if t.tipo == "CITA")
    estado = "PASS" if manifiesto["entregable"] else "BORRADOR CON PENDIENTES (no entregable)"
    print(f"ENSAMBLADO: {estado} — {args.salida} · {citas} cita(s) con evidencia · {len(resultado.pendientes)} pendiente(s) · "
          f"procedencia en {ruta_manifiesto(args.salida).name}")
    if args.docx:
        pandoc = shutil.which("pandoc")
        if pandoc:
            destino = args.salida.with_suffix(".docx")
            subprocess.run([pandoc, str(args.salida), "-o", str(destino)], check=True)
            print(f"DOCX: {destino}")
        else:
            print("pandoc no está instalado: el .docx no se generó (sudo apt install pandoc)")
    return 0 if manifiesto["entregable"] else 2


if __name__ == "__main__":
    sys.exit(principal())
