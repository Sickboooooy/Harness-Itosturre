#!/usr/bin/env python3
"""Lint de arquitectura Itosturre (capa 2 de la pirámide invertida).

Cada regla nace de una corrección repetida. El mensaje de error explica la causa raíz y la
alternativa correcta, porque el agente lo leerá como instrucción.

Uso:
  lint_itosturre.py RUTA...            revisa archivos completos
  lint_itosturre.py --diff [BASE]      revisa solo líneas añadidas respecto a BASE (defecto HEAD)
Excepción auditable, en la misma línea o la anterior (justificación obligatoria, ≥10 caracteres):
  # itostack: permitir IT004 — servicio interno en la red local del despacho
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path

CODIGO = (".py", ".ts", ".tsx", ".js", ".mjs", ".cjs")
DOMINIOS_PERMITIDOS = r"(?:127\.0\.0\.1|localhost|\[::1\]|sjf2?\.scjn\.gob\.mx|(?:www\.)?dof\.gob\.mx|(?:www\.)?diputados\.gob\.mx)"
RE_PRAGMA = re.compile(r"itostack:\s*permitir\s+(IT\d{3})\s*[—\-:]+\s*(.{10,})")


@dataclass(frozen=True)
class Regla:
    codigo: str
    patron: re.Pattern
    mensaje: str
    extensiones: tuple[str, ...] = CODIGO
    excepto_linea: re.Pattern | None = None
    archivos_exentos: tuple[str, ...] = ()


REGLAS: tuple[Regla, ...] = (
    Regla(
        "IT001",
        re.compile(r"""(?:\.goto\(|\.get\(|requests\.\w+\(|fetch\(|urlopen\(|httpx\.\w+\(|curl\s).{0,200}scjn\.gob\.mx"""),
        "Visita a la SCJN sin evidencia forense. Toda consulta pasa por visitarConEvidencia() de "
        "scripts/lib/navegador_forense.ts (captura + SHA-256) o por verificar.py; nunca page.goto()/fetch() directos.",
        archivos_exentos=("*/lib/navegador_forense.ts", "*/verificador_fuente.ts"),
    ),
    Regla(
        "IT002",
        re.compile(r"postgres(?:ql)?(?:\+\w+)?://|mysql://|mongodb(?:\+srv)?://|\bimport\s+psycopg|\bfrom\s+psycopg|\bfrom\s+supabase\b|@supabase/|\bimport\s+pymongo"),
        "Base de datos fuera del MVP. Itosturre usa SQLite (itosturre.db como fuente única de verdad); "
        "Postgres, Supabase o Mongo quedan fuera hasta que el operador lo decida.",
    ),
    Regla(
        "IT003",
        re.compile(r"\bfrom\s+fastapi\b|\bimport\s+fastapi\b"),
        "Backend en Flask, no FastAPI (decisión de stack del operador).",
        extensiones=(".py",),
    ),
    Regla(
        "IT004",
        re.compile(r"""(?:requests|httpx)\.(?:post|put|patch)\(\s*f?["']https?://(?!""" + DOMINIOS_PERMITIDOS + r""")"""
                   r"""|fetch\(\s*[`"']https?://(?!""" + DOMINIOS_PERMITIDOS + r""")[^`"']*[`"']\s*,\s*\{[^}]*method\s*:\s*["'](?:POST|PUT|PATCH)"""),
        "Envío de datos a un servidor externo. Los datos legales nunca salen de la máquina: usa servicios en "
        "127.0.0.1 o, si es un portal oficial, agrégalo a dominios_oficiales en .itostack/config.json.",
    ),
    Regla(
        "IT005",
        re.compile(r"api\.openai\.com|api\.anthropic\.com|generativelanguage\.googleapis\.com|api\.deepseek\.com|api\.x\.ai|api\.mistral\.ai"),
        "Llamada a un LLM en la nube desde código de producto. El procesamiento de Itosturre es 100 % local: "
        "usa Ollama en http://127.0.0.1:11434.",
    ),
    Regla(
        "IT006",
        re.compile(r"""executemany\([^)]*(?:tesis|jurisprudencia)|/tesis/ids\b|descarga_masiva|bulk_(?:insert|download).{0,40}tesis""", re.IGNORECASE),
        "Ingesta masiva de jurisprudencia. El modelo Itosturre es consulta en tiempo real con evidencia por "
        "consulta; no se construyen bases masivas de tesis.",
    ),
    Regla(
        "IT007",
        re.compile(r"\bwaitForTimeout\s*\("),
        "Espera por tiempo fijo. Espera por condición observable (locator.waitFor, getByText, waitForResponse): "
        "los temporizadores ocultan la causa raíz y vuelven frágil la evidencia.",
        extensiones=(".ts", ".tsx", ".js", ".mjs"),
    ),
    Regla(
        "IT008",
        re.compile(r"(?:#|//|/\*).*\b(?:HACK|FIXME|XXX|workaround|parche\s+temporal|por\s+ahora|soluci[oó]n\s+temporal|chapuza)\b", re.IGNORECASE),
        "Comentario que documenta un parche. Los agentes copian los patrones que leen: resuelve la causa raíz "
        "o registra el pendiente en el gestor de incidencias, no en el código.",
        excepto_linea=re.compile(r"itostack:\s*permitir"),
    ),
)


@dataclass(frozen=True)
class Hallazgo:
    archivo: str
    linea: int
    codigo: str
    mensaje: str
    texto: str

    def formato(self) -> str:
        return f"{self.archivo}:{self.linea}: {self.codigo} {self.mensaje}\n    → {self.texto.strip()[:160]}"


def _pragmas(lineas: list[str], indice: int) -> set[str]:
    codigos = set()
    for candidata in (lineas[indice], lineas[indice - 1] if indice > 0 else ""):
        for m in RE_PRAGMA.finditer(candidata):
            codigos.add(m.group(1))
    return codigos


def revisar_texto(texto: str, ruta: str, numeros_linea: list[int] | None = None) -> list[Hallazgo]:
    sufijo = Path(ruta).suffix
    if sufijo not in CODIGO or fnmatch.fnmatch(ruta, "*guardias/lint_itosturre.py"):
        return []
    lineas = texto.splitlines()
    hallazgos = []
    for indice, linea in enumerate(lineas):
        permitidos = _pragmas(lineas, indice)
        for regla in REGLAS:
            if sufijo not in regla.extensiones or regla.codigo in permitidos:
                continue
            if any(fnmatch.fnmatch(ruta, patron) for patron in regla.archivos_exentos):
                continue
            if regla.excepto_linea and regla.excepto_linea.search(linea):
                continue
            if regla.patron.search(linea):
                numero = numeros_linea[indice] if numeros_linea else indice + 1
                hallazgos.append(Hallazgo(ruta, numero, regla.codigo, regla.mensaje, linea))
    return hallazgos


def revisar_archivos(rutas: list[Path]) -> list[Hallazgo]:
    hallazgos = []
    for ruta in rutas:
        archivos = [p for p in ruta.rglob("*") if p.suffix in CODIGO and "node_modules" not in p.parts] if ruta.is_dir() else [ruta]
        for archivo in archivos:
            try:
                hallazgos.extend(revisar_texto(archivo.read_text(encoding="utf-8"), str(archivo)))
            except (UnicodeDecodeError, FileNotFoundError):
                continue
    return hallazgos


class ErrorGit(RuntimeError):
    pass


def _git(*argumentos: str) -> str:
    proceso = subprocess.run(["git", *argumentos], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if proceso.returncode != 0:
        raise ErrorGit(f"git {' '.join(argumentos[:2])} falló ({proceso.returncode}): {proceso.stderr.strip()[:300]}")
    return proceso.stdout


def revisar_diff(base: str) -> tuple[list[Hallazgo], int, int, list[str]]:
    """Líneas añadidas respecto a BASE y archivos nuevos sin rastrear (D-10: `git diff` no los ve).

    Devuelve (hallazgos, archivos examinados, líneas examinadas, archivos que no se pudieron leer). Un error de Git
    es un error, no un verde vacío.
    """
    globs = [f"*{s}" for s in CODIGO]
    salida = _git("diff", "-U0", base, "--", *globs)
    hallazgos, archivo, numero = [], "", 0
    lineas_por_archivo: dict[str, tuple[list[str], list[int]]] = {}
    for linea in salida.splitlines():
        if linea.startswith("+++ "):
            archivo = linea[6:] if linea.startswith("+++ b/") else ""
        elif linea.startswith("@@"):
            m = re.search(r"\+(\d+)", linea)
            numero = int(m.group(1)) if m else 0
        elif linea.startswith("+") and archivo:
            textos, numeros = lineas_por_archivo.setdefault(archivo, ([], []))
            textos.append(linea[1:])
            numeros.append(numero)
            numero += 1
    raiz = Path(_git("rev-parse", "--show-toplevel").strip())
    no_examinados: list[str] = []
    # -z: sin él, Git entrecomilla y escapa los nombres no ASCII («nuevo_ñ.py») y el archivo se saltaría.
    for relativo in _git("ls-files", "--others", "--exclude-standard", "--full-name", "-z", "--", *globs).split("\0"):
        if not relativo.strip() or "node_modules" in Path(relativo).parts:
            continue
        try:
            contenido = _leer_codigo(raiz / relativo).splitlines()
        except (UnicodeDecodeError, SyntaxError, LookupError, OSError):
            no_examinados.append(relativo)
            continue
        lineas_por_archivo[relativo] = (contenido, list(range(1, len(contenido) + 1)))
    for archivo, (textos, numeros) in lineas_por_archivo.items():
        hallazgos.extend(revisar_texto("\n".join(textos), archivo, numeros))
    return hallazgos, len(lineas_por_archivo), sum(len(textos) for textos, _ in lineas_por_archivo.values()), no_examinados


def _leer_codigo(ruta: Path) -> str:
    """UTF-8, o la codificación que declare un .py («# coding: cp1252»): un archivo válido no se salta."""
    try:
        return ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        if ruta.suffix != ".py":
            raise
        with tokenize.open(ruta) as archivo:
            return archivo.read()


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("rutas", nargs="*", type=Path)
    analizador.add_argument("--diff", nargs="?", const="HEAD", help="revisa las líneas añadidas respecto a BASE y los archivos nuevos sin rastrear; sale con 2 si no examinó nada")
    args = analizador.parse_args()
    cobertura = ""
    if args.diff:
        try:
            hallazgos, archivos, lineas, no_examinados = revisar_diff(args.diff)
        except ErrorGit as error:
            print(f"lint itosturre: {error}. Sin diff no hay comprobación.")
            return 2
        if no_examinados:
            for hallazgo in hallazgos:
                print(hallazgo.formato())
            print(f"lint itosturre: no se pudieron leer {len(no_examinados)} archivo(s) nuevos: {', '.join(no_examinados)}. Resultado incompleto.")
            return 2
        cobertura = f" · examinados {archivos} archivo(s), {lineas} línea(s) nuevas o añadidas"
        if not archivos:
            print("lint itosturre: 0 archivos de código examinados: el diff no tiene cambios de código. Esto no acredita el cambio.")
            return 2
    elif args.rutas:
        hallazgos = revisar_archivos(args.rutas)
    else:
        analizador.error("indica rutas o --diff")
    for hallazgo in hallazgos:
        print(hallazgo.formato())
    print(f"lint itosturre: {len(hallazgos)} hallazgo(s){cobertura}")
    return 1 if hallazgos else 0


if __name__ == "__main__":
    sys.exit(principal())
