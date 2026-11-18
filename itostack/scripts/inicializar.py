#!/usr/bin/env python3
"""Prepara `.itostack/` en un proyecto: configuración, almacén de evidencia, carpetas de mejora y plantillas.

Uso:
  inicializar.py [--proyecto .] [--perfil juridico|desarrollo|ambos] [--modo real|fixture]
                 [--sjf-fixture RUTA] [--silencioso]
Es idempotente: no pisa archivos existentes salvo los valores pasados explícitamente.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nucleo import config as cfg  # noqa: E402
from nucleo.evidencia import AlmacenEvidencia  # noqa: E402

PLANTILLAS = cfg.RAIZ_PLUGIN / "plantillas"
GITIGNORE = "evidencia/\n*.db\n*.db-journal\nraiz_plugin\nultimo_resultado.json\nultimo_lote.json\napp.json\n"


def inicializar(proyecto: Path, perfil: str, modo: str | None, fixture: str | None, silencioso: bool) -> Path:
    base = proyecto / cfg.DIR_ITOSTACK
    for sub in ("evidencia", "mejora/reportes", "bitacora"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    (base / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (base / "raiz_plugin").write_text(str(cfg.RAIZ_PLUGIN), encoding="utf-8")

    ruta_config = base / "config.json"
    propia = json.loads(ruta_config.read_text(encoding="utf-8")) if ruta_config.is_file() else {"version": 1, "perfil": perfil}
    if modo:
        propia["modo"] = modo
    if fixture:
        propia.setdefault("sjf", {})["fixture"] = str(Path(fixture).resolve())
    if not propia.get("navegador", {}).get("ejecutable"):
        detectado = cfg.detectar_navegador(cfg.CONFIG_DEFECTO)
        if detectado:
            propia.setdefault("navegador", {})["ejecutable"] = detectado
    ruta_config.write_text(json.dumps(propia, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for nombre in ("correcciones.tsv", "elevaciones.tsv"):
        ruta = base / "mejora" / nombre
        if not ruta.exists():
            encabezado = (
                "fecha\tsesion\tclave\textracto\n" if nombre == "correcciones.tsv"
                else "fecha\tclave\tnivel\tartefacto\tdescripcion\n"
            )
            ruta.write_text(encabezado, encoding="utf-8")

    copias = {"CLAUDE.itostack.md": base / "CLAUDE.itostack.md", "modelos.json": base / "modelos.json"}
    if perfil in {"desarrollo", "ambos"}:
        copias["mapa-funcionalidades.md"] = base / "mapa-funcionalidades.md"
    for origen, destino in copias.items():
        if not destino.exists() and (PLANTILLAS / origen).is_file():
            shutil.copyfile(PLANTILLAS / origen, destino)

    config = cfg.cargar(proyecto)
    AlmacenEvidencia(cfg.ruta_en_proyecto(config, config["evidencia"]["base_datos"])).inicializar()

    if not silencioso:
        print(f"itostack inicializado en {base}")
        print(f"  modo: {config['modo']} · perfil: {propia.get('perfil', perfil)}")
        print(f"  navegador: {config['navegador'].get('ejecutable') or 'el de Playwright (npx playwright install chromium)'}")
        print("Siguiente paso: agrega esta línea a tu CLAUDE.md →  @.itostack/CLAUDE.itostack.md")
        if not (cfg.RAIZ_PLUGIN / "scripts" / "node_modules" / "playwright").is_dir():
            print(f"Falta Playwright: cd {cfg.RAIZ_PLUGIN / 'scripts'} && npm install && npx playwright install chromium")
    return base


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("--proyecto", default=".")
    analizador.add_argument("--perfil", choices=["juridico", "desarrollo", "ambos"], default="ambos")
    analizador.add_argument("--modo", choices=["real", "fixture"])
    analizador.add_argument("--sjf-fixture")
    analizador.add_argument("--silencioso", action="store_true")
    args = analizador.parse_args()
    inicializar(Path(args.proyecto).resolve(), args.perfil, args.modo, args.sjf_fixture, args.silencioso)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
