#!/usr/bin/env python3
"""Copia la plantilla del ejecutor aislado (CR-2) a la copia de trabajo de su repositorio PRIVADO y SEPARADO.

Falla cerrado. No copia nada si:
- queda algún «PENDIENTE-DE-VERIFICAR» o una acción externa no fijada a un SHA de 40 hex en el workflow;
- versiones.json declara pendientes de verificar, no declara herramientas verificadas o no fija la copia del
  orquestador (directorio y huella de cada archivo);
- known_hosts no tiene claves de host (ssh no podría comprobar a quién se conecta);
- el destino está dentro del repositorio del constructor (el ejecutor debe vivir en otro repositorio, con permisos
  propios), o el destino no es un repositorio Git.
No crea credenciales ni toca GitHub: el operador configura el environment «holdout» (revisores obligatorios), los
secretos y la clave de despliegue en la interfaz web.
Uso: instanciar.py <copia de trabajo del repositorio del ejecutor> [--plantilla <ruta>]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

CONSTRUCTOR = Path(__file__).resolve().parent
PLANTILLA = CONSTRUCTOR / "plantilla"
_USES = re.compile(r"^\s*-?\s*uses:\s*(\S+)", re.MULTILINE)
_SHA = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")


def raiz_git(ruta: Path) -> Path | None:
    salida = subprocess.run(["git", "-C", str(ruta), "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)
    return Path(salida.stdout.strip()).resolve() if salida.returncode == 0 else None


def impedimentos(plantilla: Path, destino: Path, constructor: Path = CONSTRUCTOR) -> list[str]:
    problemas = []
    for workflow in sorted((plantilla / ".github" / "workflows").glob("*.yml")):
        texto = "\n".join(l for l in workflow.read_text(encoding="utf-8").splitlines() if not l.lstrip().startswith("#"))
        if "PENDIENTE-DE-VERIFICAR" in texto:
            problemas.append(f"{workflow.name}: quedan dependencias PENDIENTE-DE-VERIFICAR")
        problemas += [f"{workflow.name}: «{u}» no está fijada a un SHA de 40 hex" for u in _USES.findall(texto) if not _SHA.match(u) and "PENDIENTE" not in u]
    versiones = json.loads((plantilla / "ejecutor" / "versiones.json").read_text(encoding="utf-8"))
    problemas += [f"versiones.json: pendiente de verificar «{p}»" for p in versiones.get("pendientes_de_verificar", [])]
    if not versiones.get("verificadas"):
        problemas.append("versiones.json: no declara herramientas verificadas")
    hosts = (plantilla / "ejecutor" / "known_hosts").read_text(encoding="utf-8") if (plantilla / "ejecutor" / "known_hosts").is_file() else ""
    if not any(linea.strip() and not linea.lstrip().startswith("#") for linea in hosts.splitlines()):
        problemas.append("known_hosts: no tiene las claves de host de github.com")
    fijados = versiones.get("fijados")
    if not isinstance(fijados, dict) or not fijados.get("directorio") or not fijados.get("archivos"):
        problemas.append("versiones.json: no fija la copia del orquestador (directorio y huella de cada archivo)")
    destino_git = raiz_git(destino) if destino.is_dir() else None
    if destino_git is None:
        problemas.append("el destino no es la copia de trabajo de un repositorio Git")
    elif destino_git == raiz_git(constructor):
        problemas.append("el destino está dentro del repositorio del constructor: el ejecutor debe vivir en un repositorio separado")
    return problemas


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("destino", type=Path)
    analizador.add_argument("--plantilla", type=Path, default=PLANTILLA)
    args = analizador.parse_args()
    problemas = impedimentos(args.plantilla, args.destino)
    if problemas:
        for p in problemas:
            print(f"✘ {p}")
        print("No se instancia la plantilla: resuelve lo anterior (verificar versiones y SHAs; repositorio separado).")
        return 1
    shutil.copytree(args.plantilla, args.destino, dirs_exist_ok=True)
    print(f"Plantilla copiada a {args.destino}. Falta lo que hace el operador en GitHub: environment «holdout» con revisores "
          "obligatorios, secretos (CONSTRUCTOR_DEPLOY_KEY, CLAUDE_CODE_OAUTH_TOKEN, CODEX_AUTH_JSON, CLAVE_FIRMA_EJECUTOR) y "
          "la variable REPO_CONSTRUCTOR.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(principal())
