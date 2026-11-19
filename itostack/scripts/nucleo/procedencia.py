"""Contrato estructurado de citas (CR-1): gramática de marcadores, ensamblado desde evidencia y manifiesto de procedencia.

Principio: el agente nunca escribe una cita jurisprudencial; la pide con un marcador. El texto de la cita lo produce el
ensamblador desde la evidencia, y cada tramo que produce queda en un manifiesto. Un entregable es válido solo si su
manifiesto existe, su huella coincide y todo patrón de cita del texto cae dentro de un tramo del ensamblador.

Gramática (cada «[[» del borrador debe abrir uno de estos marcadores; si no, es un error):
  [[CITA:<registro>]]  ·  [[CITA:<registro>|completa|rubro|clave|corta]]   cita verificada (exige evidencia PASS vigente)
  [[CITA_AJENA:<referencia>|<fuente>]]   cita que hizo un tercero; la referencia debe aparecer literal en <fuente>
  [[NO_VERIFICADO:<texto>]]              afirmación propia no verificada; se entrega con advertencia visible

Fuera de un marcador, un borrador no puede contener patrones de cita (registro digital, clave de tesis, «rubro:» o una
marca ⚠/❌ de verificación): el detector de texto libre es una alarma que solo deniega, nunca exime.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .normalizacion import _COMILLAS

CONTRATO = "itostack/citas@1"
FORMAS = ("completa", "rubro", "clave", "corta")
ADVERTENCIA_FIJA = (
    "⚠ Documento ensamblado con apoyo de IA. Verificar citas en fuentes oficiales antes de uso procesal: "
    "sjf.scjn.gob.mx · dof.gob.mx · diputados.gob.mx/LeyesBiblio"
)
SEPARADOR_NOTAS = "\n\n---\n\n"

# Un marcador por tipo, anclado en la posición del «[[». Los argumentos no cruzan líneas ni contienen «]» ni «|».
_MARCADORES = {
    "CITA": re.compile(r"\[\[CITA:([A-Za-z0-9][A-Za-z0-9-]{0,31})(?:\|([a-z]+))?\]\]"),
    "CITA_AJENA": re.compile(r"\[\[CITA_AJENA:([^\]\|\n]+)\|([^\]\|\n]+)\]\]"),
    "NO_VERIFICADO": re.compile(r"\[\[NO_VERIFICADO:([^\]\n]+)\]\]"),
}
# Patrones de la ALARMA: más agresivos que los de extracción de nucleo/citas.py (sin anclas de palabra), porque un falso
# positivo solo produce una denegación de más y un falso negativo dejaría pasar una cita escrita a mano.
_ALARMA = (
    ("registro", re.compile(r"(?i)(?:registro|ius)(?:\s+(?:digital|ius))?\s*(?:n[úu]m(?:ero)?\.?|no\.)?\s*:?\s*(?:FICT-\d{4}|\d{6,7})(?!\d)")),
    ("registro", re.compile(r"(?i)(?:tesis|jurisprudencia)\s+(?:FICT-\d{4}|\d{6,7})(?!\d)")),
    ("clave", re.compile(r"(?:P|\d{1,2}a|[IVXLC]{1,6}|PR|PC|FICT)\.[^\n()\"“”]{0,40}?\((?:[5-9]|1[0-2])a\.\)")),
    ("rubro", re.compile(r"(?i)rubro\s*:")),
    # Marcas de estado de verificación (⚠ NO VERIFICADO…, ❌, ✅): solo las escribe el ensamblador (I-10).
    ("marca", re.compile(r"❌|✅|⚠️?\s*(?:CITA\s+)?NO\s+VERIFICA", re.IGNORECASE)),
)


@dataclass(frozen=True)
class Marcador:
    tipo: str
    argumentos: tuple[str, ...]
    inicio: int
    fin: int


@dataclass(frozen=True)
class Tramo:
    """Una porción del documento final escrita por el ensamblador (posiciones en caracteres del texto final)."""
    inicio: int
    fin: int
    tipo: str  # CITA · CITA_PENDIENTE · CITA_AJENA · NO_VERIFICADO · NOTAS
    registro: str | None = None
    forma: str | None = None
    sha256_evidencia: str | None = None
    fuente: str | None = None
    sha256_fuente: str | None = None


@dataclass
class Ensamblado:
    texto: str = ""
    tramos: list[Tramo] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)
    pendientes: list[str] = field(default_factory=list)


def sha256(datos: str | bytes) -> str:
    return hashlib.sha256(datos.encode("utf-8") if isinstance(datos, str) else datos).hexdigest()


def _linea(texto: str, posicion: int) -> int:
    return texto.count("\n", 0, posicion) + 1


def analizar(texto: str) -> tuple[list[Marcador], list[str]]:
    """Recorre el texto: cada «[[» abre un marcador válido de la gramática o es un error. No hay marcadores anidados."""
    marcadores: list[Marcador] = []
    errores: list[str] = []
    posicion = 0
    while (inicio := texto.find("[[", posicion)) >= 0:
        hallado = None
        for tipo, patron in _MARCADORES.items():
            m = patron.match(texto, inicio)
            if m:
                hallado = (tipo, m)
                break
        if hallado is None:
            errores.append(f"línea {_linea(texto, inicio)}: «{texto[inicio:inicio + 40].splitlines()[0]}» no es un marcador válido "
                           "([[CITA:registro|forma]], [[CITA_AJENA:referencia|fuente]] o [[NO_VERIFICADO:texto]])")
            posicion = inicio + 2
            continue
        tipo, m = hallado
        argumentos = tuple(a.strip() for a in m.groups() if a is not None)
        if tipo == "CITA" and m.group(2) is not None and m.group(2) not in FORMAS:
            errores.append(f"línea {_linea(texto, inicio)}: forma «{m.group(2)}» desconocida (usa {', '.join(FORMAS)})")
        elif any(not a for a in argumentos):
            errores.append(f"línea {_linea(texto, inicio)}: el marcador {tipo} tiene un argumento vacío")
        else:
            marcadores.append(Marcador(tipo, argumentos, inicio, m.end()))
        posicion = m.end()
    return marcadores, errores


def patrones_de_cita(texto: str) -> list[tuple[int, int, str]]:
    """Alarma de texto libre: posiciones de registros, claves, «rubro:» y marcas ⚠/❌ de verificación."""
    return sorted((m.start(), m.end(), tipo) for tipo, patron in _ALARMA for m in patron.finditer(texto))


def _dentro(inicio: int, fin: int, intervalos) -> bool:
    return any(a <= inicio and fin <= b for a, b in intervalos)


def citas_fuera_de_marcadores(texto: str) -> list[str]:
    """Patrones de cita escritos a mano en un borrador (fuera de todo marcador). Cada uno impide ensamblar."""
    marcadores, _ = analizar(texto)
    dentro = [(m.inicio, m.fin) for m in marcadores]
    return [f"línea {_linea(texto, a)}: {tipo} escrito a mano «{texto[a:b]}»: usa un marcador ([[CITA:…]], [[CITA_AJENA:…|…]] o [[NO_VERIFICADO:…]])"
            for a, b, tipo in patrones_de_cita(texto) if not _dentro(a, b, dentro)]


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


def _comparable(texto: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", texto).translate(_COMILLAS)).strip().casefold()


def ensamblar(texto: str, evidencia_de, fuente_de, permitir_pendientes: bool = False) -> Ensamblado:
    """Resuelve los marcadores. `evidencia_de(registro)` → fila vigente del almacén o None; `fuente_de(ruta)` →
    (texto, sha256) de un documento del expediente o None. Sin evidencia vigente, una CITA es un error (no se degrada a
    no verificada), salvo con `permitir_pendientes`, que produce un borrador NO entregable."""
    resultado = Ensamblado()
    marcadores, errores = analizar(texto)
    resultado.errores += errores + citas_fuera_de_marcadores(texto)
    partes: list[str] = []
    tramos: list[Tramo] = []
    notas: list[str] = []
    numeracion: dict[str, int] = {}
    largo = 0
    cursor = 0

    def agregar(fragmento: str, tramo: dict | None = None) -> None:
        nonlocal largo
        if tramo is not None:
            tramos.append(Tramo(inicio=largo, fin=largo + len(fragmento), **tramo))
        partes.append(fragmento)
        largo += len(fragmento)

    for m in marcadores:
        agregar(texto[cursor:m.inicio])
        cursor = m.fin
        if m.tipo == "CITA":
            registro, forma = m.argumentos[0], (m.argumentos[1] if len(m.argumentos) > 1 else "completa")
            fila = evidencia_de(registro)
            if not fila:
                resultado.pendientes.append(registro)
                if not permitir_pendientes:
                    resultado.errores.append(f"[[CITA:{registro}]] sin evidencia PASS vigente: verifica el registro antes de ensamblar")
                agregar(f"⚠ CITA NO VERIFICADA (registro {registro}) — ejecutar /verificar-cita", {"tipo": "CITA_PENDIENTE", "registro": registro})
                continue
            if registro not in numeracion:
                numeracion[registro] = len(numeracion) + 1
                avisos = "".join(f" ⚠ {a}" for a in json.loads(fila["advertencias"]))
                notas.append(f"[^ev{numeracion[registro]}]: Verificado en el portal oficial el {fila['creado_en']} [{fila['modo_fuente']}] · "
                             f"evidencia `{fila['ruta_resultado']}` · SHA-256 {fila['sha256_resultado'][:16]}….{avisos}")
            agregar(formatear(json.loads(fila["datos_oficiales"]), forma, f"[^ev{numeracion[registro]}]"),
                    {"tipo": "CITA", "registro": registro, "forma": forma, "sha256_evidencia": fila["sha256_resultado"]})
        elif m.tipo == "CITA_AJENA":
            referencia, ruta = m.argumentos
            fuente = fuente_de(ruta)
            if fuente is None:
                resultado.errores.append(f"[[CITA_AJENA:…|{ruta}]]: la fuente no existe o está fuera del proyecto")
                continue
            contenido, huella = fuente
            if _comparable(referencia) not in _comparable(contenido):
                resultado.errores.append(f"[[CITA_AJENA:{referencia}|{ruta}]]: la referencia no aparece literal en la fuente")
                continue
            agregar(f"{referencia} (⚠ CITA NO VERIFICADA: así la cita {Path(ruta).name}; no se cotejó con el Semanario Judicial)",
                    {"tipo": "CITA_AJENA", "fuente": ruta, "sha256_fuente": huella})
        else:
            agregar(f"{m.argumentos[0]} (⚠ NO VERIFICADO)", {"tipo": "NO_VERIFICADO"})
    agregar(texto[cursor:].rstrip())
    agregar(SEPARADOR_NOTAS + ("\n".join(notas) + "\n\n" if notas else "") + ADVERTENCIA_FIJA + "\n", {"tipo": "NOTAS"})
    if resultado.errores:
        return Ensamblado(errores=resultado.errores, pendientes=resultado.pendientes)
    resultado.texto, resultado.tramos = "".join(partes), tramos
    return resultado


def manifiesto(documento: str, borrador: str, ensamblado: Ensamblado, version_plugin: str) -> dict:
    """Procedencia del entregable: huella del texto final y de cada tramo que escribió el ensamblador."""
    return {
        "contrato": CONTRATO,
        "version_plugin": version_plugin,
        "entregable": not ensamblado.pendientes,
        "sha256_documento": sha256(documento),
        "sha256_borrador": sha256(borrador),
        "tramos": [dict(asdict(t), sha256_texto=sha256(documento[t.inicio:t.fin])) for t in ensamblado.tramos],
    }


def verificar_entrega(documento: bytes, datos_manifiesto) -> list[str]:
    """Razones por las que un documento NO es entregable; vacío = entregable. No confía en nada que no pueda recalcular."""
    if not isinstance(datos_manifiesto, dict) or datos_manifiesto.get("contrato") != CONTRATO:
        return ["sin manifiesto de procedencia válido (contrato itostack/citas@1)"]
    errores = []
    if sha256(documento) != datos_manifiesto.get("sha256_documento"):
        return ["el documento cambió después de ensamblarse (su huella no coincide con el manifiesto)"]
    if datos_manifiesto.get("entregable") is not True:
        errores.append("el manifiesto declara citas pendientes de verificar: es un borrador, no un entregable")
    try:
        texto = documento.decode("utf-8")
    except UnicodeDecodeError:
        return errores + ["el documento no es UTF-8"]
    tramos = datos_manifiesto.get("tramos")
    intervalos = []
    for tramo in tramos if isinstance(tramos, list) else []:
        inicio, fin = (tramo.get("inicio"), tramo.get("fin")) if isinstance(tramo, dict) else (None, None)
        if not (type(inicio) is int and type(fin) is int and 0 <= inicio <= fin <= len(texto)) or sha256(texto[inicio:fin]) != tramo.get("sha256_texto"):
            errores.append("un tramo del manifiesto no corresponde al documento")
            continue
        intervalos.append((inicio, fin))
    if "[[" in texto:
        errores.append(f"línea {_linea(texto, texto.find('[['))}: quedó un marcador sin resolver")
    for a, b, tipo in patrones_de_cita(texto):
        if not _dentro(a, b, intervalos):
            errores.append(f"línea {_linea(texto, a)}: {tipo} «{texto[a:b]}» fuera de los tramos del ensamblador (escrito a mano)")
    return errores
