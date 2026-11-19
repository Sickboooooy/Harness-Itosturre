"""Contrato común de los revisores de otra familia de modelos (Codex y Ollama): instrucciones, esquema y puntaje.

El modelo solo califica cada criterio de la rúbrica (`si`, `no` o `no_aplicable`, con evidencia textual). El
puntaje lo calcula este módulo: así el juez no puede inventar un 10 que la rúbrica no define (D-17), y un
criterio que el artefacto no ofrece ocasión de ejercer no se cuenta como cumplido ni como fallado. La calificación
exige cobertura exacta de la rúbrica: un veredicto que omite criterios no aprueba.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from . import config as cfg

# Marcas de la familia Claude: el juez debe ver el trabajo con otros ojos que el modelo que lo produjo.
FAMILIA_CLAUDE = re.compile(r"claude|anthropic|\bopus\b|\bsonnet\b|\bhaiku\b|\bfable\b", re.IGNORECASE)

INSTRUCCIONES = {
    "adversarial": (
        "Eres un revisor adversarial de un despacho jurídico mexicano. Busca errores, no virtudes. Señala: citas sin fuente "
        "verificable, afirmaciones sin sustento, riesgos procesales (plazos, competencia, improcedencia), contradicciones, "
        "atajos técnicos y, si es código, defectos que un caso concreto haría fallar. Cada hallazgo debe poder comprobarse "
        "en el material recibido; no inventes ubicaciones. Todo lo que necesitas está en este mensaje: no busques archivos.\n"
        "Responde SOLO JSON: {\"hallazgos\": [{\"gravedad\": \"alta|media|baja\", \"ubicacion\": \"...\", "
        "\"problema\": \"...\", \"sugerencia\": \"...\"}], \"veredicto\": \"aprobar|corregir|rechazar\"}"
    ),
    "juez": (
        "Eres un juez de evaluación. Califica el artefacto SOLO contra la rúbrica congelada que se te da, criterio por "
        "criterio y en su orden, uno por cada criterio numerado, con su número en \"numero\"; no premies estilo ni "
        "esfuerzo. Para cada criterio responde:\n"
        "- \"si\": el artefacto lo cumple; la evidencia copia entre «» un fragmento LITERAL del artefacto que corresponde a "
        "ESE criterio (el programa comprueba que el fragmento exista).\n"
        "- \"no\": no lo cumple o no encuentras evidencia textual de que lo cumpla.\n"
        "- \"no_aplicable\": el artefacto no ofrece ocasión de ejercerlo (p. ej. pide trasladar advertencias y ninguna "
        "cita las dispara); explica en la evidencia por qué no hay ocasión.\n"
        "Lista en fallos_criticos los que la rúbrica define como críticos y ocurren. No calcules puntaje: lo calcula el "
        "programa. Todo lo que necesitas está en este mensaje: no busques archivos.\n"
        "Responde SOLO JSON: {\"criterios\": [{\"numero\": 1, \"criterio\": \"...\", \"cumple\": \"si|no|no_aplicable\", "
        "\"evidencia\": \"...\"}], \"fallos_criticos\": [\"...\"], \"observaciones\": \"...\"}"
    ),
}

_TEXTO = {"type": "string"}

ESQUEMAS = {
    "adversarial": {
        "type": "object",
        "additionalProperties": False,
        "required": ["hallazgos", "veredicto"],
        "properties": {
            "hallazgos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["gravedad", "ubicacion", "problema", "sugerencia"],
                    "properties": {
                        "gravedad": {"type": "string", "enum": ["alta", "media", "baja"]},
                        "ubicacion": _TEXTO,
                        "problema": _TEXTO,
                        "sugerencia": _TEXTO,
                    },
                },
            },
            "veredicto": {"type": "string", "enum": ["aprobar", "corregir", "rechazar"]},
        },
    },
    "juez": {
        "type": "object",
        "additionalProperties": False,
        "required": ["criterios", "fallos_criticos", "observaciones"],
        "properties": {
            "criterios": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["numero", "criterio", "cumple", "evidencia"],
                    "properties": {
                        "numero": {"type": "integer"},
                        "criterio": _TEXTO,
                        "cumple": {"type": "string", "enum": ["si", "no", "no_aplicable"]},
                        "evidencia": _TEXTO,
                    },
                },
            },
            "fallos_criticos": {"type": "array", "items": _TEXTO},
            "observaciones": _TEXTO,
        },
    },
}

# Lo que el programa agrega a la respuesta del modelo al guardar un veredicto. Todo lo demás debe cumplir ESQUEMAS.
CAMPOS_DEL_PROGRAMA = frozenset({"juez", "material", "aplicables", "cumplidos", "no_aplicables", "puntaje", "aprobado", "cobertura", "contrato"})
CAMPOS_DEL_PROGRAMA_CRITERIO = frozenset({"evidencia_verificada", "motivo"})

# Campos del programa que la compuerta usa para decidir: deben existir y tener su tipo.
_ESQUEMA_GUARDADO = {
    "type": "object",
    "required": ["juez", "material"],
    "properties": {
        "juez": {"type": "object", "required": ["familia", "herramienta", "modelo", "rol"],
                 "properties": {"familia": _TEXTO, "herramienta": _TEXTO, "modelo": _TEXTO, "rol": _TEXTO}},
        "material": {"type": "object", "required": ["sha256_artefactos", "rubrica"], "properties": {
            "sha256_artefactos": {"type": "array", "items": _TEXTO},
            "rubrica": {"type": "object", "required": ["sha256", "criterios"], "properties": {"sha256": _TEXTO, "criterios": {"type": "integer"}}},
            "caso": _TEXTO,
        }},
    },
}

_CRITERIO = re.compile(r"^\s*(\d+)\.\s+\S")
_FIN_CRITERIOS = re.compile(r"^\s*fallos?\s+cr[ií]ticos?", re.IGNORECASE)


class MaterialExcedido(ValueError):
    """El material no cabe en el mensaje: recortarlo dejaría parte sin revisar y el veredicto no lo diría."""


def _errores_esquema(valor, esquema: dict, ruta: str) -> list[str]:
    """Valida contra el subconjunto de JSON Schema de ESQUEMAS, el mismo que recibe Codex: una sola fuente del contrato."""
    tipo = esquema.get("type")
    if tipo == "object":
        if not isinstance(valor, dict):
            return [f"{ruta}: debe ser un objeto"]
        propiedades = esquema.get("properties", {})
        errores = [f"{ruta}.{campo}: falta" for campo in esquema.get("required", []) if campo not in valor]
        if esquema.get("additionalProperties") is False:
            errores += [f"{ruta}.{campo}: fuera del esquema" for campo in valor if campo not in propiedades]
        for campo, subesquema in propiedades.items():
            if campo in valor:
                errores += _errores_esquema(valor[campo], subesquema, f"{ruta}.{campo}")
        return errores
    if tipo == "array":
        if not isinstance(valor, list):
            return [f"{ruta}: debe ser una lista"]
        return [error for i, elemento in enumerate(valor) for error in _errores_esquema(elemento, esquema.get("items", {}), f"{ruta}[{i}]")]
    if tipo == "string" and not isinstance(valor, str):
        return [f"{ruta}: debe ser texto"]
    # Entero JSON de verdad: ni booleano (true == 1) ni decimal.
    if tipo == "integer" and (not isinstance(valor, int) or isinstance(valor, bool)):
        return [f"{ruta}: debe ser un entero"]
    if "enum" in esquema and valor not in esquema["enum"]:
        return [f"{ruta}: {valor!r} no es uno de {esquema['enum']}"]
    return []


def respuesta_del_modelo(datos: dict) -> dict:
    """Un veredicto sin lo que agregó el programa: lo que queda es lo que respondió el modelo."""
    respuesta = {k: v for k, v in datos.items() if k not in CAMPOS_DEL_PROGRAMA}
    if isinstance(respuesta.get("criterios"), list):
        respuesta["criterios"] = [{k: v for k, v in c.items() if k not in CAMPOS_DEL_PROGRAMA_CRITERIO} if isinstance(c, dict) else c
                                  for c in respuesta["criterios"]]
    return respuesta


def errores_contrato(rol: str, datos, guardado: bool = False) -> list[str]:
    """Todo lo que impide calificar una respuesta; vacío = cumple el contrato. Fuera de contrato es BLOCKED.

    - Respuesta del modelo (`guardado=False`, los revisores): el esquema exacto que recibe Codex, sin campos de más.
    - Veredicto guardado (`guardado=True`, la compuerta): la parte del modelo con ese mismo esquema, más los campos
      del programa con su tipo (identidad del juez y material calificado).
    No hay valores por omisión que completen una respuesta: un campo faltante no se supone vacío ni favorable.
    """
    if not isinstance(datos, dict):
        return ["la respuesta no es un objeto JSON"]
    errores: list[str] = []
    if guardado:
        errores += _errores_esquema(datos, _ESQUEMA_GUARDADO, "veredicto")
        for i, criterio in enumerate(datos.get("criterios") if isinstance(datos.get("criterios"), list) else []):
            if isinstance(criterio, dict) and "evidencia_verificada" in criterio and not isinstance(criterio["evidencia_verificada"], bool):
                errores.append(f"respuesta.criterios[{i}].evidencia_verificada: debe ser booleano")
        datos = respuesta_del_modelo(datos)
    return errores + _errores_esquema(datos, ESQUEMAS[rol], "respuesta")


def es_familia_claude(modelo: str) -> bool:
    return bool(FAMILIA_CLAUDE.search(modelo or ""))


def criterios_de_rubrica(texto: str) -> list[str]:
    """Criterios numerados de una rúbrica congelada (hasta la línea de fallos críticos)."""
    criterios = []
    for linea in texto.splitlines():
        if _FIN_CRITERIOS.match(linea):
            break
        if _CRITERIO.match(linea):
            criterios.append(linea.strip())
    return criterios


def sha256(texto: str | bytes) -> str:
    return hashlib.sha256(texto.encode("utf-8") if isinstance(texto, str) else texto).hexdigest()


_FRAGMENTO = re.compile(r"«([^»]+)»|“([^”]+)”|\"([^\"]+)\"")
_RELLENO_MD = re.compile(r"[`*_]+")


def _comparable(texto: str) -> str:
    from .normalizacion import _COMILLAS

    limpio = unicodedata.normalize("NFC", str(texto)).translate(_COMILLAS)
    return re.sub(r"\s+", " ", _RELLENO_MD.sub("", limpio)).strip().casefold()


def evidencia_en_artefacto(evidencia: str, artefacto: str) -> bool:
    """La evidencia de un «si» debe traer al menos un fragmento entre comillas que exista en el artefacto.

    Un fragmento con elisión («inicio … fin») vale si todos sus tramos aparecen en ese orden. Sin fragmento
    comprobable, el juez pudo haber inventado la cita.
    """
    texto = _comparable(artefacto)
    for grupos in _FRAGMENTO.findall(evidencia or ""):
        fragmento = next((g for g in grupos if g), "")
        tramos = [t for t in (_comparable(t) for t in re.split(r"…|\.\.\.", fragmento)) if t]
        if not tramos or sum(len(t) for t in tramos) < 4:
            continue
        # Todos los tramos, sin descartar ninguno, y en el orden en que la evidencia los declara.
        desde, completo = 0, True
        for tramo in tramos:
            posicion = texto.find(tramo, desde)
            if posicion < 0:
                completo = False
                break
            desde = posicion + len(tramo)
        if completo:
            return True
    return False


def _bloqueado(resultado, errores: list[str]) -> dict:
    base = {k: v for k, v in resultado.items() if k not in {"puntaje", "aprobado"}} if isinstance(resultado, dict) else {}
    base.update(criterios=[], fallos_criticos=[], aplicables=0, cumplidos=0, no_aplicables=0, puntaje=None, aprobado=False,
                contrato=errores, cobertura="BLOCKED: respuesta fuera del contrato del juez")
    return base


def calificar(resultado, esperados: int, artefacto: str | None = None) -> dict:
    """Añade puntaje, conteos y `aprobado` calculados a partir de los criterios. Nunca confía en un puntaje del modelo.

    - Respuesta fuera de contrato (no es objeto, falta un campo, tipo o valor fuera del esquema) → BLOCKED: sin puntaje
      y sin aprobar. Ningún valor por omisión la completa: ni `fallos_criticos` vacío, ni un booleano leído como «si»,
      ni una evidencia verificada que nadie verificó, ni una cobertura sin rúbrica.
    - Un «si» cuenta solo con evidencia literal verificada. Con `artefacto` se comprueba aquí y se anota
      `evidencia_verificada`; sin él (la compuerta), el criterio debe traer `evidencia_verificada: true`.
    - Los criterios deben llevar los números 1..`esperados`, cada uno una sola vez: repetir un criterio u omitir otro
      deja el veredicto sin puntaje (BLOCKED).
    """
    if not isinstance(esperados, int) or isinstance(esperados, bool) or esperados < 1:
        return _bloqueado(resultado, ["sin rúbrica con criterios numerados no hay cobertura que exigir"])
    errores = errores_contrato("juez", respuesta_del_modelo(resultado)) if isinstance(resultado, dict) else ["la respuesta no es un objeto JSON"]
    if errores:
        return _bloqueado(resultado, errores)
    criterios = []
    for criterio in resultado["criterios"]:
        criterio = dict(criterio)
        if criterio["cumple"] == "si":
            if artefacto is not None:
                criterio["evidencia_verificada"] = evidencia_en_artefacto(criterio["evidencia"], artefacto)
            if not criterio["evidencia"].strip() or criterio.get("evidencia_verificada") is not True:
                criterio["cumple"] = "no"
                criterio["motivo"] = "sin evidencia literal comprobable en el artefacto"
        criterios.append(criterio)
    fallos = [f for f in resultado["fallos_criticos"] if f.strip()]
    aplicables = [c for c in criterios if c["cumple"] != "no_aplicable"]
    cumplidos = sum(1 for c in aplicables if c["cumple"] == "si")
    cobertura_ok = sorted(c["numero"] for c in criterios) == list(range(1, esperados + 1))
    if fallos:
        puntaje = 0.0
    elif aplicables and cobertura_ok:
        puntaje = round(10 * cumplidos / len(aplicables), 2)
    else:
        puntaje = None
    calificado = {k: v for k, v in resultado.items() if k != "puntaje"}
    calificado.update(
        criterios=criterios,
        fallos_criticos=fallos,
        aplicables=len(aplicables),
        cumplidos=cumplidos,
        no_aplicables=len(criterios) - len(aplicables),
        puntaje=puntaje,
        # Por conteos, no por el puntaje redondeado: 2499 de 2500 da 9.996 → «10», y no debe aprobar.
        aprobado=bool(aplicables) and cumplidos == len(aplicables) and not fallos and cobertura_ok,
        cobertura=f"{len(criterios)} criterio(s) para {esperados} de la rúbrica" + ("" if cobertura_ok else " (números 1..N incompletos o repetidos)"),
    )
    return calificado


def codigo_salida(rol: str, resultado: dict) -> int:
    """0 aprobado · 1 no aprobado · 2 nada que calificar o cobertura incompleta: BLOCKED, no PASS."""
    if rol == "juez":
        if resultado.get("puntaje") is None:
            return 2
        return 0 if resultado.get("aprobado") else 1
    return 0 if resultado.get("veredicto") == "aprobar" else 1


def armar_prompt(rol: str, artefactos: str, rubrica: str | None, limite: int) -> str:
    if len(artefactos) > limite:
        raise MaterialExcedido(f"el material tiene {len(artefactos)} caracteres y el límite es {limite}: divide la revisión")
    seccion_rubrica = f"\n\nRÚBRICA CONGELADA:\n{rubrica}" if rubrica else ""
    return f"{INSTRUCCIONES[rol]}{seccion_rubrica}\n\nARTEFACTO:\n{artefactos}"


def instantanea(archivos: list[Path], entrada: str) -> tuple[str, list[str]]:
    """Lee cada artefacto UNA vez: el mensaje y sus huellas salen de la misma lectura, así que un archivo corregido
    mientras corre el juez no queda asociado a un veredicto que no lo revisó. Los artefactos se rotulan con un número,
    no con su ruta: la ruta puede delatar un examen (holdout-*, evals/)."""
    if not archivos:
        return entrada, [sha256(entrada)]
    datos = [a.read_bytes() for a in archivos]
    texto = "\n\n".join(f"=== documento {i} ===\n{d.decode('utf-8')}" for i, d in enumerate(datos, 1))
    return texto, [sha256(d) for d in datos]


def material(huellas: list[str], rubrica: bytes | None, caso: str | None = None) -> dict:
    """Huellas de lo calificado: atan el veredicto a sus artefactos y a su rúbrica (bytes, igual que la compuerta)."""
    datos: dict = {"sha256_artefactos": sorted(huellas)}
    if rubrica is not None:
        datos["rubrica"] = {"sha256": sha256(rubrica), "criterios": len(criterios_de_rubrica(rubrica.decode("utf-8")))}
    if caso:
        datos["caso"] = caso
    return datos


def anotar_bitacora(proyecto: Path, resultado: dict) -> None:
    """Toda corrida del juez queda registrada: la compuerta ve si un artefacto ya fue reprobado por ese mismo juez."""
    datos_juez = resultado.get("juez") or {}
    if datos_juez.get("rol") != "juez":
        return
    carpeta = proyecto / cfg.DIR_ITOSTACK / "bitacora"
    if not carpeta.parent.is_dir():
        return
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / "juez.tsv"
    nueva = not ruta.exists()
    materia = resultado.get("material") or {}
    with open(ruta, "a", encoding="utf-8") as archivo:
        if nueva:
            archivo.write("fecha\tfamilia\therramienta\tmodelo\tesfuerzo\tversion\tcaso\tsha256_artefactos\tsha256_rubrica\tpuntaje\taprobado\n")
        archivo.write("\t".join([
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            str(datos_juez.get("familia")),
            str(datos_juez.get("herramienta")),
            str(datos_juez.get("modelo")),
            str(datos_juez.get("esfuerzo")),
            str(datos_juez.get("version")),
            str(materia.get("caso") or ""),
            ",".join(sorted(materia.get("sha256_artefactos") or [])),
            str((materia.get("rubrica") or {}).get("sha256", "")),
            str(resultado.get("puntaje")),
            "si" if resultado.get("aprobado") else "no",
        ]) + "\n")


def leer_bitacora(proyecto: Path) -> list[dict]:
    ruta = proyecto / cfg.DIR_ITOSTACK / "bitacora" / "juez.tsv"
    if not ruta.is_file():
        return []
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    campos = lineas[0].split("\t") if lineas else []
    return [dict(zip(campos, l.split("\t"))) for l in lineas[1:] if l.strip()]


def cargar_modelos(proyecto: Path | None = None) -> dict:
    """La plantilla del plugin con el `modelos.json` del proyecto encima (un proyecto antiguo hereda las claves nuevas)."""
    plantilla = json.loads((cfg.RAIZ_PLUGIN / "plantillas" / "modelos.json").read_text(encoding="utf-8"))
    ruta = (proyecto or cfg.raiz_proyecto()) / cfg.DIR_ITOSTACK / "modelos.json"
    if ruta.is_file():
        return cfg._mezclar(plantilla, json.loads(ruta.read_text(encoding="utf-8")))
    return plantilla
