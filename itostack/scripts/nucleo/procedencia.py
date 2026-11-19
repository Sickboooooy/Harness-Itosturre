"""Contrato estructurado de citas (CR-1): gramática de marcadores, ensamblado desde evidencia y manifiesto de procedencia.

Principio: el agente nunca escribe una cita jurisprudencial; la pide con un marcador. El texto de la cita lo produce un
renderizador (ensamblar_documento.py para escritos, reporte_vvca.py para informes) desde la evidencia, y cada tramo que
produce queda en un manifiesto. Un entregable es válido solo si su manifiesto existe y es completo y coherente, su huella
coincide, todo patrón de cita del texto cae dentro de un tramo del renderizador y, con las fuentes a la vista, cada tramo
se puede volver a verificar contra ellas.

Gramática (cada «[[» del borrador debe abrir uno de estos marcadores; si no, es un error):
  [[CITA:<registro>]]  ·  [[CITA:<registro>|completa|rubro|clave|corta]]   cita verificada (exige evidencia PASS vigente)
  [[CITA_AJENA:<referencia>|<fuente>]]   cita que hizo un tercero; la referencia debe aparecer literal en <fuente>
  [[NO_VERIFICADO:<texto>]]              afirmación propia no verificada; se entrega con advertencia visible

Fuera de un marcador, un borrador no puede contener patrones de cita (registro digital, clave de tesis, «rubro:» o una
marca ⚠/❌/✅ de verificación): el detector de texto libre es una alarma que solo deniega, nunca exime.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from .normalizacion import _COMILLAS

CONTRATO = "itostack/citas@1"
FORMAS = ("completa", "rubro", "clave", "corta")
ADVERTENCIA_FIJA = (
    "⚠ Documento ensamblado con apoyo de IA. Verificar citas en fuentes oficiales antes de uso procesal: "
    "sjf.scjn.gob.mx · dof.gob.mx · diputados.gob.mx/LeyesBiblio"
)
SEPARADOR_NOTAS = "\n\n---\n\n"
VEREDICTOS = ("PASS", "FAIL", "BLOCKED")

# Un marcador por tipo, anclado en la posición del «[[». Los argumentos no cruzan líneas ni contienen corchetes ni «|»:
# así no hay marcadores anidados y ningún «[[» puede llegar al entregable dentro del texto de otro marcador.
_MARCADORES = {
    "CITA": re.compile(r"\[\[CITA:([A-Za-z0-9][A-Za-z0-9-]{0,31})(?:\|([a-z]+))?\]\]"),
    "CITA_AJENA": re.compile(r"\[\[CITA_AJENA:([^\[\]\|\n]+)\|([^\[\]\|\n]+)\]\]"),
    "NO_VERIFICADO": re.compile(r"\[\[NO_VERIFICADO:([^\[\]\n]+)\]\]"),
}
# Patrones de la ALARMA: más agresivos que los de extracción de nucleo/citas.py (sin anclas de palabra), porque un falso
# positivo solo produce una denegación de más y un falso negativo dejaría pasar una cita escrita a mano.
_ALARMA = (
    ("registro", re.compile(r"(?i)(?:registro|ius)(?:\s+(?:digital|ius))?\s*(?:n[úu]m(?:ero)?\.?|no\.)?\s*:?\s*(?:FICT-\d{4}|\d{6,7})(?!\d)")),
    ("registro", re.compile(r"(?i)(?:tesis|jurisprudencia)\s+(?:FICT-\d{4}|\d{6,7})(?!\d)")),
    ("clave", re.compile(r"(?:P|\d{1,2}a|[IVXLC]{1,6}|PR|PC|FICT)\.[^\n()\"“”]{0,40}?\((?:[5-9]|1[0-2])a\.\)")),
    ("rubro", re.compile(r"(?i)rubro\s*:")),
    # Marcas de estado de verificación (⚠ NO VERIFICADO…, ❌, ✅): solo las escribe un renderizador (I-10).
    ("marca", re.compile("❌|✅|⚠️?\\s*(?:CITA\\s+)?NO\\s+VERIFICA", re.IGNORECASE)),
)

# Manifiesto: campos por tipo de documento y por tipo de tramo. Lo que no está aquí es un manifiesto inválido.
_CAMPOS_DOCUMENTO = {
    "escrito": {"contrato", "version_plugin", "tipo_documento", "entregable", "sha256_documento", "sha256_borrador", "tramos"},
    "informe": {"contrato", "version_plugin", "tipo_documento", "entregable", "sha256_documento", "sha256_lote", "tramos", "citas"},
}
_TIPOS_TRAMO = {"escrito": {"CITA", "CITA_PENDIENTE", "CITA_AJENA", "NO_VERIFICADO", "NOTAS"}, "informe": {"INFORME"}}
_CAMPOS_TRAMO = {"inicio", "fin", "tipo", "sha256_texto", "registro", "forma", "nota", "sha256_evidencia", "referencia", "fuente", "sha256_fuente"}
_REQUERIDOS_TRAMO = {
    "CITA": ("registro", "forma", "nota", "sha256_evidencia"),
    "CITA_PENDIENTE": ("registro",),
    "CITA_AJENA": ("referencia", "fuente", "sha256_fuente"),
    "NO_VERIFICADO": (),
    "NOTAS": (),
    "INFORME": ("fuente", "sha256_fuente"),
}
_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Marcador:
    tipo: str
    argumentos: tuple[str, ...]
    inicio: int
    fin: int


@dataclass(frozen=True)
class Tramo:
    """Una porción del documento final escrita por el renderizador (posiciones en caracteres del texto final)."""
    inicio: int
    fin: int
    tipo: str  # CITA · CITA_PENDIENTE · CITA_AJENA · NO_VERIFICADO · NOTAS · INFORME
    registro: str | None = None
    forma: str | None = None
    nota: str | None = None
    sha256_evidencia: str | None = None
    referencia: str | None = None
    fuente: str | None = None
    sha256_fuente: str | None = None


@dataclass
class Ensamblado:
    texto: str = ""
    tramos: list[Tramo] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)
    pendientes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Contexto:
    """Fuentes vivas para volver a verificar un entregable: `evidencia_de(registro)` → fila vigente del almacén o None;
    `fuente_de(ruta)` → (texto, sha256 de los bytes) de un documento del proyecto, o None."""
    evidencia_de: Callable[[str], dict | None]
    fuente_de: Callable[[str], tuple[str, str] | None]


def sha256(datos: str | bytes) -> str:
    return hashlib.sha256(datos.encode("utf-8") if isinstance(datos, str) else datos).hexdigest()


def leer_texto(ruta: Path) -> str:
    """Texto de un documento (.docx, o texto UTF-8): el mismo para extraer, comparar y volver a verificar."""
    if ruta.suffix.lower() == ".docx":
        with zipfile.ZipFile(ruta) as paquete:
            xml = paquete.read("word/document.xml").decode("utf-8")
        parrafos = re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S)
        lineas = ["".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, flags=re.S)) for p in parrafos]
        texto = "\n\n".join(linea for linea in lineas if linea.strip())
        return texto.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    return ruta.read_text(encoding="utf-8")


def lector_de_fuentes(proyecto: Path):
    """`fuente_de` para un proyecto: solo documentos dentro de él (rutas relativas a su raíz)."""
    raiz = proyecto.resolve()

    def leer(ruta: str):
        destino = (raiz / ruta).resolve()
        if not destino.is_file() or not destino.is_relative_to(raiz):
            return None
        try:
            return leer_texto(destino), sha256(destino.read_bytes())
        except (OSError, UnicodeDecodeError, KeyError, zipfile.BadZipFile):
            return None

    return leer


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
    """Alarma de texto libre: posiciones de registros, claves, «rubro:» y marcas ⚠/❌/✅ de verificación."""
    return sorted((m.start(), m.end(), tipo) for tipo, patron in _ALARMA for m in patron.finditer(texto))


def _dentro(inicio: int, fin: int, intervalos) -> bool:
    return any(a <= inicio and fin <= b for a, b in intervalos)


def citas_fuera_de_marcadores(texto: str) -> list[str]:
    """Patrones de cita escritos a mano en un borrador (fuera de todo marcador). Cada uno impide ensamblar."""
    marcadores, _ = analizar(texto)
    dentro = [(m.inicio, m.fin) for m in marcadores]
    return [f"línea {_linea(texto, a)}: {tipo} escrito a mano «{texto[a:b]}»: usa un marcador ([[CITA:…]], [[CITA_AJENA:…|…]] o [[NO_VERIFICADO:…]])"
            for a, b, tipo in patrones_de_cita(texto) if not _dentro(a, b, dentro)]


def problemas_de_borrador(texto: str) -> list[str]:
    """Todo lo que impide que un borrador llegue a ser entregable: marcadores inválidos y citas escritas a mano."""
    return analizar(texto)[1] + citas_fuera_de_marcadores(texto)


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


def comparable(texto: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", texto).translate(_COMILLAS)).strip().casefold()


_comparable = comparable


def literal_en(fragmento: str, fuente: str) -> bool:
    """El fragmento aparece en la fuente, salvo espacios, comillas tipográficas y mayúsculas."""
    return bool(comparable(fragmento)) and comparable(fragmento) in comparable(fuente)


def texto_cita_ajena(referencia: str, ruta: str) -> str:
    return f"{referencia} (⚠ CITA NO VERIFICADA: así la cita {Path(ruta).name}; no se cotejó con el Semanario Judicial)"


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
            nota = f"[^ev{numeracion[registro]}]"
            agregar(formatear(json.loads(fila["datos_oficiales"]), forma, nota),
                    {"tipo": "CITA", "registro": registro, "forma": forma, "nota": nota, "sha256_evidencia": fila["sha256_resultado"]})
        elif m.tipo == "CITA_AJENA":
            referencia, ruta = m.argumentos
            fuente = fuente_de(ruta)
            if fuente is None:
                resultado.errores.append(f"[[CITA_AJENA:…|{ruta}]]: la fuente no existe o está fuera del proyecto")
                continue
            contenido, huella = fuente
            if not literal_en(referencia, contenido):
                resultado.errores.append(f"[[CITA_AJENA:{referencia}|{ruta}]]: la referencia no aparece literal en la fuente")
                continue
            agregar(texto_cita_ajena(referencia, ruta), {"tipo": "CITA_AJENA", "referencia": referencia, "fuente": ruta, "sha256_fuente": huella})
        else:
            agregar(f"{m.argumentos[0]} (⚠ NO VERIFICADO)", {"tipo": "NO_VERIFICADO"})
    agregar(texto[cursor:].rstrip())
    agregar(SEPARADOR_NOTAS + ("\n".join(notas) + "\n\n" if notas else "") + ADVERTENCIA_FIJA + "\n", {"tipo": "NOTAS"})
    if resultado.errores:
        return Ensamblado(errores=resultado.errores, pendientes=resultado.pendientes)
    resultado.texto, resultado.tramos = "".join(partes), tramos
    return resultado


def _tramo_dict(texto: str, tramo: Tramo) -> dict:
    datos = {k: v for k, v in asdict(tramo).items() if v is not None}
    datos["sha256_texto"] = sha256(texto[tramo.inicio:tramo.fin])
    return datos


def manifiesto(documento: str, borrador: str, ensamblado: Ensamblado, version_plugin: str) -> dict:
    """Procedencia de un escrito: huella del texto final y de cada tramo que escribió el ensamblador."""
    return {
        "contrato": CONTRATO,
        "version_plugin": version_plugin,
        "tipo_documento": "escrito",
        "entregable": not ensamblado.pendientes,
        "sha256_documento": sha256(documento),
        "sha256_borrador": sha256(borrador),
        "tramos": [_tramo_dict(documento, t) for t in ensamblado.tramos],
    }


def manifiesto_informe(documento: str, version_plugin: str, fuente: str, sha256_fuente: str, sha256_lote: str, citas: list[dict]) -> dict:
    """Procedencia de un informe VVCA: todo el texto lo escribe el renderizador desde el lote verificado; las citas que
    reporta son las del documento auditado (`fuente`), y cada una debe aparecer literal en él."""
    tramo = Tramo(inicio=0, fin=len(documento), tipo="INFORME", fuente=fuente, sha256_fuente=sha256_fuente)
    return {
        "contrato": CONTRATO,
        "version_plugin": version_plugin,
        "tipo_documento": "informe",
        "entregable": True,
        "sha256_documento": sha256(documento),
        "sha256_lote": sha256_lote,
        "tramos": [_tramo_dict(documento, tramo)],
        "citas": citas,
    }


def afirmaciones_de(cita: dict) -> list[tuple[str, str]]:
    """Lo que un informe afirma que dice el documento auditado sobre una cita: debe aparecer literal en él."""
    return [(campo, cita[campo]) for campo in ("registro", "clave", "rubro_citado", "extracto") if isinstance(cita.get(campo), str) and cita[campo].strip()]


def _es_hex(valor) -> bool:
    return isinstance(valor, str) and bool(_HEX.match(valor))


def _entero(valor) -> bool:
    return type(valor) is int


def validar_manifiesto(datos, texto: str) -> list[str]:
    """Completo y coherente con el texto: cualquier campo faltante, de más, de otro tipo o inconsistente es un error."""
    if not isinstance(datos, dict) or datos.get("contrato") != CONTRATO:
        return ["sin manifiesto de procedencia válido (contrato itostack/citas@1)"]
    tipo_documento = datos.get("tipo_documento")
    if not isinstance(tipo_documento, str) or tipo_documento not in _CAMPOS_DOCUMENTO:
        return [f"manifiesto incompleto: tipo_documento «{tipo_documento}» desconocido"]
    errores = []
    esperados = _CAMPOS_DOCUMENTO[tipo_documento]
    if set(datos) != esperados:
        faltan, sobran = sorted(esperados - set(datos)), sorted(set(datos) - esperados)
        errores.append(f"manifiesto incompleto o con campos ajenos (faltan {faltan or '—'}; sobran {sobran or '—'})")
    if not isinstance(datos.get("version_plugin"), str) or not isinstance(datos.get("entregable"), bool):
        errores.append("manifiesto con tipos inválidos (version_plugin o entregable)")
    for campo in esperados & {"sha256_documento", "sha256_borrador", "sha256_lote"}:
        if not _es_hex(datos.get(campo)):
            errores.append(f"manifiesto con {campo} inválido")
    tramos = datos.get("tramos")
    if not isinstance(tramos, list) or not tramos:
        return errores + ["manifiesto sin tramos"]
    anterior = 0
    for i, tramo in enumerate(tramos):
        if not isinstance(tramo, dict) or not set(tramo) <= _CAMPOS_TRAMO or not {"inicio", "fin", "tipo", "sha256_texto"} <= set(tramo):
            errores.append(f"tramo {i}: campos incompletos o ajenos")
            continue
        tipo = tramo["tipo"]
        if not isinstance(tipo, str) or tipo not in _TIPOS_TRAMO[tipo_documento]:
            errores.append(f"tramo {i}: tipo «{tipo}» no válido en un {tipo_documento}")
            continue
        inicio, fin = tramo["inicio"], tramo["fin"]
        if not (_entero(inicio) and _entero(fin) and anterior <= inicio <= fin <= len(texto)):
            errores.append(f"tramo {i}: posiciones fuera de orden, solapadas o fuera del documento")
            continue
        anterior = fin
        faltantes = [c for c in _REQUERIDOS_TRAMO[tipo] if not isinstance(tramo.get(c), str) or not tramo[c].strip()]
        if faltantes:
            errores.append(f"tramo {i} ({tipo}): faltan {faltantes}")
        for campo in ("sha256_texto", "sha256_evidencia", "sha256_fuente"):
            if campo in tramo and not _es_hex(tramo[campo]):
                errores.append(f"tramo {i}: {campo} inválido")
        if tipo == "CITA" and tramo.get("forma") not in FORMAS:
            errores.append(f"tramo {i}: forma inválida")
        if _es_hex(tramo.get("sha256_texto")) and sha256(texto[inicio:fin]) != tramo["sha256_texto"]:
            errores.append(f"tramo {i}: su texto no corresponde al documento")
    tipos = [t.get("tipo") for t in tramos if isinstance(t, dict)]
    if tipo_documento == "escrito":
        ultimo = tramos[-1] if isinstance(tramos[-1], dict) else {}
        if tipos.count("NOTAS") != 1 or ultimo.get("tipo") != "NOTAS" or ultimo.get("fin") != len(texto):
            errores.append("manifiesto inconsistente: el escrito debe cerrar con un único tramo de notas")
        if datos.get("entregable") is True and "CITA_PENDIENTE" in tipos:
            errores.append("manifiesto inconsistente: se declara entregable con citas pendientes")
        errores += _notas_incoherentes(texto, [t for t in tramos if isinstance(t, dict)])
    else:
        if tipos != ["INFORME"] or not isinstance(tramos[0], dict) or tramos[0].get("inicio") != 0 or tramos[0].get("fin") != len(texto):
            errores.append("manifiesto inconsistente: el informe debe ser un único tramo del renderizador")
        citas = datos.get("citas")
        if not isinstance(citas, list) or not all(isinstance(c, dict) and c.get("veredicto") in VEREDICTOS and isinstance(c.get("id"), str) for c in citas):
            errores.append("manifiesto incompleto: citas del informe sin id o veredicto válidos")
    return errores


_RE_LLAMADA = re.compile(r"\[\^ev\d+\]")
_RE_DEFINICION = re.compile(r"^(\[\^ev\d+\]):", re.MULTILINE)


def _notas_incoherentes(texto: str, tramos: list[dict]) -> list[str]:
    """Un manifiesto completo declara todas sus citas: cada llamada [^evN] del cuerpo cae dentro del tramo CITA que la
    lleva como nota, y las notas definidas son exactamente las de esos tramos. Así no se puede omitir un tramo de cita
    (p. ej. uno en forma «rubro», cuyo texto no dispara la alarma) sin que se note."""
    notas = [t for t in tramos if t.get("tipo") == "NOTAS"]
    citas = [t for t in tramos if t.get("tipo") == "CITA" and _entero(t.get("inicio")) and _entero(t.get("fin"))]
    if len(notas) != 1 or not (_entero(notas[0].get("inicio")) and _entero(notas[0].get("fin"))):
        return []  # ya informado por la regla del tramo de notas
    errores = []
    for m in _RE_LLAMADA.finditer(texto, 0, notas[0]["inicio"]):
        if not any(c["inicio"] <= m.start() and m.end() <= c["fin"] and c.get("nota") == m.group(0) for c in citas):
            errores.append(f"línea {_linea(texto, m.start())}: la llamada {m.group(0)} no pertenece a ningún tramo de cita del manifiesto")
    definidas = set(_RE_DEFINICION.findall(texto[notas[0]["inicio"]:notas[0]["fin"]]))
    if definidas != {c["nota"] for c in citas if isinstance(c.get("nota"), str)}:
        errores.append("manifiesto inconsistente: las notas de evidencia no coinciden con los tramos de cita declarados")
    return errores


def _reverificar(texto: str, datos: dict, contexto: Contexto) -> list[str]:
    """Vuelve a comprobar cada tramo contra las fuentes vivas: evidencia, fuentes de citas ajenas y documento auditado."""
    errores = []
    for i, tramo in enumerate(datos["tramos"]):
        fragmento = texto[tramo["inicio"]:tramo["fin"]]
        if tramo["tipo"] == "CITA":
            fila = contexto.evidencia_de(tramo["registro"])
            if not fila:
                errores.append(f"tramo {i}: la cita {tramo['registro']} ya no tiene evidencia PASS vigente")
            elif fila["sha256_resultado"] != tramo["sha256_evidencia"]:
                errores.append(f"tramo {i}: la evidencia vigente de {tramo['registro']} no es la que se usó al ensamblar")
            elif formatear(json.loads(fila["datos_oficiales"]), tramo["forma"], tramo["nota"]) != fragmento:
                errores.append(f"tramo {i}: el texto de la cita {tramo['registro']} no es el de su evidencia")
        elif tramo["tipo"] in {"CITA_AJENA", "INFORME"}:
            fuente = contexto.fuente_de(tramo["fuente"])
            if fuente is None:
                errores.append(f"tramo {i}: la fuente «{tramo['fuente']}» no está disponible dentro del proyecto")
                continue
            contenido, huella = fuente
            if huella != tramo["sha256_fuente"]:
                errores.append(f"tramo {i}: la fuente «{tramo['fuente']}» cambió después de generar el documento")
            elif tramo["tipo"] == "CITA_AJENA" and (not literal_en(tramo["referencia"], contenido)
                                                     or fragmento != texto_cita_ajena(tramo["referencia"], tramo["fuente"])):
                errores.append(f"tramo {i}: la cita ajena no conserva su procedencia literal")
            elif tramo["tipo"] == "INFORME":
                for cita in datos["citas"]:
                    for campo, valor in afirmaciones_de(cita):
                        if not literal_en(valor, contenido):
                            errores.append(f"cita {cita['id']}: su {campo} «{valor[:60]}» no aparece literal en el documento auditado")
    return errores


def verificar_entrega(documento: bytes, datos_manifiesto, contexto: Contexto | None = None) -> list[str]:
    """Razones por las que un documento NO es entregable (BLOCKED); vacío = entregable (PASS). No confía en nada que no
    pueda recalcular. Con `contexto`, además vuelve a verificar cada tramo contra la evidencia y las fuentes vivas."""
    if not isinstance(datos_manifiesto, dict) or datos_manifiesto.get("contrato") != CONTRATO:
        return ["sin manifiesto de procedencia válido (contrato itostack/citas@1)"]
    if sha256(documento) != datos_manifiesto.get("sha256_documento"):
        return ["el documento cambió después de generarse (su huella no coincide con el manifiesto)"]
    try:
        texto = documento.decode("utf-8")
    except UnicodeDecodeError:
        return ["el documento no es UTF-8"]
    errores = validar_manifiesto(datos_manifiesto, texto)
    if errores:
        return errores
    if datos_manifiesto["entregable"] is not True:
        errores.append("el manifiesto declara citas pendientes de verificar: es un borrador, no un entregable")
    intervalos = [(t["inicio"], t["fin"]) for t in datos_manifiesto["tramos"]]
    if "[[" in texto:
        errores.append(f"línea {_linea(texto, texto.find('[['))}: quedó un marcador sin resolver")
    for a, b, tipo in patrones_de_cita(texto):
        if not _dentro(a, b, intervalos):
            errores.append(f"línea {_linea(texto, a)}: {tipo} «{texto[a:b]}» fuera de los tramos del renderizador (escrito a mano)")
    if contexto is not None:
        errores += _reverificar(texto, datos_manifiesto, contexto)
    return errores
