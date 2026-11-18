#!/usr/bin/env python3
"""Compuerta holdout: protocolo de aceptación de una skill candidata (sobre `claude plugin eval`).

1. Itera la skill con los casos de desarrollo hasta 10/10 sin fallos críticos (mejorar-skill + /loop).
2. `congelar`: con los resultados de desarrollo en 1.0, fija la huella de la candidata (skill + scripts + casos dev).
3. `holdout`: corre UNA sola vez los casos holdout-* de esa skill. Si falla, la candidata queda RECHAZADA y esa
   huella no puede volver a intentarlo: hay que rediseñar la skill (y quizá la eval) y volver al paso 1.

Uso:
  compuerta_holdout.py huella --skill verificar-cita
  compuerta_holdout.py congelar --skill verificar-cita --resultados dev.json
  compuerta_holdout.py holdout --skill verificar-cita [--resultados holdout.json] [-- <argumentos extra para claude plugin eval>]
  compuerta_holdout.py estado
Los resultados se obtienen con: claude plugin eval <plugin> --tag desarrollo --case "verificar-cita.*" --scaffold --json dev.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

EVALS = Path(__file__).resolve().parent
PLUGIN = EVALS.parent
COMPUERTA = EVALS / "compuerta"
HISTORIAL = COMPUERTA / "historial.tsv"
EXCLUIR = {"node_modules", "__pycache__", "results"}


def huella(skill: str) -> str:
    resumen = hashlib.sha256()
    fuentes = [PLUGIN / "skills" / skill, PLUGIN / "scripts", PLUGIN / "hooks", PLUGIN / "guardias", EVALS / skill]
    for raiz in fuentes:
        if not raiz.exists():
            continue
        for archivo in sorted(p for p in raiz.rglob("*") if p.is_file()):
            relativo = archivo.relative_to(PLUGIN)
            if any(parte in EXCLUIR for parte in relativo.parts) or any(parte.startswith("holdout-") for parte in relativo.parts):
                continue
            resumen.update(str(relativo).encode())
            resumen.update(archivo.read_bytes())
    return resumen.hexdigest()


def puntajes(datos) -> dict[str, float]:
    """Extrae {nombre_de_caso: puntaje} de la salida JSON de claude plugin eval, tolerando variaciones de esquema."""
    encontrados: dict[str, float] = {}
    if isinstance(datos, dict) and isinstance(datos.get("cases"), list):
        # Esquema 1 de claude plugin eval: cases[].name + cases[].aggregates.score (brazo con plugin)
        for caso in datos["cases"]:
            puntaje = (caso.get("aggregates") or {}).get("score")
            if isinstance(caso.get("name"), str) and isinstance(puntaje, (int, float)):
                encontrados[caso["name"]] = float(puntaje)
        if encontrados:
            return encontrados

    def recorrer(nodo) -> None:
        if isinstance(nodo, dict):
            nombre = next((nodo[k] for k in ("name", "case", "caseName", "case_name") if isinstance(nodo.get(k), str)), None)
            puntaje = next((nodo[k] for k in ("score", "meanScore", "mean_score") if isinstance(nodo.get(k), (int, float))), None)
            if nombre and puntaje is not None and "." in nombre:
                encontrados[nombre] = min(float(puntaje), encontrados.get(nombre, float(puntaje)))
            for valor in nodo.values():
                recorrer(valor)
        elif isinstance(nodo, list):
            for valor in nodo:
                recorrer(valor)

    recorrer(datos)
    return encontrados


def _casos(skill: str, conjunto: str) -> set[str]:
    nombres = set()
    for case in (EVALS / skill).glob("*/case.yaml"):
        es_holdout = case.parent.name.startswith("holdout-")
        if (conjunto == "holdout") == es_holdout:
            nombres.add(f"{skill}.{case.parent.name}")
    return nombres


def _historial() -> list[list[str]]:
    if not HISTORIAL.is_file():
        return []
    return [l.split("\t") for l in HISTORIAL.read_text(encoding="utf-8").splitlines()[1:] if l.strip()]


def _anotar(skill: str, huella_actual: str, evento: str, puntaje: float, decision: str) -> None:
    COMPUERTA.mkdir(parents=True, exist_ok=True)
    if not HISTORIAL.exists():
        HISTORIAL.write_text("fecha\tskill\thuella\tevento\tpuntaje_min\tdecision\n", encoding="utf-8")
    with open(HISTORIAL, "a", encoding="utf-8") as archivo:
        archivo.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}\t{skill}\t{huella_actual}\t{evento}\t{puntaje:.2f}\t{decision}\n")


def _evaluar(skill: str, conjunto: str, ruta: Path) -> tuple[float, dict[str, float], set[str]]:
    obtenidos = puntajes(json.loads(ruta.read_text(encoding="utf-8")))
    esperados = _casos(skill, conjunto)
    faltantes = esperados - obtenidos.keys()
    minimo = min((obtenidos[n] for n in esperados if n in obtenidos), default=0.0)
    return (0.0 if faltantes else minimo), obtenidos, faltantes


def congelar(skill: str, resultados: Path) -> int:
    minimo, obtenidos, faltantes = _evaluar(skill, "desarrollo", resultados)
    if faltantes or minimo < 1.0:
        print(f"No se congela: desarrollo debe estar en 1.0 en todos los casos. Mínimo {minimo:.2f}; faltan {sorted(faltantes) or 'ninguno'}.")
        for nombre in sorted(_casos(skill, "desarrollo")):
            print(f"  {nombre}: {obtenidos.get(nombre, 'sin resultado')}")
        return 1
    actual = huella(skill)
    COMPUERTA.mkdir(parents=True, exist_ok=True)
    (COMPUERTA / f"{skill}.json").write_text(json.dumps({"skill": skill, "huella": actual, "congelado": datetime.now(timezone.utc).isoformat(timespec="seconds")}, indent=2), encoding="utf-8")
    _anotar(skill, actual, "congelado", minimo, "CANDIDATA")
    print(f"Candidata congelada: {skill} · huella {actual[:16]}…  Siguiente: compuerta_holdout.py holdout --skill {skill}")
    return 0


def holdout(skill: str, resultados: Path | None, extra: list[str]) -> int:
    candidata_ruta = COMPUERTA / f"{skill}.json"
    if not candidata_ruta.is_file():
        print("No hay candidata congelada: ejecuta primero `congelar` con resultados de desarrollo en 1.0.")
        return 1
    candidata = json.loads(candidata_ruta.read_text(encoding="utf-8"))
    actual = huella(skill)
    if actual != candidata["huella"]:
        print("La skill o sus scripts cambiaron después de congelar. Vuelve a correr desarrollo y a congelar.")
        return 1
    if any(f[1] == skill and f[2] == actual and f[3] == "holdout" for f in _historial()):
        print("El holdout ya se consumió para esta candidata. Rediseña la skill (y la eval si hace falta) y repite el ciclo.")
        return 1
    if resultados is None:
        resultados = Path(tempfile.mkstemp(suffix=".json")[1])
        comando = [shutil.which("claude") or "claude", "plugin", "eval", str(PLUGIN), "--tag", "holdout", "--case", f"{skill}.*", "--runs", "1", "--scaffold", "--json", str(resultados), *extra]
        print("Ejecutando:", " ".join(comando))
        subprocess.run(comando, check=False)
    minimo, obtenidos, faltantes = _evaluar(skill, "holdout", resultados)
    decision = "ACEPTADA" if minimo == 1.0 and not faltantes else "RECHAZADA"
    _anotar(skill, actual, "holdout", minimo, decision)
    for nombre in sorted(_casos(skill, "holdout")):
        print(f"  {nombre}: {obtenidos.get(nombre, 'sin resultado')}")
    print(f"Holdout {skill}: {decision} (mínimo {minimo:.2f}). Trazas completas en el directorio de resultados de claude plugin eval.")
    return 0 if decision == "ACEPTADA" else 1


def principal() -> int:
    argv = sys.argv[1:]
    extra: list[str] = []
    if "--" in argv:
        indice = argv.index("--")
        argv, extra = argv[:indice], argv[indice + 1:]
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = analizador.add_subparsers(dest="accion", required=True)
    p_h = sub.add_parser("huella")
    p_h.add_argument("--skill", required=True)
    p_c = sub.add_parser("congelar")
    p_c.add_argument("--skill", required=True)
    p_c.add_argument("--resultados", type=Path, required=True)
    p_o = sub.add_parser("holdout")
    p_o.add_argument("--skill", required=True)
    p_o.add_argument("--resultados", type=Path)
    sub.add_parser("estado")
    args = analizador.parse_args(argv)
    if args.accion == "huella":
        print(huella(args.skill))
        return 0
    if args.accion == "congelar":
        return congelar(args.skill, args.resultados)
    if args.accion == "holdout":
        return holdout(args.skill, args.resultados, extra)
    for fila in _historial():
        print(" · ".join([fila[0], fila[1], fila[2][:12], fila[3], fila[4], fila[5]]))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
