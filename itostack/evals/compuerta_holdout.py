#!/usr/bin/env python3
"""Compuerta holdout: protocolo de aceptación de una skill candidata (sobre `claude plugin eval`).

1. Itera la skill con los casos de desarrollo hasta 10/10 sin fallos críticos (mejorar-skill + /loop).
2. `congelar`: con los resultados de desarrollo en 1.0 y el visto bueno de un juez de OTRA familia de modelos
   (revisar_codex.py o revisar_ollama.py --rol juez contra una rúbrica congelada de evals/rubricas), fija la huella de
   la candidata, la de la reserva y la identidad del juez. Una candidata congelada no se vuelve a congelar.
3. `reservar`: consume el ÚNICO intento holdout antes de correr nada (creación exclusiva de una marca).
4. Se corre `claude plugin eval --tag holdout` y el MISMO juez califica sus artefactos; después `holdout` registra la
   decisión con resultados y veredictos posteriores a la reserva. Si falla —o si el juez no aprueba, o ya reprobó esos
   artefactos en otra corrida—, la candidata queda RECHAZADA y esa huella no puede volver a intentarlo.
   Sin juez externo (exención declarada), `holdout` sin --resultados reserva y corre la evaluación él mismo.

Uso:
  compuerta_holdout.py huella --skill verificar-cita
  compuerta_holdout.py congelar --skill verificar-cita --resultados dev.json --juez v1.json [--juez v2.json]
  compuerta_holdout.py congelar --skill verificar-cita --resultados dev.json --sin-juez-externo "motivo"
  compuerta_holdout.py reservar --skill verificar-cita
  compuerta_holdout.py holdout --skill verificar-cita --resultados holdout.json --juez vh.json
  compuerta_holdout.py holdout --skill verificar-cita [-- <argumentos extra para claude plugin eval>]   (sin juez)
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
import time
from datetime import datetime, timezone
from pathlib import Path

EVALS = Path(__file__).resolve().parent
PLUGIN = EVALS.parent
sys.path.insert(0, str(PLUGIN / "scripts"))

from nucleo import config as cfg  # noqa: E402
from nucleo import juez as contrato_juez  # noqa: E402

COMPUERTA = EVALS / "compuerta"
HISTORIAL = COMPUERTA / "historial.tsv"
RUBRICAS = EVALS / "rubricas"
# Estado de la reserva holdout (decisión del operador). Solo «aislada» permite correr un holdout: los casos actuales los
# escribió el agente y están en la historia de Git, así que quedan «contaminada» hasta que CR-2 los aísle por permisos.
RESERVA_ESTADO = EVALS / "reserva.json"


def reserva_bloqueada() -> str | None:
    """Motivo por el que la reserva no admite un holdout, o None si está declarada aislada. Falla cerrado."""
    try:
        estado = json.loads(RESERVA_ESTADO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return f"no se pudo leer el estado de la reserva ({RESERVA_ESTADO.name})"
    if not isinstance(estado, dict) or estado.get("estado") != "aislada":
        motivo = estado.get("motivo") if isinstance(estado, dict) else None
        return f"la reserva holdout está «{estado.get('estado') if isinstance(estado, dict) else '?'}»" + (f": {motivo}" if motivo else "")
    return None
EXCLUIR = {"node_modules", "__pycache__", "results"}
CAMPOS_JUEZ = ("familia", "herramienta", "modelo", "esfuerzo", "version")


def _archivos(raiz: Path) -> list[Path]:
    if raiz.is_file():
        return [raiz]
    return sorted(p for p in raiz.rglob("*") if p.is_file()) if raiz.exists() else []


def huella(skill: str) -> str:
    """Huella de la candidata: la skill y todo lo que la evaluación usa (N-08), sin la reserva holdout.

    Incluye scripts, hooks, guardias y agentes (el juez), las rúbricas, los fixtures, el andamiaje común de los casos
    y los propios instrumentos (autoprueba y compuerta): cambiar cualquiera invalida lo congelado.

    No incluye la `.itostack/config.json` del operador (CR-4): cada caso corre en un espacio aislado que preparar.sh
    inicializa solo con archivos de esta huella (CONFIG_DEFECTO de scripts/, modo fixture, fixtures de evals/), así
    que esa configuración no llega al comportamiento evaluado. Incluirla invalidaba candidatas sin proteger nada.
    Condición de la corrida: sin ITOSTACK_PROYECTO ni ITOSTACK_MODO en el entorno (autoprueba.py los quita; con
    `claude plugin eval` lanzado a mano es responsabilidad del operador hasta CR-3).
    """
    resumen = hashlib.sha256()
    fuentes = [
        PLUGIN / "skills" / skill, PLUGIN / "scripts", PLUGIN / "hooks", PLUGIN / "guardias", PLUGIN / "agents",
        EVALS / skill, RUBRICAS, EVALS / "fixtures", EVALS / "_comun", EVALS / "autoprueba.py", EVALS / "compuerta_holdout.py",
    ]
    for raiz in fuentes:
        for archivo in _archivos(raiz):
            relativo = archivo.relative_to(PLUGIN)
            if any(parte in EXCLUIR for parte in relativo.parts) or any(parte.startswith("holdout-") for parte in relativo.parts):
                continue
            resumen.update(relativo.as_posix().encode())
            resumen.update(archivo.read_bytes())
    return resumen.hexdigest()


def huella_holdout(skill: str) -> str:
    """Huella de la reserva: si cambia después de congelar, el holdout ya no mide lo mismo."""
    resumen = hashlib.sha256()
    for directorio in sorted((EVALS / skill).glob("holdout-*")):
        for archivo in _archivos(directorio):
            relativo = archivo.relative_to(PLUGIN)
            if any(parte in EXCLUIR for parte in relativo.parts):
                continue
            resumen.update(relativo.as_posix().encode())
            resumen.update(archivo.read_bytes())
    return resumen.hexdigest()


def puntajes(datos) -> dict[str, float]:
    """Extrae {nombre_de_caso: puntaje} de la salida JSON de claude plugin eval, tolerando variaciones de esquema."""
    encontrados: dict[str, float] = {}
    if isinstance(datos, dict) and isinstance(datos.get("cases"), list):
        # Esquema 1 de claude plugin eval: cases[].name + cases[].aggregates.score (brazo con plugin)
        for caso in datos["cases"]:
            if not isinstance(caso, dict):
                continue
            agregados = caso.get("aggregates")
            puntaje = agregados.get("score") if isinstance(agregados, dict) else None
            if isinstance(caso.get("name"), str) and isinstance(puntaje, (int, float)) and not isinstance(puntaje, bool):
                encontrados[caso["name"]] = float(puntaje)
        if encontrados:
            return encontrados

    def recorrer(nodo) -> None:
        if isinstance(nodo, dict):
            nombre = next((nodo[k] for k in ("name", "case", "caseName", "case_name") if isinstance(nodo.get(k), str)), None)
            puntaje = next((nodo[k] for k in ("score", "meanScore", "mean_score") if isinstance(nodo.get(k), (int, float)) and not isinstance(nodo.get(k), bool)), None)
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


def _anotar(skill: str, huella_actual: str, evento: str, puntaje: float, decision: str, juez: str = "") -> None:
    COMPUERTA.mkdir(parents=True, exist_ok=True)
    if not HISTORIAL.exists():
        HISTORIAL.write_text("fecha\tskill\thuella\tevento\tpuntaje_min\tdecision\tjuez\n", encoding="utf-8")
    juez = " ".join(juez.split())
    with open(HISTORIAL, "a", encoding="utf-8") as archivo:
        archivo.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}\t{skill}\t{huella_actual}\t{evento}\t{puntaje:.2f}\t{decision}\t{juez}\n")


def rubrica_de(skill: str) -> Path | None:
    """La rúbrica autorizada para juzgar una skill (evals/rubricas/por_skill.json, parte de la huella)."""
    asignacion = json.loads((RUBRICAS / "por_skill.json").read_text(encoding="utf-8"))
    nombre = asignacion.get(skill)
    return RUBRICAS / nombre if nombre and (RUBRICAS / nombre).is_file() else None


def _rubricas_congeladas() -> dict[str, int]:
    """{sha256 de la rúbrica: cantidad de criterios} de evals/rubricas (forman parte de la huella)."""
    return {contrato_juez.sha256(r.read_bytes()): len(contrato_juez.criterios_de_rubrica(r.read_text(encoding="utf-8"))) for r in RUBRICAS.glob("*.md")}


def veredictos_juez(rutas: list[Path], desde: float | None = None, proyecto: Path | None = None, skill: str | None = None) -> tuple[dict | None, list[str], list[str], set[str], set[str]]:
    """Lee veredictos de revisar_codex.py / revisar_ollama.py --rol juez.

    Devuelve (identidad común del juez, errores, artefactos no aprobados, huellas de los artefactos calificados,
    casos de eval calificados).
    Exige: el contrato del veredicto guardado (juez.errores_contrato con guardado=True), rol juez de otra familia, una
    rúbrica congelada de evals/rubricas, cobertura exacta de sus criterios (el puntaje se recalcula: un `aprobado`
    editado a mano no cuenta) y, con `desde`, archivos posteriores a la reserva.
    Un veredicto ilegible, fuera de contrato o incompleto (sin puntaje) es BLOCKED: va a errores, nunca a aprobados
    ni a una decisión, y no lanza excepción.
    Con `proyecto`, un artefacto que ESE MISMO juez ya reprobó en otra corrida registrada en la bitácora cuenta como
    reprobado: repetir el juicio hasta obtener un aprobado no sirve.
    """
    errores: list[str] = []
    desaprobados: list[str] = []
    identidades: set[str] = set()
    huellas: set[str] = set()
    casos: set[str] = set()
    rubricas = _rubricas_congeladas()
    bitacora = contrato_juez.leer_bitacora(proyecto) if proyecto else []
    for ruta in rutas:
        ruta = Path(ruta)
        try:
            veredicto = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            errores.append(f"{ruta}: no es un veredicto JSON legible")
            continue
        contrato = contrato_juez.errores_contrato("juez", veredicto, guardado=True)
        if contrato:
            errores.append(f"{ruta}: BLOCKED, fuera del contrato del juez: {'; '.join(contrato[:5])}")
            continue
        datos_juez = veredicto["juez"]
        if datos_juez.get("rol") != "juez":
            errores.append(f"{ruta}: no es un veredicto del rol juez")
            continue
        modelo = str(datos_juez.get("modelo") or "")
        if not modelo or contrato_juez.es_familia_claude(modelo) or datos_juez.get("familia") in (None, "anthropic"):
            errores.append(f"{ruta}: el juez no es de otra familia de modelos que Claude")
            continue
        materia = veredicto.get("material") or {}
        huella_rubrica = (materia.get("rubrica") or {}).get("sha256")
        artefactos = sorted(h for h in materia.get("sha256_artefactos") or [] if h)
        if huella_rubrica not in rubricas:
            errores.append(f"{ruta}: la rúbrica calificada no es una rúbrica congelada de evals/rubricas")
            continue
        if skill:
            autorizada = rubrica_de(skill)
            if autorizada is None or contrato_juez.sha256(autorizada.read_bytes()) != huella_rubrica:
                errores.append(f"{ruta}: la rúbrica no es la asignada a {skill} en evals/rubricas/por_skill.json")
                continue
        if not artefactos:
            errores.append(f"{ruta}: el veredicto no identifica los artefactos que calificó")
            continue
        if desde is not None and ruta.stat().st_mtime < desde:
            errores.append(f"{ruta}: el veredicto es anterior a la reserva del holdout")
            continue
        identidades.add(json.dumps({k: datos_juez.get(k) for k in CAMPOS_JUEZ}, sort_keys=True))
        huellas.update(artefactos)
        if materia.get("caso"):
            casos.add(str(materia["caso"]))
        calificado = contrato_juez.calificar(veredicto, rubricas[huella_rubrica])
        if calificado["puntaje"] is None:
            errores.append(f"{ruta}: BLOCKED, veredicto sin puntaje: {calificado.get('cobertura')}")
            continue
        if not calificado["aprobado"]:
            desaprobados.append(f"{ruta}: puntaje {calificado['puntaje']}, {calificado.get('cobertura')}, fallos críticos {calificado['fallos_criticos'] or 'ninguno'}")
            continue
        clave = ",".join(artefactos)
        if any(",".join(sorted((f.get("sha256_artefactos") or "").split(","))) == clave and f.get("sha256_rubrica") == huella_rubrica
               and all(f.get(k) == str(datos_juez.get(k)) for k in CAMPOS_JUEZ) and f.get("aprobado") == "no" for f in bitacora):
            desaprobados.append(f"{ruta}: el juez ya reprobó estos mismos artefactos en otra corrida (bitácora del juez)")
    if len(identidades) > 1:
        errores.append("los veredictos vienen de jueces distintos")
    identidad = json.loads(next(iter(identidades))) if len(identidades) == 1 and not errores else None
    return identidad, errores, desaprobados, huellas, casos


def _describir(identidad: dict | None) -> str:
    if not identidad:
        return ""
    return f"{identidad.get('herramienta')}:{identidad.get('modelo')}@{identidad.get('esfuerzo')} ({identidad.get('version')})"


def _evaluar(skill: str, conjunto: str, ruta: Path) -> tuple[float, dict[str, float], set[str]]:
    try:
        obtenidos = puntajes(json.loads(Path(ruta).read_text(encoding="utf-8")))
    except (OSError, ValueError, RecursionError) as error:
        print(f"Resultados ilegibles ({ruta}): {error}")
        obtenidos = {}
    esperados = _casos(skill, conjunto)
    faltantes = esperados - obtenidos.keys()
    minimo = min((obtenidos[n] for n in esperados if n in obtenidos), default=0.0)
    return (0.0 if faltantes else minimo), obtenidos, faltantes


def congelar(skill: str, resultados: Path, jueces: list[Path] | tuple = (), sin_juez_externo: str | None = None) -> int:
    actual = huella(skill)
    candidata_ruta = COMPUERTA / f"{skill}.json"
    if any(f[1] == skill and f[2] == actual and f[3] == "congelado" for f in _historial()):
        print("Esta candidata ya se congeló antes (historial): su juez (o su exención) no se cambia. Para otro intento, cambia la skill.")
        return 1
    minimo, obtenidos, faltantes = _evaluar(skill, "desarrollo", resultados)
    if faltantes or minimo < 1.0:
        print(f"No se congela: desarrollo debe estar en 1.0 en todos los casos. Mínimo {minimo:.2f}; faltan {sorted(faltantes) or 'ninguno'}.")
        for nombre in sorted(_casos(skill, "desarrollo")):
            print(f"  {nombre}: {obtenidos.get(nombre, 'sin resultado')}")
        return 1
    motivo = (sin_juez_externo or "").strip()
    identidad, huellas = None, set()
    if jueces:
        identidad, errores, desaprobados, huellas, _ = veredictos_juez(list(jueces), proyecto=cfg.raiz_proyecto(), skill=skill)
        if errores or desaprobados:
            print("No se congela: el juez de otra familia no da su visto bueno.")
            for problema in errores + desaprobados:
                print(f"  {problema}")
            return 1
    elif not motivo:
        print("No se congela: falta el juez de otra familia. Califica los artefactos de desarrollo con "
              "`revisar_codex.py --rol juez --rubrica <rúbrica congelada>` y pásalos con --juez, o declara por qué no "
              "con --sin-juez-externo \"motivo\" (queda en el historial y la aceptación lo dirá).")
        return 1
    COMPUERTA.mkdir(parents=True, exist_ok=True)
    # Congelar es una transición única por huella: dos invocaciones simultáneas (o una interrumpida) no pueden dejar
    # jueces o exenciones distintos para la misma candidata.
    try:
        with open(COMPUERTA / f"{skill}.{actual[:16]}.congelado", "x", encoding="utf-8") as marca:
            marca.write(json.dumps({"juez": identidad, "sin_juez_externo": motivo or None}, ensure_ascii=False) + "\n")
    except FileExistsError:
        print("Esta candidata ya se congeló (o se está congelando): su juez o su exención no se cambian.")
        return 1
    candidata = {
        "skill": skill, "huella": actual, "huella_holdout": huella_holdout(skill),
        "congelado": datetime.now(timezone.utc).isoformat(timespec="seconds"), "juez": identidad,
        "artefactos_desarrollo": sorted(huellas),
    }
    if not identidad:
        candidata["sin_juez_externo"] = motivo
    candidata_ruta.write_text(json.dumps(candidata, ensure_ascii=False, indent=2), encoding="utf-8")
    _anotar(skill, actual, "congelado", minimo, "CANDIDATA", _describir(identidad) or f"sin juez externo: {motivo}")
    print(f"Candidata congelada: {skill} · huella {actual[:16]}… · juez {_describir(identidad) or 'ninguno (declarado)'}")
    print(f"Siguiente: compuerta_holdout.py reservar --skill {skill}" if identidad else f"Siguiente: compuerta_holdout.py holdout --skill {skill}")
    return 0


def _candidata_vigente(skill: str) -> tuple[dict | None, str]:
    candidata_ruta = COMPUERTA / f"{skill}.json"
    if not candidata_ruta.is_file():
        print("No hay candidata congelada: ejecuta primero `congelar` con resultados de desarrollo en 1.0.")
        return None, ""
    candidata = json.loads(candidata_ruta.read_text(encoding="utf-8"))
    actual = huella(skill)
    if actual != candidata["huella"]:
        print("La skill o sus scripts cambiaron después de congelar. Vuelve a correr desarrollo y a congelar.")
        return None, ""
    if candidata.get("huella_holdout") and candidata["huella_holdout"] != huella_holdout(skill):
        print("La reserva holdout cambió después de congelar: el resultado ya no mediría lo mismo. Vuelve a congelar.")
        return None, ""
    if any(f[1] == skill and f[2] == actual and f[3] == "holdout" for f in _historial()):
        print("El holdout ya se consumió para esta candidata. Rediseña la skill (y la eval si hace falta) y repite el ciclo.")
        return None, ""
    return candidata, actual


def _marca(skill: str, actual: str) -> Path:
    return COMPUERTA / f"{skill}.{actual[:16]}.consumido"


def _tomar_reserva(skill: str, actual: str, candidata: dict) -> bool:
    """N-07: el intento se consume ANTES de correr. Una interrupción, una salida ilegible o una segunda invocación
    simultánea ya no permiten repetir el holdout (la creación exclusiva del archivo es atómica)."""
    try:
        with open(_marca(skill, actual), "x", encoding="utf-8") as marca:
            marca.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}\n{time.time():.6f}\n")
    except FileExistsError:
        print("El holdout ya se reservó para esta candidata: su único intento está en curso o consumido.")
        return False
    _anotar(skill, actual, "holdout-iniciado", 0.0, "EN CURSO", _describir(candidata.get("juez")))
    return True


def _instante_de_reserva(marca: Path) -> float:
    """Instante exacto de la reserva (segunda línea de la marca), sin tolerancia: un archivo anterior no cuenta."""
    lineas = marca.read_text(encoding="utf-8").split()
    try:
        return float(lineas[1])
    except (IndexError, ValueError):
        return datetime.fromisoformat(lineas[0]).timestamp() + 1  # marca sin instante preciso: el segundo siguiente


def reservar(skill: str) -> int:
    if bloqueo := reserva_bloqueada():
        print(f"No se reserva: {bloqueo}. Un holdout sobre una reserva contaminada no mide generalización.")
        return 1
    candidata, actual = _candidata_vigente(skill)
    if not candidata or not _tomar_reserva(skill, actual, candidata):
        return 1
    print(f"Intento holdout reservado y consumido: {skill} · huella {actual[:16]}….")
    print(f"Ahora: claude plugin eval <plugin> --tag holdout --case \"{skill}.*\" --runs 1 --scaffold --json h.json; "
          "califica sus artefactos con el juez congelado y registra con: compuerta_holdout.py holdout --skill "
          f"{skill} --resultados h.json --juez <veredicto.json>")
    return 0


def holdout(skill: str, resultados: Path | None, extra: list[str], jueces: list[Path] | tuple = ()) -> int:
    if bloqueo := reserva_bloqueada():
        print(f"No se registra ni se corre el holdout: {bloqueo}.")
        return 1
    candidata, actual = _candidata_vigente(skill)
    if not candidata:
        return 1
    congelado_con = candidata.get("juez")
    marca = _marca(skill, actual)
    desaprobados: list[str] = []
    if resultados is None:
        if congelado_con:
            print("Esta candidata tiene juez de otra familia: usa `reservar`, corre el holdout, califica sus artefactos y "
                  "registra con --resultados y --juez.")
            return 1
        if not _tomar_reserva(skill, actual, candidata):
            return 1
        resultados = Path(tempfile.mkstemp(suffix=".json")[1])
        comando = [shutil.which("claude") or "claude", "plugin", "eval", str(PLUGIN), "--tag", "holdout", "--case", f"{skill}.*", "--runs", "1", "--scaffold", "--json", str(resultados), *extra]
        print("Ejecutando:", " ".join(comando))
        subprocess.run(comando, check=False)
    else:
        if not marca.is_file():
            print(f"Primero reserva el intento (compuerta_holdout.py reservar --skill {skill}) y después corre el holdout: "
                  "unos resultados obtenidos sin reserva podrían ser el mejor de varios intentos.")
            return 1
        reserva = _instante_de_reserva(marca)
        if Path(resultados).is_file() and Path(resultados).stat().st_mtime < reserva:
            print("Los resultados son anteriores a la reserva: no corresponden al intento reservado.")
            return 1
        if congelado_con:
            if not jueces:
                print("Falta el veredicto del juez congelado sobre los artefactos del holdout (--juez).")
                return 1
            identidad, errores, desaprobados, huellas, casos = veredictos_juez(list(jueces), desde=reserva, proyecto=cfg.raiz_proyecto(), skill=skill)
            reutilizados = huellas & set(candidata.get("artefactos_desarrollo") or [])
            if reutilizados:
                errores.append("un veredicto califica artefactos de desarrollo, no del holdout")
            sin_juicio = _casos(skill, "holdout") - casos
            if sin_juicio:
                errores.append(f"falta el veredicto del juez para cada caso holdout (--caso en revisar_codex.py): {sorted(sin_juicio)}")
            if errores:
                print("Veredictos del juez inválidos; corrígelos y vuelve a registrar (el intento sigue reservado):")
                for problema in errores:
                    print(f"  {problema}")
                return 1
            if identidad != congelado_con:
                print(f"El juez cambió después de congelar ({_describir(congelado_con)} → {_describir(identidad)}): "
                      "califica con el juez congelado.")
                return 1
    # La decisión se escribe una sola vez: dos registros simultáneos de la misma reserva no pueden dejar un
    # ACEPTADA después de un RECHAZADA.
    try:
        with open(COMPUERTA / f"{skill}.{actual[:16]}.decidido", "x", encoding="utf-8") as decidido:
            decidido.write(datetime.now(timezone.utc).isoformat(timespec="seconds") + "\n")
    except FileExistsError:
        print("La decisión de este holdout ya se registró (u otra invocación la está registrando).")
        return 1
    minimo, obtenidos, faltantes = _evaluar(skill, "holdout", resultados)
    aprobada = minimo == 1.0 and not faltantes and not desaprobados
    decision = ("ACEPTADA" if congelado_con else "ACEPTADA SIN JUEZ EXTERNO") if aprobada else "RECHAZADA"
    _anotar(skill, actual, "holdout", minimo, decision, _describir(congelado_con) or f"sin juez externo: {candidata.get('sin_juez_externo', '')}")
    for nombre in sorted(_casos(skill, "holdout")):
        print(f"  {nombre}: {obtenidos.get(nombre, 'sin resultado')}")
    for problema in desaprobados:
        print(f"  juez: {problema}")
    print(f"Holdout {skill}: {decision} (mínimo {minimo:.2f}). Trazas completas en el directorio de resultados de claude plugin eval.")
    return 0 if aprobada else 1


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
    p_c.add_argument("--juez", type=Path, action="append", default=[], help="veredicto de revisar_codex.py/revisar_ollama.py --rol juez")
    p_c.add_argument("--sin-juez-externo", metavar="MOTIVO", help="congelar sin juez de otra familia, con el motivo en el historial")
    p_r = sub.add_parser("reservar")
    p_r.add_argument("--skill", required=True)
    p_o = sub.add_parser("holdout")
    p_o.add_argument("--skill", required=True)
    p_o.add_argument("--resultados", type=Path)
    p_o.add_argument("--juez", type=Path, action="append", default=[])
    sub.add_parser("estado")
    args = analizador.parse_args(argv)
    if args.accion == "huella":
        print(huella(args.skill))
        return 0
    if args.accion == "congelar":
        return congelar(args.skill, args.resultados, args.juez, args.sin_juez_externo)
    if args.accion == "reservar":
        return reservar(args.skill)
    if args.accion == "holdout":
        return holdout(args.skill, args.resultados, extra, args.juez)
    for fila in _historial():
        print(" · ".join([fila[0], fila[1], fila[2][:12], *fila[3:]]))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
