#!/usr/bin/env python3
"""Ensamblado de escritos con citas resueltas desde la evidencia (capa 1 de la pirámide).

El agente redacta con marcadores [[CITA:registro]] o [[CITA:registro|forma]] y nunca escribe
rubros a mano. Este script sustituye cada marcador con los datos OFICIALES capturados y añade
una nota de evidencia. Si falta evidencia vigente, no entrega nada (falla cerrado).

Formas: completa (defecto) · rubro · clave · corta
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

from nucleo import config as cfg, citas  # noqa: E402
from nucleo.evidencia import AlmacenEvidencia  # noqa: E402

ADVERTENCIA_FIJA = (
    "⚠ Documento ensamblado con apoyo de IA. Verificar citas en fuentes oficiales antes de uso procesal: "
    "sjf.scjn.gob.mx · dof.gob.mx · diputados.gob.mx/LeyesBiblio"
)


def modos_validos(config: dict) -> tuple[str, ...]:
    return ("real", "fixture") if config["modo"] == "fixture" else ("real",)


def formatear(oficial: dict, forma: str, nota: str) -> str:
    registro = oficial.get("registro", "—")
    if forma == "rubro":
        return f"«{oficial.get('rubro', '')}»{nota}"
    if forma == "clave":
        return f"{oficial.get('clave', '—')} (registro digital {registro}){nota}"
    if forma == "corta":
        return f"registro digital {registro}{nota}"
    tipo = "Jurisprudencia" if "jurisprud" in str(oficial.get("tipo", "")).lower() else "Tesis"
    return (
        f"{tipo} {oficial.get('clave', '—')}, de rubro: «{oficial.get('rubro', '')}», "
        f"emitida por {oficial.get('instancia', '—')}, {oficial.get('epoca', '—')}, registro digital {registro}{nota}"
    )


def ensamblar(texto: str, almacen: AlmacenEvidencia, dias: int, modos: tuple[str, ...]) -> tuple[str, list[str], list[str]]:
    pendientes: list[str] = []
    notas: list[str] = []
    numeracion: dict[str, int] = {}

    def sustituir(coincidencia) -> str:
        registro, forma = coincidencia.group(1), coincidencia.group(2) or "completa"
        fila = almacen.vigente("tesis", registro, dias, modos)
        if not fila:
            pendientes.append(registro)
            return f"⚠ CITA NO VERIFICADA (registro {registro}) — ejecutar /verificar-cita"
        if registro not in numeracion:
            numeracion[registro] = len(numeracion) + 1
            avisos = json.loads(fila["advertencias"])
            detalle_avisos = "".join(f" ⚠ {a}" for a in avisos)
            notas.append(
                f"[^ev{numeracion[registro]}]: Verificado en el portal oficial el {fila['creado_en']} "
                f"[{fila['modo_fuente']}] · evidencia `{fila['ruta_resultado']}` · SHA-256 {fila['sha256_resultado'][:16]}….{detalle_avisos}"
            )
        return formatear(json.loads(fila["datos_oficiales"]), forma, f"[^ev{numeracion[registro]}]")

    resultado = citas.RE_MARCADOR.sub(sustituir, texto)
    return resultado, pendientes, notas


def citas_a_mano(texto: str, almacen: AlmacenEvidencia, dias: int, modos: tuple[str, ...], ignorar_acentos: bool = True) -> list[str]:
    """Registros o claves escritos fuera de marcadores sin evidencia vigente (y sin marca ⚠/❌), o con un rubro
    explícito que no es el de su evidencia (N-01)."""
    problemas = []
    for cita in citas.extraer(texto):
        if cita.tipo == "marcador" or cita.marcada_no_verificada:
            continue
        vigente = (
            almacen.vigente("tesis", cita.valor, dias, modos) if cita.tipo == "registro"
            else almacen.vigente_por_clave(cita.valor, dias, modos)
        )
        if not vigente:
            problemas.append(f"línea {cita.linea}: {cita.tipo} «{cita.valor}» escrito a mano sin evidencia vigente")

    def oficial_de(registro: str | None, clave: str | None) -> dict | None:
        fila = (almacen.vigente("tesis", registro, dias, modos) if registro else None) or (
            almacen.vigente_por_clave(clave, dias, modos) if clave else None
        )
        return json.loads(fila["datos_oficiales"]) if fila else None

    problemas.extend(citas.rubros_discrepantes(texto, oficial_de, ignorar_acentos))
    return problemas


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("borrador", type=Path)
    analizador.add_argument("--salida", type=Path, required=True)
    analizador.add_argument("--permitir-pendientes", action="store_true", help="entrega un borrador con marcas ⚠ (no apto para presentar)")
    analizador.add_argument("--docx", action="store_true", help="además genera .docx con pandoc si está instalado")
    args = analizador.parse_args()

    config = cfg.cargar()
    almacen = AlmacenEvidencia(cfg.ruta_en_proyecto(config, config["evidencia"]["base_datos"]))
    dias, modos = config["evidencia"]["vigencia_dias"], modos_validos(config)
    texto = args.borrador.read_text(encoding="utf-8")

    manuales = citas_a_mano(texto, almacen, dias, modos, config["comparacion"]["ignorar_acentos"])
    cuerpo, pendientes, notas = ensamblar(texto, almacen, dias, modos)
    if (manuales or pendientes) and not args.permitir_pendientes:
        for problema in manuales:
            print(f"✘ {problema}")
        for registro in pendientes:
            print(f"✘ [[CITA:{registro}]] sin evidencia vigente: python3 {Path(__file__).parent / 'verificar.py'} tesis --registro {registro} --modo existencia")
        print("ENSAMBLADO: BLOCKED — no se escribió ningún archivo.")
        return 2

    documento = cuerpo.rstrip() + "\n\n---\n\n" + ("\n".join(notas) + "\n\n" if notas else "") + ADVERTENCIA_FIJA + "\n"
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(documento, encoding="utf-8")
    estado = "BORRADOR CON PENDIENTES" if (manuales or pendientes) else "PASS"
    print(f"ENSAMBLADO: {estado} — {args.salida} · {len(notas)} cita(s) con evidencia · {len(pendientes)} pendiente(s)")
    if args.docx:
        pandoc = shutil.which("pandoc")
        if pandoc:
            destino = args.salida.with_suffix(".docx")
            subprocess.run([pandoc, str(args.salida), "-o", str(destino)], check=True)
            print(f"DOCX: {destino}")
        else:
            print("pandoc no está instalado: el .docx no se generó (sudo apt install pandoc)")
    return 0 if estado == "PASS" else 2


if __name__ == "__main__":
    sys.exit(principal())
