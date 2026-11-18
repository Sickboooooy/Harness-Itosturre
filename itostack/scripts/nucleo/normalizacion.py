"""Normalización y cotejo estricto de datos de tesis.

Regla VVCA: un solo rubro discrepante bloquea el veredicto. Solo se toleran variaciones
tipográficas (espacios, mayúsculas, comillas, guiones, punto final y, si se configura, acentos).
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date

_COMILLAS = str.maketrans({"“": '"', "”": '"', "«": '"', "»": '"', "„": '"', "‘": "'", "’": "'", "–": "-", "—": "-", "‑": "-"})

ORDINALES_EPOCA = {
    "primera": 1, "segunda": 2, "tercera": 3, "cuarta": 4, "quinta": 5, "sexta": 6,
    "septima": 7, "octava": 8, "novena": 9, "decima": 10, "undecima": 11, "duodecima": 12,
}

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto)
    return unicodedata.normalize("NFC", "".join(c for c in descompuesto if unicodedata.category(c) != "Mn"))


def normalizar_texto(texto: str | None, ignorar_acentos: bool = True) -> str:
    if not texto:
        return ""
    limpio = unicodedata.normalize("NFC", str(texto)).translate(_COMILLAS)
    limpio = re.sub(r"\s+", " ", limpio).strip().strip("\"'").strip()
    limpio = re.sub(r"[\s.;:,]+$", "", limpio).strip("\"'").strip()
    if ignorar_acentos:
        limpio = sin_acentos(limpio)
    return limpio.casefold()


def normalizar_clave(clave: str | None) -> str:
    if not clave:
        return ""
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", str(clave)).translate(_COMILLAS)).upper()


def normalizar_registro(registro: str | int | None) -> str:
    if registro is None:
        return ""
    valor = str(registro).strip().upper()
    if re.fullmatch(r"\d+", valor):
        return str(int(valor))
    return valor


def epoca_a_numero(texto: str | int | None) -> int | None:
    if texto is None or texto == "":
        return None
    if isinstance(texto, int):
        return texto
    limpio = sin_acentos(str(texto)).lower()
    for palabra, numero in sorted(ORDINALES_EPOCA.items(), key=lambda par: -len(par[0])):
        if re.search(rf"\b{palabra}\b", limpio):
            return numero
    encontrado = re.search(r"\b(\d{1,2})\s*a?\.?\b", limpio)
    if encontrado and 1 <= int(encontrado.group(1)) <= 12:
        return int(encontrado.group(1))
    return None


def normalizar_tipo(texto: str | None) -> str:
    limpio = sin_acentos(str(texto or "")).lower()
    if "jurisprud" in limpio or limpio.strip() in {"j", "jur"}:
        return "jurisprudencia"
    if "aislada" in limpio or limpio.strip() in {"a", "ta"}:
        return "aislada"
    return limpio.strip()


def parsear_fecha(texto: str | None) -> date | None:
    if not texto:
        return None
    valor = sin_acentos(str(texto)).lower().strip()
    iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", valor)
    if iso:
        return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
    dmy = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", valor)
    if dmy:
        return date(int(dmy.group(3)), int(dmy.group(2)), int(dmy.group(1)))
    larga = re.search(r"\b(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})\b", valor)
    if larga and larga.group(2) in MESES:
        return date(int(larga.group(3)), MESES[larga.group(2)], int(larga.group(1)))
    return None


@dataclass
class Cotejo:
    campo: str
    citado: str | None
    oficial: str | None
    estado: str  # coincide | tipografica | discrepante | no_confirmado
    detalle: str = ""
    critico: bool = field(default=False)

    def como_dict(self) -> dict:
        return {
            "campo": self.campo, "citado": self.citado, "oficial": self.oficial,
            "estado": self.estado, "detalle": self.detalle, "critico": self.critico,
        }


def _diferencia_palabras(a: str, b: str) -> str:
    palabras_a, palabras_b = a.split(), b.split()
    for operacion, i1, i2, j1, j2 in difflib.SequenceMatcher(a=palabras_a, b=palabras_b).get_opcodes():
        if operacion != "equal":
            citado = " ".join(palabras_a[i1:i2]) or "∅"
            oficial = " ".join(palabras_b[j1:j2]) or "∅"
            return f"primera diferencia — citado: «{citado}» / oficial: «{oficial}»"
    return ""


def cotejar_rubro(citado: str, oficial: str | None, ignorar_acentos: bool = True) -> Cotejo:
    if not oficial:
        return Cotejo("rubro", citado, oficial, "no_confirmado", "el portal no devolvió rubro", critico=True)
    if citado == oficial:
        return Cotejo("rubro", citado, oficial, "coincide", "idéntico", critico=True)
    a = normalizar_texto(citado, ignorar_acentos)
    b = normalizar_texto(oficial, ignorar_acentos)
    if a == b:
        return Cotejo("rubro", citado, oficial, "tipografica", "coincide salvo variaciones tipográficas", critico=True)
    return Cotejo("rubro", citado, oficial, "discrepante", _diferencia_palabras(a, b), critico=True)


def cotejar_clave(citado: str, oficial: str | None) -> Cotejo:
    if not oficial:
        return Cotejo("clave", citado, oficial, "no_confirmado", "el portal no devolvió clave", critico=True)
    if normalizar_clave(citado) == normalizar_clave(oficial):
        estado = "coincide" if citado.strip() == str(oficial).strip() else "tipografica"
        return Cotejo("clave", citado, oficial, estado, "", critico=True)
    return Cotejo("clave", citado, oficial, "discrepante", "la clave citada no corresponde al registro", critico=True)


def cotejar_epoca(citado: str, oficial: str | None) -> Cotejo:
    n_citado, n_oficial = epoca_a_numero(citado), epoca_a_numero(oficial)
    if n_oficial is None:
        return Cotejo("epoca", citado, oficial, "no_confirmado", "época no disponible en el portal")
    if n_citado is None:
        return Cotejo("epoca", citado, oficial, "discrepante", "la época citada no es interpretable")
    if n_citado == n_oficial:
        return Cotejo("epoca", citado, oficial, "coincide")
    return Cotejo("epoca", citado, oficial, "discrepante", f"época {n_citado} citada vs {n_oficial} oficial")


def cotejar_instancia(citado: str, oficial: str | None) -> Cotejo:
    if not oficial:
        return Cotejo("instancia", citado, oficial, "no_confirmado", "instancia no disponible en el portal")
    a, b = normalizar_texto(citado), normalizar_texto(oficial)
    if a and (a in b or b in a):
        return Cotejo("instancia", citado, oficial, "coincide" if a == b else "tipografica")
    return Cotejo("instancia", citado, oficial, "discrepante", "el órgano emisor citado no coincide")


def cotejar_tipo(citado: str, oficial: str | None) -> Cotejo:
    if not oficial:
        return Cotejo("tipo", citado, oficial, "no_confirmado", "tipo no disponible en el portal")
    if normalizar_tipo(citado) == normalizar_tipo(oficial):
        return Cotejo("tipo", citado, oficial, "coincide")
    return Cotejo("tipo", citado, oficial, "discrepante", "jurisprudencia/aislada no coincide")


def cotejar_fecha(citado: str, oficial: str | None) -> Cotejo:
    f_oficial, f_citado = parsear_fecha(oficial), parsear_fecha(citado)
    if f_oficial is None:
        return Cotejo("fecha_publicacion", citado, oficial, "no_confirmado", "fecha no disponible en el portal")
    if f_citado is None:
        return Cotejo("fecha_publicacion", citado, oficial, "discrepante", "la fecha citada no es interpretable")
    if f_citado == f_oficial:
        return Cotejo("fecha_publicacion", citado, oficial, "coincide")
    return Cotejo("fecha_publicacion", citado, oficial, "discrepante", f"{f_citado.isoformat()} citada vs {f_oficial.isoformat()} oficial")


COTEJADORES = {
    "clave": cotejar_clave,
    "epoca": cotejar_epoca,
    "instancia": cotejar_instancia,
    "tipo": cotejar_tipo,
    "fecha_publicacion": cotejar_fecha,
}
