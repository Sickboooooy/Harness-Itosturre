"""Detección de citas jurisprudenciales en texto libre.

Detecta registros digitales, claves de tesis y marcadores [[CITA:registro]]. No intenta
"entender" la cita: solo localiza lo que debe pasar por verificación forense.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

RE_REGISTRO = re.compile(
    r"(?i)\b(?:registro(?:\s+(?:digital|ius))?|ius)\s*(?:n[úu]m(?:ero)?\.?|no\.)?\s*:?\s*(FICT-\d{4}|\d{6,7})\b"
)
RE_CLAVE = re.compile(
    r"(?<![\w/])((?:P|\d{1,2}a|[IVXLC]{1,6}|PR|PC|FICT)\.[^\n()\"“”]{0,40}?\((?:[5-9]|1[0-2])a\.\))"
)
RE_MARCADOR = re.compile(r"\[\[CITA:([^\]|\s]+)(?:\|([a-z]+))?\]\]")
RE_MARCA_NO_VERIFICADA = re.compile(r"⚠|❌|NO VERIFICAD|NO VERIFICABLE|BLOQUEAD|INEXISTENTE", re.IGNORECASE)
RE_RUBRO_ENTRECOMILLADO = re.compile(r"(?i)rubro\s*:?\s*[\"“«]([^\"”»]{10,800})[\"”»]")
RE_RUBRO_MAYUSCULAS = re.compile(r"([A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ0-9 ,;:()\-\"“”'’]{30,800}[.])")


@dataclass
class Cita:
    tipo: str  # registro | clave | marcador
    valor: str
    linea: int
    columna: int
    texto_linea: str
    marcada_no_verificada: bool
    forma: str | None = None

    def como_dict(self) -> dict:
        return {
            "tipo": self.tipo, "valor": self.valor, "linea": self.linea, "columna": self.columna,
            "marcada_no_verificada": self.marcada_no_verificada, "forma": self.forma,
        }


def extraer(texto: str) -> list[Cita]:
    encontradas: list[Cita] = []
    for numero, linea in enumerate(texto.splitlines(), start=1):
        marcada = bool(RE_MARCA_NO_VERIFICADA.search(linea))
        for m in RE_MARCADOR.finditer(linea):
            encontradas.append(Cita("marcador", m.group(1), numero, m.start() + 1, linea, marcada, m.group(2)))
        sin_marcadores = RE_MARCADOR.sub(lambda m: " " * len(m.group(0)), linea)
        for m in RE_REGISTRO.finditer(sin_marcadores):
            encontradas.append(Cita("registro", m.group(1).upper(), numero, m.start(1) + 1, linea, marcada))
        for m in RE_CLAVE.finditer(sin_marcadores):
            encontradas.append(Cita("clave", m.group(1).strip(), numero, m.start(1) + 1, linea, marcada))
    return encontradas


@dataclass
class Referencia:
    """Agrupa lo que parece una misma cita dentro de un párrafo: registro, clave y rubro candidato."""

    id: str
    parrafo: int
    registro: str | None = None
    clave: str | None = None
    rubro: str | None = None
    marcada_no_verificada: bool = False
    extracto: str = ""
    lineas: list[int] = field(default_factory=list)

    def como_dict(self) -> dict:
        return {
            "id": self.id, "parrafo": self.parrafo, "registro": self.registro, "clave": self.clave,
            "rubro": self.rubro, "modo": "cotejo", "marcada_no_verificada": self.marcada_no_verificada,
            "extracto": self.extracto, "lineas": self.lineas,
        }


def _parrafos(texto: str) -> list[tuple[int, str]]:
    bloques: list[tuple[int, str]] = []
    inicio, actual = 1, []
    for numero, linea in enumerate(texto.splitlines(), start=1):
        if linea.strip():
            if not actual:
                inicio = numero
            actual.append(linea)
        elif actual:
            bloques.append((inicio, "\n".join(actual)))
            actual = []
    if actual:
        bloques.append((inicio, "\n".join(actual)))
    return bloques


def agrupar_referencias(texto: str) -> list[Referencia]:
    referencias: list[Referencia] = []
    for indice, (linea_inicio, parrafo) in enumerate(_parrafos(texto), start=1):
        citas = extraer(parrafo)
        registros = [c for c in citas if c.tipo == "registro"]
        claves = [c for c in citas if c.tipo == "clave"]
        if not registros and not claves:
            continue
        rubro = None
        entrecomillado = RE_RUBRO_ENTRECOMILLADO.search(parrafo)
        if entrecomillado:
            rubro = re.sub(r"\s+", " ", entrecomillado.group(1)).strip()
        else:
            mayusculas = [m.group(1) for m in RE_RUBRO_MAYUSCULAS.finditer(parrafo) if len(m.group(1).split()) >= 6]
            if mayusculas:
                rubro = re.sub(r"\s+", " ", max(mayusculas, key=len)).strip()
        total = max(len(registros), len(claves))
        lineas_parrafo = parrafo.splitlines()
        for posicion in range(total):
            registro = registros[posicion].valor if posicion < len(registros) else None
            clave = claves[posicion].valor if posicion < len(claves) else None
            ancla = registros[posicion] if posicion < len(registros) else claves[posicion]
            lineas = sorted({c.linea + linea_inicio - 1 for c in citas})
            rubro_propio = rubro if total == 1 else None
            if total > 1:
                en_linea = RE_RUBRO_ENTRECOMILLADO.search(lineas_parrafo[ancla.linea - 1])
                rubro_propio = re.sub(r"\s+", " ", en_linea.group(1)).strip() if en_linea else None
            referencias.append(
                Referencia(
                    id=f"c{len(referencias) + 1:02d}",
                    parrafo=indice,
                    registro=registro,
                    clave=clave,
                    rubro=rubro_propio,
                    marcada_no_verificada=any(c.marcada_no_verificada for c in citas),
                    extracto=re.sub(r"\s+", " ", parrafo)[:300],
                    lineas=lineas,
                )
            )
    return referencias
