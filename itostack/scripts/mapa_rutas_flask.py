#!/usr/bin/env python3
"""Palanca determinista para el mapa de funcionalidades: rutas Flask y selectores data-testid.

Analiza el código sin ejecutarlo (AST + regex), así que es seguro en cualquier repositorio.
Uso: mapa_rutas_flask.py [RAIZ] [--json]
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

EXCLUIR = {".git", "node_modules", ".venv", "venv", "__pycache__", ".itostack", "dist", "build"}
RE_TESTID = re.compile(r"""data-testid\s*=\s*["']([^"']+)["']""")


def _archivos(raiz: Path, sufijos: tuple[str, ...]):
    for ruta in raiz.rglob("*"):
        if ruta.suffix in sufijos and not any(parte in EXCLUIR for parte in ruta.parts):
            yield ruta


def _literal(nodo: ast.AST) -> str | None:
    return nodo.value if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str) else None


def rutas_flask(raiz: Path) -> list[dict]:
    rutas = []
    for archivo in _archivos(raiz, (".py",)):
        try:
            arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        prefijos: dict[str, str] = {}
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Assign) and isinstance(nodo.value, ast.Call) and getattr(nodo.value.func, "id", getattr(nodo.value.func, "attr", "")) == "Blueprint":
                prefijo = next((_literal(k.value) for k in nodo.value.keywords if k.arg == "url_prefix"), "") or ""
                for objetivo in nodo.targets:
                    if isinstance(objetivo, ast.Name):
                        prefijos[objetivo.id] = prefijo
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorador in nodo.decorator_list:
                if not (isinstance(decorador, ast.Call) and isinstance(decorador.func, ast.Attribute)):
                    continue
                metodo = decorador.func.attr
                if metodo not in {"route", "get", "post", "put", "delete", "patch"} or not decorador.args:
                    continue
                camino = _literal(decorador.args[0])
                if camino is None:
                    continue
                dueno = decorador.func.value.id if isinstance(decorador.func.value, ast.Name) else "?"
                metodos = [metodo.upper()] if metodo != "route" else ["GET"]
                for clave in decorador.keywords:
                    if clave.arg == "methods" and isinstance(clave.value, (ast.List, ast.Tuple)):
                        metodos = [m for m in (_literal(e) for e in clave.value.elts) if m]
                rutas.append({
                    "ruta": prefijos.get(dueno, "") + camino,
                    "metodos": metodos,
                    "funcion": nodo.name,
                    "archivo": f"{archivo.relative_to(raiz)}:{nodo.lineno}",
                })
    return sorted(rutas, key=lambda r: r["ruta"])


def selectores(raiz: Path) -> dict[str, list[str]]:
    encontrados: dict[str, list[str]] = {}
    for archivo in _archivos(raiz, (".html", ".jinja", ".j2", ".tsx", ".jsx", ".ts", ".js", ".vue")):
        try:
            ids = sorted(set(RE_TESTID.findall(archivo.read_text(encoding="utf-8"))))
        except UnicodeDecodeError:
            continue
        if ids:
            encontrados[str(archivo.relative_to(raiz))] = ids
    return encontrados


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("raiz", nargs="?", default=".", type=Path)
    analizador.add_argument("--json", action="store_true")
    args = analizador.parse_args()
    raiz = args.raiz.resolve()
    datos = {"rutas": rutas_flask(raiz), "selectores": selectores(raiz)}
    if args.json:
        print(json.dumps(datos, ensure_ascii=False, indent=2))
        return 0
    print("## Rutas Flask\n\n| Ruta | Métodos | Función | Archivo |\n|---|---|---|---|")
    for r in datos["rutas"]:
        print(f"| `{r['ruta']}` | {', '.join(r['metodos'])} | `{r['funcion']}` | `{r['archivo']}` |")
    print("\n## Selectores estables (data-testid)\n")
    for archivo, ids in datos["selectores"].items():
        print(f"- `{archivo}`: " + ", ".join(f"`[data-testid={i}]`" for i in ids))
    if not datos["selectores"]:
        print("- (ninguno) — agrega data-testid a los controles que el agente deba operar.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
