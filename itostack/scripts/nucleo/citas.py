"""Detección de citas jurisprudenciales en texto libre.

Detecta registros digitales, claves de tesis y marcadores [[CITA:registro]]. No intenta
"entender" la cita: solo localiza lo que debe pasar por verificación forense.
"""

from __future__ import annotations

import bisect
import re
from dataclasses import dataclass, field

RE_REGISTRO = re.compile(
    r"(?i)\b(?:registro(?:\s+(?:digital|ius))?|ius)\s*(?:n[úu]m(?:ero)?\.?|no\.)?\s*:?\s*(FICT-\d{4}|\d{6,7})\b"
)
RE_CLAVE = re.compile(
    r"(?<![\w/])((?:P|\d{1,2}a|[IVXLC]{1,6}|PR|PC|FICT)\.[^\n()\"“”]{0,40}?\((?:[5-9]|1[0-2])a\.\))"
)
RE_MARCADOR = re.compile(r"\[\[CITA:([^\]|\s]+)(?:\|([a-z]+))?\]\]")
# Marca explícita de cita no verificada: «⚠ NO VERIFICADO», «⚠ CITA NO VERIFICADA», «⚠ NO VERIFICABLE» o «❌».
# D-04: solo cuenta FUERA del texto entrecomillado. Una palabra del rubro («…INEXISTENTE…») o una advertencia de
# contexto («⚠ Tesis aislada») no exime a la cita de la evidencia.
RE_MARCA_NO_VERIFICADA = re.compile(r"❌|⚠\ufe0f?\s*(?:CITA\s+)?NO\s+VERIFICA(?:D[AO]S?|BLES?)\b", re.IGNORECASE)
RE_ENTRECOMILLADO = re.compile(r"«[^»]*»|“[^”]*”|\"[^\"\n]*\"")
# Sin límite de longitud, y cada apertura con SU cierre: «DERECHO A LA "VERDAD". ALCANCE.» se captura entero.
RE_RUBRO_ENTRECOMILLADO = re.compile(r"(?i)rubro\s*:?\s*(?:«([^»]+)»|“([^”]+)”|\"([^\"]+)\")")
RE_RUBRO_MAYUSCULAS = re.compile(r"([A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ0-9 ,;:()\-\"“”'’]{30,800}[.])")
# Un rubro declarado sin comillas («Rubro: LA VERIFICACIÓN…», «RUBRO LA…»): lo que sigue debe empezar con el rubro
# oficial. No cotejarlo dejaría pasar un rubro falso respaldado por la evidencia del registro (N-01).
RE_RUBRO_DECLARADO = re.compile(r"(?i:\brubro)\s*:\s*(?=[^\s\"“«])|(?i:\brubro)\s+(?=[A-ZÁÉÍÓÚÑÜ]{3,})")
# Entre una cita y su marca (o entre citas de un mismo grupo) solo puede haber puntuación y estas palabras.
CONECTORES = {"registro", "digital", "ius", "num", "núm", "numero", "número", "no", "de", "rubro", "tesis", "jurisprudencia", "clave"}
# Cortes de segmento: «;» o un fin de oración. Un corte que cae dentro de una cita (las claves llevan puntos:
# «P. J/9») no cuenta, y se calculan sin el texto entrecomillado (el punto de un rubro no corta).
RE_CORTE = re.compile(r";|(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡\[])")


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


_SALTOS = re.compile(r"[^\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029]")


def _sin_comillas(texto: str) -> str:
    """Borra el texto entrecomillado conservando las posiciones y los saltos de línea (una cita entre «» puede
    abarcar varias líneas: su interior sigue siendo texto citado)."""
    return RE_ENTRECOMILLADO.sub(lambda m: _SALTOS.sub(" ", m.group(0)), texto)


def _rubro(m: re.Match) -> str:
    return re.sub(r"\s+", " ", next(g for g in m.groups() if g is not None)).strip()


def _declaraciones(texto: str) -> list[re.Match]:
    """Declaraciones de rubro sin comillas que no están dentro de un texto entrecomillado."""
    comillas = [(m.start(), m.end()) for m in RE_ENTRECOMILLADO.finditer(texto)]
    return [m for m in RE_RUBRO_DECLARADO.finditer(texto) if not any(a <= m.start() < b for a, b in comillas)]


def _texto_tras_rubro(texto: str) -> str | None:
    """Texto que sigue a un «rubro» declarado sin comillas (None si no hay declaración)."""
    declaraciones = _declaraciones(texto)
    if not declaraciones:
        return None
    return re.sub(r"\s+", " ", texto[declaraciones[0].end():]).strip()


def extraer(texto: str) -> list[Cita]:
    encontradas: list[Cita] = []
    visibles_por_linea = _sin_comillas(texto).splitlines()
    for numero, linea in enumerate(texto.splitlines(), start=1):
        halladas: list[tuple[str, str, int, int, int, str | None]] = []  # tipo, valor, columna, inicio, fin, forma
        for m in RE_MARCADOR.finditer(linea):
            halladas.append(("marcador", m.group(1), m.start() + 1, m.start(), m.end(), m.group(2)))
        sin_marcadores = RE_MARCADOR.sub(lambda m: " " * len(m.group(0)), linea)
        for m in RE_REGISTRO.finditer(sin_marcadores):
            halladas.append(("registro", m.group(1).upper(), m.start(1) + 1, m.start(), m.end(), None))
        for m in RE_CLAVE.finditer(sin_marcadores):
            halladas.append(("clave", m.group(1).strip(), m.start(1) + 1, m.start(1), m.end(1), None))
        if not halladas:
            continue
        marcadas = _citas_marcadas(visibles_por_linea[numero - 1], halladas)
        for indice, (tipo, valor, columna, _, _, forma) in enumerate(halladas):
            encontradas.append(Cita(tipo, valor, numero, columna, linea, indice in marcadas, forma))
    return encontradas


def _contiguas(visibles: str, desde: int, hasta: int) -> bool:
    """Entre dos posiciones solo hay puntuación, cifras y palabras conectoras («registro digital», «de rubro»)."""
    return all(p in CONECTORES for p in re.findall(r"[^\W\d_]+", visibles[desde:hasta].lower()))


def _citas_marcadas(visibles: str, halladas: list) -> set[int]:
    """Índices de las citas que una marca ⚠/❌ exime: el grupo contiguo pegado a la marca, dentro de su segmento.

    La marca se asocia a las citas que la preceden sin palabras de por medio (o, si no hay, a las que la siguen):
    «registro FICT-0404 ❌, pero se aplica el registro FICT-0009» no exime a FICT-0009, y «1a./J. 45/2019 (10a.),
    registro digital 1999999 ⚠ NO VERIFICADO» exime a la clave y al registro de la misma cita.
    """
    citas = sorted((inicio, fin, i) for i, (tipo, _, _, inicio, fin, _) in enumerate(halladas) if tipo != "marcador")
    cortes = [m.start() for m in RE_CORTE.finditer(visibles) if not any(a <= m.start() < b for a, b, _ in citas)]
    marcadas: set[int] = set()
    for marca in RE_MARCA_NO_VERIFICADA.finditer(visibles):
        segmento = bisect.bisect_right(cortes, marca.start())
        mismas = [c for c in citas if bisect.bisect_right(cortes, c[0]) == segmento]
        previas = [c for c in mismas if c[1] <= marca.start()]
        siguientes = [c for c in mismas if c[0] >= marca.end()]
        grupo: list = []
        if previas and _contiguas(visibles, previas[-1][1], marca.start()):
            grupo = [previas[-1]]
            for cita in reversed(previas[:-1]):
                if not _contiguas(visibles, cita[1], grupo[-1][0]):
                    break
                grupo.append(cita)
        elif siguientes and _contiguas(visibles, marca.end(), siguientes[0][0]):
            grupo = [siguientes[0]]
            for cita in siguientes[1:]:
                if not _contiguas(visibles, grupo[-1][1], cita[0]):
                    break
                grupo.append(cita)
        marcadas.update(c[2] for c in grupo)
    return marcadas


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
    # True si el rubro vino de «rubro: "…"» explícito; False si se infirió de un bloque en mayúsculas.
    rubro_explicito: bool = False
    # True si el texto dice «rubro: …» o «rubro LA …» sin comillas: afirma un rubro aunque no se pueda aislar.
    rubro_declarado: bool = False
    # Lo que sigue a la palabra «rubro» en ese caso: debe empezar con el rubro oficial completo.
    texto_tras_rubro: str | None = None
    # Rubros del párrafo que no se pudieron asociar a una sola cita: con evidencia de por medio, se rechazan.
    rubros_ambiguos: int = 0

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


def _referencias_del_parrafo(parrafo: str, registros: list[Cita], claves: list[Cita]) -> tuple[list[list[Cita]], dict[int, tuple[str | None, str | None]], int]:
    """Varias citas en un párrafo: arma las referencias por proximidad y les asigna sus rubros.

    - Cada clave se une al registro libre más cercano de su segmento (no por orden de aparición): en
      «registro A, rubro «X», registro B, clave K, rubro «Y»», K va con B.
    - Cada rubro (entrecomillado o declarado) va a la referencia que lo contiene (clave … rubro … registro, el formato
      de ensamblar_documento.py), si no a la más cercana que lo precede en su segmento y, si no, a la que lo sigue. Las
      posiciones son del párrafo completo: un rubro en la línea siguiente a su registro también se asigna.
    - Un rubro sin dueño claro (ninguno, o la referencia ya tiene otro) se cuenta como ambiguo.
    """
    desplazamientos, acumulado = [], 0
    for linea in parrafo.split("\n"):
        desplazamientos.append(acumulado)
        acumulado += len(linea) + 1

    def tramo(c: Cita) -> tuple[int, int]:
        inicio = desplazamientos[c.linea - 1] + c.columna - 1
        return inicio, inicio + len(c.valor)

    visibles = _sin_comillas(parrafo)
    todas = [tramo(c) for c in registros + claves]
    cortes = [m.start() for m in RE_CORTE.finditer(visibles) if not any(a <= m.start() < b for a, b in todas)]

    def segmento(posicion: int) -> int:
        return bisect.bisect_right(cortes, posicion)

    referencias: list[list[Cita]] = [[r] for r in registros]
    for clave in claves:
        inicio = tramo(clave)[0]
        libres = [(abs(inicio - tramo(r[0])[0]), i) for i, r in enumerate(referencias)
                  if len(r) == 1 and r[0].tipo == "registro" and segmento(tramo(r[0])[0]) == segmento(inicio)]
        if libres:
            referencias[min(libres)[1]].append(clave)
        else:
            referencias.append([clave])
    referencias.sort(key=lambda r: min(tramo(c)[0] for c in r))
    tramos = [(min(tramo(c)[0] for c in r), max(tramo(c)[1] for c in r)) for r in referencias]

    def dueno(inicio: int, fin: int) -> int | None:
        dentro = [k for k, (a, b) in enumerate(tramos) if a <= inicio and fin <= b]
        if dentro:
            return dentro[0]
        previas = [(inicio - b, k) for k, (a, b) in enumerate(tramos) if b <= inicio and segmento(a) == segmento(inicio)]
        if previas:
            return min(previas)[1]
        siguientes = [(a - fin, k) for k, (a, b) in enumerate(tramos) if a >= fin and segmento(a) == segmento(inicio)]
        return min(siguientes)[1] if siguientes else None

    asignados: dict[int, tuple[str | None, str | None]] = {}
    ambiguos = 0
    for m in RE_RUBRO_ENTRECOMILLADO.finditer(parrafo):
        k = dueno(m.start(), m.end())
        if k is None or k in asignados:
            ambiguos += 1
            continue
        asignados[k] = (_rubro(m), None)
    for m in _declaraciones(parrafo):
        k = dueno(m.start(), m.end())
        if k is None or k in asignados:
            ambiguos += 1
            continue
        # Hasta la siguiente cita: un rubro sin comillas tiene puntos propios («LEGALIDAD. SU ALCANCE.»).
        fin = min([a for a, _ in tramos if a > m.end()] + [len(parrafo)])
        asignados[k] = (None, re.sub(r"\s+", " ", parrafo[m.end():fin]).strip())
    return referencias, asignados, ambiguos


def agrupar_referencias(texto: str) -> list[Referencia]:
    referencias: list[Referencia] = []
    for indice, (linea_inicio, parrafo) in enumerate(_parrafos(texto), start=1):
        citas = extraer(parrafo)
        registros = [c for c in citas if c.tipo == "registro"]
        claves = [c for c in citas if c.tipo == "clave"]
        if not registros and not claves:
            continue
        lineas = sorted({c.linea + linea_inicio - 1 for c in citas})
        extracto = re.sub(r"\s+", " ", parrafo)[:300]
        if len(registros) == 1 and len(claves) == 1 and len(_referencias_del_parrafo(parrafo, registros, claves)[0]) == 2:
            registros_y_claves_separados = True  # registro y clave en segmentos distintos: dos citas, no una
        else:
            registros_y_claves_separados = False
        if len(registros) <= 1 and len(claves) <= 1 and not registros_y_claves_separados:
            # Una sola cita: el rubro del párrafo (entrecomillado o, para validar documentos, el bloque en mayúsculas).
            entrecomillados = list(RE_RUBRO_ENTRECOMILLADO.finditer(parrafo))
            entrecomillado = entrecomillados[0] if entrecomillados else None
            rubro = _rubro(entrecomillado) if entrecomillado else None
            if not entrecomillado:
                mayusculas = [m.group(1) for m in RE_RUBRO_MAYUSCULAS.finditer(parrafo) if len(m.group(1).split()) >= 6]
                if mayusculas:
                    rubro = re.sub(r"\s+", " ", max(mayusculas, key=len)).strip()
            tras = _texto_tras_rubro(parrafo)
            propias = registros + claves
            referencias.append(Referencia(
                id=f"c{len(referencias) + 1:02d}", parrafo=indice,
                registro=registros[0].valor if registros else None, clave=claves[0].valor if claves else None,
                rubro=rubro, marcada_no_verificada=any(c.marcada_no_verificada for c in propias),
                extracto=extracto, lineas=lineas, rubro_explicito=bool(entrecomillado),
                rubro_declarado=tras is not None, texto_tras_rubro=tras,
                # Un segundo rubro para la misma cita es una atribución que nadie coteja: se rechaza.
                rubros_ambiguos=max(0, len(entrecomillados) + (1 if tras is not None else 0) - 1),
            ))
            continue
        grupos, asignados, ambiguos = _referencias_del_parrafo(parrafo, registros, claves)
        for k, propias in enumerate(grupos):
            rubro, tras = asignados.get(k, (None, None))
            referencias.append(Referencia(
                id=f"c{len(referencias) + 1:02d}", parrafo=indice,
                registro=next((c.valor for c in propias if c.tipo == "registro"), None),
                clave=next((c.valor for c in propias if c.tipo == "clave"), None),
                rubro=rubro,
                # La marca ⚠/❌ de UNA cita no exime a las demás del párrafo: solo cuentan el registro y la clave propios.
                marcada_no_verificada=any(c.marcada_no_verificada for c in propias),
                extracto=extracto, lineas=lineas, rubro_explicito=rubro is not None,
                rubro_declarado=tras is not None, texto_tras_rubro=tras, rubros_ambiguos=ambiguos,
            ))
    return referencias


def rubros_discrepantes(texto: str, oficial_de, ignorar_acentos: bool = True) -> list[str]:
    """N-01: la evidencia de un registro no respalda otra tesis.

    `oficial_de(registro, clave)` devuelve los datos oficiales de la evidencia vigente, o None si no hay evidencia
    (eso ya lo reporta la comprobación de evidencia). Para cada referencia con evidencia:
    - si trae registro y clave, la clave debe ser la de la evidencia del registro (no la de otra tesis);
    - un rubro entrecomillado debe coincidir con el oficial y uno declarado sin comillas («Rubro: LA …») debe empezar
      con el rubro oficial completo;
    - un rubro del párrafo que no se puede asociar a una sola cita se rechaza.
    Un bloque en mayúsculas sin la palabra «rubro» no se coteja: es una heurística y daría falsos rechazos.
    """
    from . import normalizacion as norm

    problemas = []
    ambiguos_reportados: set[int] = set()
    for referencia in agrupar_referencias(texto):
        if referencia.marcada_no_verificada:
            continue
        identificador = referencia.registro or referencia.clave
        linea = referencia.lineas[0] if referencia.lineas else "?"
        oficial = oficial_de(referencia.registro, None if referencia.registro else referencia.clave)
        if oficial is None:
            continue
        if referencia.registro and referencia.clave and oficial.get("clave"):
            cotejo_clave = norm.cotejar_clave(referencia.clave, oficial.get("clave"))
            if cotejo_clave.estado not in {"coincide", "tipografica"}:
                problemas.append(f"línea {linea}: la clave «{referencia.clave}» no es la del registro {referencia.registro} según su evidencia")
        if referencia.rubros_ambiguos and referencia.parrafo not in ambiguos_reportados:
            ambiguos_reportados.add(referencia.parrafo)
            problemas.append(f"línea {linea}: hay rubros que no se pueden asociar a una sola cita; pon cada rubro junto a su registro "
                             "o usa marcadores [[CITA:registro|rubro]]")
        if referencia.rubro_explicito and referencia.rubro:
            cotejo = norm.cotejar_rubro(referencia.rubro, oficial.get("rubro"), ignorar_acentos)
            if cotejo.estado not in {"coincide", "tipografica"}:
                problemas.append(f"línea {linea}: el rubro escrito para «{identificador}» no es el de su evidencia ({cotejo.detalle or cotejo.estado})")
        elif referencia.rubro_declarado:
            escrito = norm.normalizar_texto(referencia.texto_tras_rubro or "", ignorar_acentos)
            esperado = norm.normalizar_texto(oficial.get("rubro"), ignorar_acentos)
            if not esperado or not escrito.startswith(esperado):
                problemas.append(f"línea {linea}: el rubro declarado para «{identificador}» no empieza con el rubro oficial de su evidencia; "
                                 f"escríbelo completo y entre comillas («…») o usa [[CITA:{identificador}|rubro]]")
    return problemas
