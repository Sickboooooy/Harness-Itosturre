"""Orquestador del holdout (CR-3; contrato en docs/contrato-cr3.md): la compuerta PRODUCE resultados y veredictos.

Incremento CR-3.2a — núcleo verificable con pruebas sintéticas locales:
- Contrato de resultados de `claude plugin eval` (R1–R8) con cuatro estados distinguibles por caso:
  ACEPTA · RECHAZA (fallo de la candidata) · INFRAESTRUCTURA (la evaluación no ocurrió bien) · FUERA_DE_CONTRATO
  (resultado que no se reconoce: evaluación bloqueada). Ningún puntaje se lee si hubo una falla de infraestructura.
- Entorno construido desde cero con lista de permitidas (E1) y prohibidas que nunca pasan (E2).
- Invocación con la publicación desactivada (V1).
- Vínculos caso–rúbrica–evaluador–artefactos–veredicto y manifiesto validado (M5), con diario encadenado (M1).
- La transacción, con la evaluación, la extracción de artefactos y el juez inyectados (reales en el ejecutor de CR-2).
No consume ninguna reserva: antes de tocar nada exige que su estado sea «aislada».
"""

from __future__ import annotations

import getpass
import hashlib
import json
import platform
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping

EVALS = Path(__file__).resolve().parent
PLUGIN = EVALS.parent
sys.path.insert(0, str(PLUGIN / "scripts"))

from nucleo import esquema  # noqa: E402
from nucleo import juez as contrato_juez  # noqa: E402

ESQUEMA_RESULTADOS = json.loads((EVALS / "esquemas" / "resultado-plugin-eval.schema.json").read_text(encoding="utf-8"))
ESQUEMA_MANIFIESTO = json.loads((EVALS / "esquemas" / "manifiesto-holdout.schema.json").read_text(encoding="utf-8"))

ACEPTA, RECHAZA, INFRAESTRUCTURA, FUERA_DE_CONTRATO = "ACEPTA", "RECHAZA", "INFRAESTRUCTURA", "FUERA_DE_CONTRATO"
TOLERANCIA = 1e-9
CERO = "0" * 64
# E2: nunca llegan a la evaluación, aunque alguien las ponga en la lista de permitidas.
PROHIBIDAS = re.compile(r"^(ITOSTACK_|PYTHON|NODE_OPTIONS$|CLAUDECODE$|CLAUDE_CODE_ENTRYPOINT$)")


class ReservaNoAislada(RuntimeError):
    """La reserva no está declarada aislada: no se toca (ni se consume el intento)."""


class IntentoConsumido(RuntimeError):
    """Esta candidata ya usó su único intento."""


def sha256(datos: str | bytes) -> str:
    return hashlib.sha256(datos.encode("utf-8") if isinstance(datos, str) else datos).hexdigest()


def canonico(objeto) -> bytes:
    return json.dumps(objeto, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=repr).encode("utf-8")


# ---------------------------------------------------------------- contrato de resultados (R1–R8)

@dataclass(frozen=True)
class Solicitud:
    skill: str
    casos: frozenset
    runs: int
    modelo: str
    claude_version: str
    plugin_path: str
    plugin_version: str
    filtro: str = ""  # --case pedido; por omisión «<skill>.*»

    def caso_filtro(self) -> str:
        return self.filtro or f"{self.skill}.*"


@dataclass
class EstadoCaso:
    estado: str
    motivos: list = field(default_factory=list)
    corridas: list = field(default_factory=list)


@dataclass
class Clasificacion:
    estado: str  # ACEPTABLE · RECHAZADA · INFRAESTRUCTURA · FUERA_DE_CONTRATO
    casos: dict
    motivos: list
    reintentable: bool


def puntaje_recalculado(corrida: dict) -> float | None:
    """R7 (provisional hasta observar una corrida exitosa real): peso aprobado / peso total de los calificadores puntuados."""
    puntuados = [g for g in corrida["graders"] if g["scored"]]
    total = sum(g["weight"] for g in puntuados)
    return None if total <= 0 else sum(g["weight"] for g in puntuados if g["passed"]) / total


def _clasificar_caso(caso: dict, solicitud: Solicitud) -> EstadoCaso:
    corridas = caso["arms"]["with"]
    resumen = [{"score": c["score"], "turns": c["turns"], "error": c["error"], "tracePath": c["tracePath"]} for c in corridas]
    contrato, infra = [], []
    if "without" in caso["arms"]:
        contrato.append("R3: hay un brazo sin plugin con ablación «none»")
    if len(corridas) != solicitud.runs:
        contrato.append(f"R6: {len(corridas)} corrida(s); se pidieron {solicitud.runs}")
    calificadores = sorted(g["name"] for g in caso["graders"])
    for i, c in enumerate(corridas):
        lanzaron = [g["name"] for g in c["graders"] if g["explanation"].startswith("grader threw")]
        if c["error"]:
            infra.append(f"corrida {i}: error de infraestructura «{c['error'][:120]}»")
        if c["turns"] == 0:
            infra.append(f"corrida {i}: el agente no llegó a correr (0 turnos)")
        if c["skippedPaidGraders"]:
            infra.append(f"corrida {i}: calificadores omitidos por el tope de costo")
        if lanzaron:
            infra.append(f"corrida {i}: calificadores que lanzaron: {lanzaron}")
        if c["error"] or lanzaron or c["turns"] == 0:
            continue  # con infraestructura fallida no se lee ningún puntaje
        if sorted(g["name"] for g in c["graders"]) != calificadores:
            contrato.append(f"corrida {i}: los calificadores informados no son los del caso")
            continue
        recalculado = puntaje_recalculado(c)
        if recalculado is None or abs(recalculado - c["score"]) > TOLERANCIA:
            contrato.append(f"corrida {i}: R7 puntaje informado {c['score']} ≠ recalculado {recalculado}")
    if contrato:
        return EstadoCaso(FUERA_DE_CONTRATO, contrato, resumen)
    if infra:
        return EstadoCaso(INFRAESTRUCTURA, infra, resumen)
    if all(c["score"] == 1 for c in corridas):
        return EstadoCaso(ACEPTA, [], resumen)
    return EstadoCaso(RECHAZA, [f"puntajes {[c['score'] for c in corridas]}"], resumen)


def clasificar_resultados(datos, solicitud: Solicitud) -> Clasificacion:
    """Clasifica la salida de `claude plugin eval` sin interpretar nada fuera de contrato."""
    errores = esquema.errores(datos, ESQUEMA_RESULTADOS)
    if errores:
        return Clasificacion(FUERA_DE_CONTRATO, {}, [f"R1: {e}" for e in errores[:10]], False)
    motivos = []
    if datos["claudeVersion"] != solicitud.claude_version:
        motivos.append(f"R2: claude {datos['claudeVersion']} ≠ la congelada {solicitud.claude_version}")
    suite = datos["suite"]
    for campo, valor in {"ablation": "none", "modelOverride": solicitud.modelo, "caseFilter": solicitud.caso_filtro(), "threshold": 1, "concurrency": 1}.items():
        if campo not in suite or not esquema._igual(suite[campo], valor):
            motivos.append(f"R3: suite.{campo} = {suite.get(campo)!r}; se pidió {valor!r}")
    if len(suite["plugins"]) != 1 or suite["plugins"][0]["path"] != solicitud.plugin_path or suite["plugins"][0]["version"] != solicitud.plugin_version:
        motivos.append("R3: el plugin evaluado no es la copia materializada de la candidata")
    nombres = [c["name"] for c in datos["cases"]]
    if len(nombres) != len(set(nombres)) or set(nombres) != set(solicitud.casos):
        motivos.append(f"R5: los casos evaluados ({len(nombres)}) no son exactamente los de la reserva ({len(solicitud.casos)})")
    if motivos:
        return Clasificacion(FUERA_DE_CONTRATO, {}, motivos, False)
    casos = {c["name"]: _clasificar_caso(c, solicitud) for c in datos["cases"]}
    generales = [f"R4: corrida parcial ({datos.get('partialReason', 'sin motivo')})"] if datos["partial"] else []
    estados = {e.estado for e in casos.values()}
    if FUERA_DE_CONTRATO in estados:
        estado = FUERA_DE_CONTRATO
    elif INFRAESTRUCTURA in estados or generales:
        estado = INFRAESTRUCTURA
    elif RECHAZA in estados:
        estado = "RECHAZADA"
    else:
        estado = "ACEPTABLE"
    corridas = [c for e in casos.values() for c in e.corridas]
    reintentable = estado == INFRAESTRUCTURA and all(c["turns"] == 0 for c in corridas)
    return Clasificacion(estado, casos, generales + [f"{n}: {m}" for n, e in casos.items() for m in e.motivos], reintentable)


# ---------------------------------------------------------------- entorno e invocación (E1, E2, V1)

def construir_entorno(base: Mapping[str, str], permitidas, fijas: Mapping[str, str]) -> tuple[dict, list]:
    """Entorno desde cero: solo las permitidas presentes en `base`, más las fijas. Devuelve también los NOMBRES (para el
    manifiesto; nunca los valores). Una prohibida en cualquiera de las dos listas es un error de configuración."""
    for nombre in [*permitidas, *fijas]:
        if PROHIBIDAS.match(nombre):
            raise ValueError(f"E2: la variable {nombre} no puede llegar a la evaluación")
    entorno = {n: base[n] for n in permitidas if n in base}
    entorno.update(fijas)
    return entorno, sorted(entorno)


def argv_evaluacion(claude: str, copia: Path, solicitud: Solicitud, almacen: Path, modelo_calificador: str, tope_usd: float, herramientas) -> list:
    """V1: opciones obligatorias; publicación desactivada y resultados dentro del almacén del ejecutor."""
    return [claude, "plugin", "eval", str(copia), "--tag", "holdout", "--case", solicitud.caso_filtro(), "--runs", str(solicitud.runs), "--ablation", "none",
            "--scaffold", "--trust-plugin", "--model", solicitud.modelo, "--judge-model", modelo_calificador, "--no-publish", "--mocks", "record",
            "--concurrency", "1", "--output-dir", str(almacen / "evaluacion"), "--json", str(almacen / "evaluacion" / "resultados.json"),
            "--max-cost-usd", str(tope_usd), "--allow-tools", *sorted(herramientas)]


# ---------------------------------------------------------------- vínculos, diario y manifiesto (M1–M5)

def huella_directorio(raiz: Path) -> str:
    resumen = hashlib.sha256()
    for archivo in sorted(p for p in raiz.rglob("*") if p.is_file()):
        resumen.update(archivo.relative_to(raiz).as_posix().encode())
        resumen.update(archivo.read_bytes())
    return resumen.hexdigest()


def id_opaco(nombre: str) -> str:
    return sha256(nombre)


def huella_evaluador(evaluador: dict, juez: dict) -> str:
    return sha256(canonico({"evaluador": evaluador, "juez": juez}))


class Diario:
    """Diario de solo anexar: cada entrada lleva la huella de la anterior (M1)."""

    def __init__(self, ruta: Path) -> None:
        self.ruta = ruta

    def entradas(self) -> list:
        if not self.ruta.is_file():
            return []
        return [json.loads(linea) for linea in self.ruta.read_text(encoding="utf-8").splitlines() if linea.strip()]

    def anotar(self, evento: str, datos: dict) -> str:
        previas = self.entradas()
        entrada = {"n": len(previas), "evento": evento, "datos": datos, "anterior": previas[-1]["huella"] if previas else CERO}
        entrada["huella"] = sha256(canonico(entrada))
        with open(self.ruta, "a", encoding="utf-8") as archivo:
            archivo.write(json.dumps(entrada, ensure_ascii=False) + "\n")
        return entrada["huella"]


def verificar_diario(ruta: Path) -> tuple:
    """(cabeza, cantidad, errores). Detecta cualquier entrada alterada, quitada, reordenada o insertada."""
    errores, anterior = [], CERO
    try:
        entradas = Diario(ruta).entradas()
    except (OSError, ValueError) as error:
        return None, 0, [f"diario ilegible ({error})"]
    for i, entrada in enumerate(entradas):
        if not isinstance(entrada, dict) or entrada.get("n") != i or entrada.get("anterior") != anterior:
            errores.append(f"entrada {i}: fuera de secuencia o encadenamiento roto")
        cuerpo = {k: v for k, v in entrada.items() if k != "huella"} if isinstance(entrada, dict) else {}
        if not isinstance(entrada, dict) or sha256(canonico(cuerpo)) != entrada.get("huella"):
            errores.append(f"entrada {i}: su huella no corresponde a su contenido")
        anterior = entrada.get("huella") if isinstance(entrada, dict) else None
    return (anterior if entradas else None), len(entradas), errores


def validar_manifiesto(m) -> list:
    """Esquema + coherencia: cada veredicto atado a su caso, su rúbrica autorizada, su evaluador y sus artefactos."""
    errores = esquema.errores(m, ESQUEMA_MANIFIESTO)
    if errores:
        return errores
    evaluador = huella_evaluador(m["evaluador"], m["juez"])
    ids = [c["id"] for c in m["casos"]]
    if len(ids) != len(set(ids)):
        errores.append("casos repetidos")
    estados = []
    for c in m["casos"]:
        if c["sha256_evaluador"] != evaluador:
            errores.append(f"caso {c['id'][:12]}: su veredicto no está atado al evaluador del manifiesto")
        if c["sha256_rubrica"] != m["rubrica"]["sha256"]:
            errores.append(f"caso {c['id'][:12]}: su rúbrica no es la autorizada")
        validas = bool(c["corridas"]) and all(r["error"] == "" and r["turns"] > 0 for r in c["corridas"])
        ultimo = c["juicios"][-1]["estado"] if c["juicios"] else None
        if c["estado"] == ACEPTA and not (validas and all(r["score"] == 1 for r in c["corridas"]) and ultimo == "APRUEBA"):
            errores.append(f"caso {c['id'][:12]}: ACEPTA sin corridas válidas en 1.0 y un juicio que aprueba")
        if c["estado"] == RECHAZA and not (validas and (any(r["score"] < 1 for r in c["corridas"]) or ultimo == "REPRUEBA")):
            errores.append(f"caso {c['id'][:12]}: RECHAZA sin un fallo válido de la candidata")
        if c["estado"] == "BLOCKED" and validas and ultimo in {"APRUEBA", "REPRUEBA"} and all(r["score"] == 1 for r in c["corridas"]):
            errores.append(f"caso {c['id'][:12]}: BLOCKED con evaluación y juicio válidos")
        estados.append(c["estado"])
    decision = m["decision"]["estado"]
    if decision == "ACEPTADA" and set(estados) != {ACEPTA}:
        errores.append("decisión ACEPTADA con casos que no aceptan")
    if decision == "RECHAZADA" and (RECHAZA not in estados or any(not c["corridas"] or any(r["error"] or r["turns"] == 0 for r in c["corridas"]) for c in m["casos"])):
        errores.append("decisión RECHAZADA sin un rechazo válido o con la evaluación afectada por infraestructura")
    if decision in {"PENDIENTE_DE_JUICIO", "INCONCLUSA", "REINTENTABLE"} and "BLOCKED" not in estados:
        errores.append(f"decisión {decision} sin ningún caso bloqueado")
    if decision == "REINTENTABLE" and any(r["turns"] > 0 for c in m["casos"] for r in c["corridas"]):
        errores.append("REINTENTABLE aunque el agente llegó a ver casos de la reserva")
    return errores


def verificar_manifiesto(m, almacen: Path) -> list:
    """M2: el manifiesto, su diario y sus resultados se recalculan y deben coincidir."""
    errores = validar_manifiesto(m)
    cabeza, cantidad, problemas = verificar_diario(almacen / "diario.jsonl")
    errores += problemas
    if isinstance(m, dict) and isinstance(m.get("diario"), dict) and (m["diario"].get("cabeza_sha256") != cabeza or m["diario"].get("entradas") != cantidad):
        errores.append("el manifiesto no apunta a la cabeza del diario")
    resultados = almacen / "evaluacion" / "resultados.json"
    if isinstance(m, dict) and isinstance(m.get("evaluador"), dict) and (not resultados.is_file() or sha256(resultados.read_bytes()) != m["evaluador"].get("sha256_resultados")):
        errores.append("los resultados guardados no son los del manifiesto")
    return errores


# ---------------------------------------------------------------- la transacción

@dataclass
class Orquestacion:
    skill: str
    reserva: Path            # <reserva>/<skill>/<caso>/case.yaml
    estado_reserva: Path     # {"estado": "aislada"} (con CR-2: atestación firmada)
    almacen: Path            # del ejecutor: diario, marcas, resultados y manifiesto
    rubrica: Path            # la autorizada para la skill (por_skill.json de la copia congelada)
    evaluador: dict          # claude_version, modelo, modelo_calificador_llm, argv
    juez: dict               # familia, herramienta, modelo, esfuerzo, version, sha256_opciones
    candidata: dict          # huella, version_plugin, huella_copia, ruta_copia
    huella_reserva: str
    entorno: dict = field(default_factory=dict)   # {"sistema", "usuario_de_servicio", "python", "variables", "path"}
    runs: int = 1
    reintentos_juez: int = 2


def _reserva_aislada(ruta: Path) -> bool:
    try:
        estado = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(estado, dict) and estado.get("estado") == "aislada"


def _juicio(respuesta, artefacto: bytes, esperados: int) -> dict:
    contrato = contrato_juez.errores_contrato("juez", respuesta)
    if contrato:
        return {"sha256_respuesta": sha256(canonico(respuesta)), "estado": "BLOCKED", "puntaje": None}
    calificado = contrato_juez.calificar(respuesta, esperados, artefacto.decode("utf-8", errors="replace"))
    estado = "APRUEBA" if calificado["aprobado"] else ("BLOCKED" if calificado["puntaje"] is None else "REPRUEBA")
    return {"sha256_respuesta": sha256(canonico(respuesta)), "estado": estado, "puntaje": calificado["puntaje"]}


def ejecutar(o: Orquestacion, correr_evaluacion: Callable, artefacto_de: Callable, juzgar: Callable) -> dict:
    """Una sola corrida del holdout de una candidata. Devuelve el manifiesto (ya validado y escrito en el almacén)."""
    if not _reserva_aislada(o.estado_reserva):
        raise ReservaNoAislada("la reserva no está declarada aislada: no se toca ni se consume el intento")
    directorios = sorted(p.parent for p in (o.reserva / o.skill).glob("*/case.yaml"))
    nombres = {f"{o.skill}.{d.name}": d for d in directorios}
    o.almacen.mkdir(parents=True, exist_ok=True)
    try:
        with open(o.almacen / f"{o.candidata['huella'][:16]}.reservado", "x", encoding="utf-8") as marca:
            marca.write(datetime.now(timezone.utc).isoformat() + "\n")
    except FileExistsError:
        raise IntentoConsumido("esta candidata ya usó su único intento") from None
    diario = Diario(o.almacen / "diario.jsonl")
    diario.anotar("reserva", {"candidata": o.candidata["huella"], "reserva": o.huella_reserva, "casos": sorted(id_opaco(n) for n in nombres)})

    solicitud = Solicitud(o.skill, frozenset(nombres), o.runs, o.evaluador["modelo"], o.evaluador["claude_version"],
                          o.candidata["ruta_copia"], o.candidata["version_plugin"])
    datos = correr_evaluacion(solicitud)
    (o.almacen / "evaluacion").mkdir(exist_ok=True)
    (o.almacen / "evaluacion" / "resultados.json").write_bytes(canonico(datos))
    sha_resultados = sha256((o.almacen / "evaluacion" / "resultados.json").read_bytes())
    clasificacion = clasificar_resultados(datos, solicitud)
    diario.anotar("evaluacion", {"sha256_resultados": sha_resultados, "estado": clasificacion.estado, "motivos": clasificacion.motivos[:20]})

    rubrica = o.rubrica.read_bytes()
    esperados = len(contrato_juez.criterios_de_rubrica(rubrica.decode("utf-8")))
    evaluador = dict(o.evaluador, sha256_resultados=sha_resultados)
    huella_eval = huella_evaluador(evaluador, o.juez)
    casos = []
    for nombre, directorio in nombres.items():
        estado_eval = clasificacion.casos.get(nombre)
        corridas = [{"score": r["score"], "turns": r["turns"], "error": r["error"],
                     "sha256_traza": sha256(Path(r["tracePath"]).read_bytes()) if r["tracePath"] and Path(r["tracePath"]).is_file() else sha256(b"")}
                    for r in (estado_eval.corridas if estado_eval else [])]
        juicios, artefacto = [], b""
        if clasificacion.estado in {"ACEPTABLE", "RECHAZADA"} and estado_eval and estado_eval.estado == ACEPTA:
            artefacto = artefacto_de(nombre)
            for _ in range(1 + o.reintentos_juez):
                juicios.append(_juicio(juzgar(artefacto, rubrica), artefacto, esperados))
                if juicios[-1]["estado"] != "BLOCKED":
                    break
        if estado_eval and estado_eval.estado == ACEPTA and juicios and juicios[-1]["estado"] == "APRUEBA":
            estado = ACEPTA
        elif estado_eval and clasificacion.estado in {"ACEPTABLE", "RECHAZADA"} and (estado_eval.estado == RECHAZA or (juicios and juicios[-1]["estado"] == "REPRUEBA")):
            estado = RECHAZA
        else:
            estado = "BLOCKED"
        casos.append({"id": id_opaco(nombre), "sha256_caso": huella_directorio(directorio), "sha256_rubrica": sha256(rubrica), "sha256_evaluador": huella_eval,
                      "corridas": corridas, "sha256_artefacto": sha256(artefacto), "juicios": juicios, "estado": estado})
    estados = [c["estado"] for c in casos]
    if clasificacion.estado == INFRAESTRUCTURA:
        decision = ("REINTENTABLE", "falla de infraestructura sin que el agente viera la reserva") if clasificacion.reintentable \
            else ("INCONCLUSA", "falla de infraestructura: la evaluación no es válida y el intento se consumió")
    elif clasificacion.estado == FUERA_DE_CONTRATO:
        decision = ("INCONCLUSA", "resultados fuera de contrato: " + "; ".join(clasificacion.motivos[:3]))
    elif RECHAZA in estados:
        decision = ("RECHAZADA", "la candidata falló al menos un caso")
    elif "BLOCKED" in estados:
        decision = ("PENDIENTE_DE_JUICIO", "el juez no dio un veredicto válido; se puede reanudar sobre los artefactos sellados")
    else:
        decision = ("ACEPTADA", "holdout 1.0 y el juez de otra familia aprueba cada caso")
    cabeza = diario.anotar("decision", {"estado": decision[0], "casos": {c["id"]: c["estado"] for c in casos}})
    manifiesto = {
        "contrato": "itostack/holdout@1", "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"), "skill": o.skill,
        "candidata": {k: o.candidata[k] for k in ("huella", "version_plugin", "huella_copia")},
        "reserva": {"huella": o.huella_reserva, "estado": "aislada"},
        "entorno": o.entorno or {"sistema": platform.platform(), "usuario_de_servicio": getpass.getuser(), "python": platform.python_version(),
                                 "variables": [], "path": ""},
        "evaluador": evaluador, "juez": o.juez,
        "rubrica": {"archivo": o.rubrica.name, "sha256": sha256(rubrica), "criterios": esperados},
        "casos": casos, "decision": {"estado": decision[0], "motivo": decision[1]},
        "diario": {"cabeza_sha256": cabeza, "entradas": len(diario.entradas())},
    }
    errores = verificar_manifiesto(manifiesto, o.almacen)
    if errores:
        raise AssertionError(f"el orquestador produjo un manifiesto inválido: {errores[:5]}")
    (o.almacen / "manifiesto.json").write_bytes(canonico(manifiesto))
    return manifiesto
