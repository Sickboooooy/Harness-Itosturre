#!/usr/bin/env python3
"""Comprueba que el ejecutor tenga exactamente lo verificado (contrato CR-3, P2 y P3; CR-2, dependencias fijadas).

- Herramientas: cada una de «verificadas» instalada y en esa versión exacta.
- Copia fijada del orquestador («fijados»): el directorio contiene EXACTAMENTE los archivos listados, cada uno con su
  sha256. Un archivo de más, de menos o con otro contenido impide evaluar: el juez no puede cambiar sin que se note.
- Cualquier «pendientes_de_verificar» impide evaluar.
Código 0 PASS · 1 BLOCKED. Uso: comprobar_versiones.py versiones.json
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

COMANDOS = {
    "claude": ["claude", "--version"], "bwrap": ["bwrap", "--version"], "socat": ["socat", "-V"],
    "python3": ["python3", "--version"], "git": ["git", "--version"], "node": ["node", "--version"], "codex": ["codex", "--version"],
}
EXCLUIR = {"__pycache__"}


def problemas_herramientas(verificadas: dict, ejecutar=subprocess.run, ubicar=shutil.which) -> list[str]:
    salida = []
    for herramienta, esperada in verificadas.items():
        comando = COMANDOS.get(herramienta)
        if comando is None:
            salida.append(f"{herramienta}: no se sabe cómo comprobarla")
            continue
        if ubicar(comando[0]) is None:
            salida.append(f"{herramienta}: no está instalada")
            continue
        resultado = ejecutar(comando, capture_output=True, text=True, timeout=60)
        palabras = f"{resultado.stdout} {resultado.stderr}".replace(",", " ").split()
        if esperada not in palabras and f"v{esperada}" not in palabras:
            salida.append(f"{herramienta}: se esperaba {esperada}; se encontró «{' '.join(palabras)[:80]}»")
    return salida


def problemas_fijados(fijados: dict, raiz: Path) -> list[str]:
    directorio = raiz / fijados.get("directorio", "")
    esperados = fijados.get("archivos")
    if not fijados.get("directorio") or not isinstance(esperados, dict) or not esperados:
        return ["«fijados» debe declarar el directorio y la huella de cada archivo"]
    if not directorio.is_dir():
        return [f"no existe la copia fijada {fijados['directorio']}"]
    presentes = {p.relative_to(directorio).as_posix(): p for p in directorio.rglob("*")
                 if p.is_file() and not any(parte in EXCLUIR for parte in p.relative_to(directorio).parts)}
    salida = [f"{fijados['directorio']}/{r}: no está en la lista fijada" for r in sorted(set(presentes) - set(esperados))]
    salida += [f"{fijados['directorio']}/{r}: falta" for r in sorted(set(esperados) - set(presentes))]
    salida += [f"{fijados['directorio']}/{r}: el contenido no es el fijado" for r in sorted(set(esperados) & set(presentes))
               if hashlib.sha256(presentes[r].read_bytes()).hexdigest() != esperados[r]]
    return salida


def problemas(versiones: dict, raiz: Path, ejecutar=subprocess.run, ubicar=shutil.which) -> list[str]:
    salida = [f"pendiente de verificar: {p}" for p in versiones.get("pendientes_de_verificar", [])]
    salida += problemas_herramientas(versiones.get("verificadas", {}), ejecutar, ubicar)
    if "fijados" in versiones:
        salida += problemas_fijados(versiones["fijados"], raiz)
    return salida


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ruta = Path(sys.argv[1]).resolve()
    # versiones.json vive en <repositorio del ejecutor>/ejecutor/; las rutas fijadas son relativas a ese repositorio.
    lista = problemas(json.loads(ruta.read_text(encoding="utf-8")), ruta.parent.parent)
    for p in lista:
        print(f"✘ {p}")
    print("herramientas y copia fijada: " + ("PASS" if not lista else "BLOCKED"))
    sys.exit(1 if lista else 0)
