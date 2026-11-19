"""CR-1.1 · contrato estructurado de citas (itostack/citas@1): gramática, ensamblado desde evidencia y procedencia.

Cada prueba demuestra una propiedad para una familia de entradas (Hypothesis), no un caso suelto. Invariantes:
- I-8  ninguna cita en un entregable sin evidencia o advertencia que emite el ensamblador;
- I-9  rubro y clave del entregable == evidencia;
- I-10 ninguna marca ⚠/❌ que no haya escrito el ensamblador.
El texto libre de las estrategias usa un alfabeto que nunca forma un patrón de cita: todo patrón que aparece en un
borrador lo puso la prueba a propósito, así que el oráculo sabe exactamente qué esperar.
"""

import json

import pytest
from hypothesis import given, settings, strategies as st

from nucleo import procedencia

PROPIEDADES = settings(max_examples=400, deadline=None)

LIBRE = st.text(alphabet="abcdefghijklmnñopqrstuvwxyz áéíóú.,;", max_size=25)
REGISTROS = st.sampled_from([f"FICT-00{i:02d}" for i in range(1, 13)] + ["2025432", "1999999", "174536"])
TEXTO_OFICIAL = st.text(alphabet=st.characters(blacklist_characters="[]\n\r", blacklist_categories=("Cs",)), min_size=1, max_size=60)
CLAVES = st.builds(lambda n, a, e: f"{n}a./J. {a}/2019 ({e}a.)", st.integers(1, 2), st.integers(1, 99), st.integers(9, 11))
A_MANO = ["registro digital 2012345", "1a./J. 45/2019 (10a.)", "rubro: «UN RUBRO DE MEMORIA.»", "⚠ NO VERIFICADO", "❌", "✅ VERIFICADA", "IUS 1234567", "tesis 2012345"]
ROTOS = ["[[CITA:", "[[CITA:FICT-0001|resumen]]", "[[OTRO:x]]", "[[CITA_AJENA:solo referencia]]", "[[ ]]", "[[NO_VERIFICADO: ]]", "[[CITA:FICT 1]]",
         "[[NO_VERIFICADO:dato [[x]]", "[[CITA_AJENA:ref [x]|exp/a.md]]"]


@st.composite
def evidencias(draw):
    """Almacén de evidencia generado: registro → fila como la devuelve AlmacenEvidencia.vigente()."""
    almacen = {}
    for registro in draw(st.lists(REGISTROS, min_size=1, max_size=6, unique=True)):
        oficial = {"registro": registro, "rubro": draw(TEXTO_OFICIAL), "clave": draw(CLAVES), "tipo": draw(st.sampled_from(["Jurisprudencia", "Tesis aislada"])),
                   "instancia": draw(TEXTO_OFICIAL), "epoca": draw(TEXTO_OFICIAL)}
        almacen[registro] = {"datos_oficiales": json.dumps(oficial, ensure_ascii=False), "advertencias": json.dumps(draw(st.lists(LIBRE, max_size=2))),
                             "creado_en": "2026-11-19T00:00:00+00:00", "modo_fuente": "fixture", "ruta_resultado": f".itostack/evidencia/{registro}.json",
                             "sha256_resultado": procedencia.sha256(registro + oficial["rubro"])}
    return almacen


@st.composite
def borradores(draw, almacen, fuentes=None):
    """Borrador con texto libre y marcadores válidos; devuelve (borrador, [(registro, forma)] de cada CITA en orden)."""
    partes, pedidas = [], []
    for _ in range(draw(st.integers(1, 8))):
        partes.append(draw(LIBRE))
        clase = draw(st.sampled_from(["CITA", "CITA", "NO_VERIFICADO"] + (["CITA_AJENA"] if fuentes else [])))
        if clase == "CITA":
            registro = draw(st.sampled_from(sorted(almacen)))
            forma = draw(st.sampled_from([None, *procedencia.FORMAS]))
            partes.append(f"[[CITA:{registro}]]" if forma is None else f"[[CITA:{registro}|{forma}]]")
            pedidas.append((registro, forma or "completa"))
        elif clase == "NO_VERIFICADO":
            partes.append(f"[[NO_VERIFICADO:{draw(LIBRE.filter(str.strip))}]]")
        else:
            ruta = draw(st.sampled_from(sorted(fuentes)))
            partes.append(f"[[CITA_AJENA:1a./J. 45/2019 (10a.)|{ruta}]]")
    partes.append(draw(LIBRE))
    return "".join(partes), pedidas


def ensamblar(borrador, almacen, fuentes=None, **kw):
    return procedencia.ensamblar(borrador, almacen.get, lambda ruta: (fuentes or {}).get(ruta), **kw)


# ---------------------------------------------------------------- gramática y alarma del borrador

@PROPIEDADES
@given(st.lists(st.one_of(LIBRE, st.sampled_from(["[[CITA:FICT-0001]]", "[[CITA:2025432|rubro]]", "[[NO_VERIFICADO:dato]]", "[[CITA_AJENA:x|exp/a.md]]"]),
                          st.sampled_from(ROTOS)), max_size=12))
def test_gramatica_todo_doble_corchete_es_un_marcador_valido_o_un_error(fragmentos):
    marcadores, errores = procedencia.analizar("".join(fragmentos))
    validos = [f for f in fragmentos if f.startswith("[[") and f not in ROTOS]
    assert bool(errores) == any(f in ROTOS for f in fragmentos)
    assert [texto for texto in ("".join(fragmentos)[m.inicio:m.fin] for m in marcadores)] == validos


@PROPIEDADES
@given(st.lists(st.one_of(LIBRE, st.sampled_from(["[[CITA:FICT-0001]]", "[[CITA_AJENA:1a./J. 45/2019 (10a.)|exp/a.md]]", "[[NO_VERIFICADO:registro digital 2012345]]"]),
                          st.sampled_from(A_MANO)), max_size=12))
def test_alarma_un_patron_de_cita_fuera_de_marcador_impide_ensamblar(fragmentos):
    # Dentro de un marcador el patrón es legítimo (la cita ajena o la afirmación no verificada lo llevan a propósito).
    assert bool(procedencia.citas_fuera_de_marcadores("".join(fragmentos))) == any(f in A_MANO for f in fragmentos)


# ---------------------------------------------------------------- ensamblado desde la evidencia (I-9)

@PROPIEDADES
@given(st.data())
def test_cada_cita_del_entregable_es_exactamente_la_de_su_evidencia(datos):
    almacen = datos.draw(evidencias())
    borrador, pedidas = datos.draw(borradores(almacen))
    r = ensamblar(borrador, almacen)
    assert not r.errores
    citas_ = [t for t in r.tramos if t.tipo == "CITA"]
    assert [(t.registro, t.forma) for t in citas_] == pedidas
    numeracion = {}
    for tramo in citas_:
        numeracion.setdefault(tramo.registro, len(numeracion) + 1)
        oficial = json.loads(almacen[tramo.registro]["datos_oficiales"])
        texto = r.texto[tramo.inicio:tramo.fin]
        assert texto == procedencia.formatear(oficial, tramo.forma, f"[^ev{numeracion[tramo.registro]}]")
        if tramo.forma in ("completa", "rubro"):
            assert f"«{oficial['rubro']}»" in texto
        if tramo.forma in ("completa", "clave"):
            assert oficial["clave"] in texto
        assert tramo.sha256_evidencia == almacen[tramo.registro]["sha256_resultado"]


@PROPIEDADES
@given(st.data())
def test_sin_evidencia_no_hay_documento(datos):
    almacen = datos.draw(evidencias())
    borrador, pedidas = datos.draw(borradores(almacen))
    if not pedidas:
        return
    faltante = datos.draw(st.sampled_from(sorted({r for r, _ in pedidas})))
    r = ensamblar(borrador, {k: v for k, v in almacen.items() if k != faltante})
    assert r.errores and r.texto == "" and not r.tramos and faltante in r.pendientes


def test_pendientes_permitidos_dan_un_borrador_no_entregable():
    r = ensamblar("Aplica [[CITA:FICT-0099]].", {}, permitir_pendientes=True)
    manifiesto = procedencia.manifiesto(r.texto, "x", r, "prueba")
    assert r.texto and manifiesto["entregable"] is False
    assert any("pendientes" in p for p in procedencia.verificar_entrega(r.texto.encode("utf-8"), manifiesto))
    # Declararlo entregable a mano no lo vuelve entregable: el manifiesto queda inconsistente.
    manifiesto["entregable"] = True
    assert any("inconsistente" in p for p in procedencia.verificar_entrega(r.texto.encode("utf-8"), manifiesto))


# ---------------------------------------------------------------- citas ajenas: verificables contra su fuente (A1-4)

@PROPIEDADES
@given(LIBRE.filter(str.strip), LIBRE, st.booleans())
def test_cita_ajena_solo_si_aparece_literal_en_la_fuente(referencia, resto, presente):
    fuente = (resto + referencia.upper() + resto) if presente else resto.replace(referencia.strip(), "")
    r = ensamblar(f"La autoridad cita [[CITA_AJENA:{referencia}|exp/acto.md]].", {}, {"exp/acto.md": (fuente, procedencia.sha256(fuente))})
    aparece = procedencia._comparable(referencia) in procedencia._comparable(fuente)
    assert (not r.errores) == aparece
    if aparece:
        (tramo,) = [t for t in r.tramos if t.tipo == "CITA_AJENA"]
        assert "⚠ CITA NO VERIFICADA" in r.texto[tramo.inicio:tramo.fin] and tramo.sha256_fuente == procedencia.sha256(fuente)


def test_cita_ajena_con_fuente_inexistente_falla():
    assert ensamblar("Cita [[CITA_AJENA:1a./J. 45/2019 (10a.)|exp/no-existe.md]].", {}).errores


# ---------------------------------------------------------------- entrega y procedencia (I-8, I-10, A1-5)

@PROPIEDADES
@given(st.data())
def test_el_entregable_se_verifica_y_cualquier_cambio_lo_invalida(datos):
    almacen = datos.draw(evidencias())
    fuentes = {"exp/acto.md": ("La autoridad invoca la 1a./J. 45/2019 (10a.) sin más.", procedencia.sha256("acto"))}
    borrador, _ = datos.draw(borradores(almacen, fuentes))
    r = ensamblar(borrador, almacen, fuentes)
    documento = r.texto.encode("utf-8")
    manifiesto = procedencia.manifiesto(r.texto, borrador, r, "prueba")
    assert procedencia.verificar_entrega(documento, manifiesto) == []
    posicion = datos.draw(st.integers(0, len(documento) - 1))
    alterado = documento[:posicion] + bytes([(documento[posicion] + 1) % 256]) + documento[posicion + 1:]
    assert procedencia.verificar_entrega(alterado, manifiesto)


@PROPIEDADES
@given(st.data())
def test_una_cita_a_mano_se_detecta_aunque_se_rehaga_la_huella(datos):
    almacen = datos.draw(evidencias())
    borrador, _ = datos.draw(borradores(almacen))
    r = ensamblar(borrador, almacen)
    insercion = datos.draw(st.sampled_from(A_MANO)) + " "
    # Un manifiesto rehecho a mano: huella del documento nueva y tramos corridos. El texto agregado no es de un tramo.
    texto = insercion + r.texto
    manifiesto = procedencia.manifiesto(r.texto, borrador, r, "prueba")
    manifiesto["sha256_documento"] = procedencia.sha256(texto)
    for tramo in manifiesto["tramos"]:
        tramo["inicio"] += len(insercion)
        tramo["fin"] += len(insercion)
    problemas = procedencia.verificar_entrega(texto.encode("utf-8"), manifiesto)
    assert any("fuera de los tramos" in p for p in problemas)


@PROPIEDADES
@given(st.data())
def test_editar_dentro_de_un_tramo_se_detecta_aunque_se_rehaga_la_huella(datos):
    # La revisión de patrones no ve un rubro alterado DENTRO de un tramo de cita: lo detecta la huella de cada tramo.
    almacen = datos.draw(evidencias())
    borrador, pedidas = datos.draw(borradores(almacen))
    r = ensamblar(borrador, almacen)
    citas_ = [t for t in r.tramos if t.tipo == "CITA"]
    if not citas_:
        return
    tramo = datos.draw(st.sampled_from(citas_))
    posicion = datos.draw(st.integers(tramo.inicio, tramo.fin - 1))
    texto = r.texto[:posicion] + ("X" if r.texto[posicion] != "X" else "Y") + r.texto[posicion + 1:]
    manifiesto = procedencia.manifiesto(r.texto, borrador, r, "prueba")
    manifiesto["sha256_documento"] = procedencia.sha256(texto)
    assert any("tramo" in p for p in procedencia.verificar_entrega(texto.encode("utf-8"), manifiesto))


@PROPIEDADES
@given(st.data())
def test_las_marcas_de_verificacion_solo_las_escribe_el_ensamblador(datos):
    almacen = datos.draw(evidencias())
    fuentes = {"exp/acto.md": ("cita 1a./J. 45/2019 (10a.)", "h")}
    borrador, _ = datos.draw(borradores(almacen, fuentes))
    r = ensamblar(borrador, almacen, fuentes)
    propios = [(t.inicio, t.fin) for t in r.tramos if t.tipo in {"CITA_AJENA", "NO_VERIFICADO", "CITA_PENDIENTE", "NOTAS"}]
    for m in procedencia._ALARMA[-1][1].finditer(r.texto):
        assert any(a <= m.start() and m.end() <= b for a, b in propios)


def test_un_marcador_sin_resolver_nunca_es_entregable():
    """Aunque un manifiesto se rehaga a mano para cubrirlo, un «[[» en el documento final es BLOCKED."""
    import dataclasses

    r = ensamblar("Texto con [[NO_VERIFICADO:un dato]].", {})
    texto = r.texto + "[[CITA:FICT-0001]]"
    falso = procedencia.Ensamblado(texto=texto, tramos=r.tramos[:-1] + [dataclasses.replace(r.tramos[-1], fin=len(texto))])
    manifiesto = procedencia.manifiesto(texto, "x", falso, "prueba")
    assert any("sin resolver" in p for p in procedencia.verificar_entrega(texto.encode("utf-8"), manifiesto))


@pytest.mark.parametrize("manifiesto", [None, [], {}, {"contrato": "otro"}, {"contrato": procedencia.CONTRATO}])
def test_sin_manifiesto_valido_no_es_entregable(manifiesto):
    assert procedencia.verificar_entrega(b"texto sin citas", manifiesto)


# ---------------------------------------------------------------- CR-1.2: manifiesto estricto y reverificación

FUENTE_ACTO = "La autoridad invoca la 1a./J. 45/2019 (10a.) sin más."
FUENTES = {"exp/acto.md": (FUENTE_ACTO, procedencia.sha256(FUENTE_ACTO))}


def contexto(almacen, fuentes=FUENTES):
    return procedencia.Contexto(almacen.get, fuentes.get)


@PROPIEDADES
@given(st.data())
def test_los_marcadores_internos_nunca_aparecen_en_el_entregable(datos):
    almacen = datos.draw(evidencias())
    borrador, _ = datos.draw(borradores(almacen, FUENTES))
    texto = ensamblar(borrador, almacen, FUENTES).texto
    assert "[[" not in texto and "]]" not in texto
    assert not any(f"{tipo}:" in texto for tipo in ("CITA", "CITA_AJENA", "NO_VERIFICADO"))


@PROPIEDADES
@given(st.data())
def test_quitar_o_agregar_cualquier_campo_del_manifiesto_es_blocked(datos):
    almacen = datos.draw(evidencias())
    borrador, _ = datos.draw(borradores(almacen, FUENTES))
    r = ensamblar(borrador, almacen, FUENTES)
    documento = r.texto.encode("utf-8")
    base = procedencia.manifiesto(r.texto, borrador, r, "prueba")
    assert procedencia.verificar_entrega(documento, base, contexto(almacen)) == []
    rutas = [(clave,) for clave in base] + [("tramos", i, clave) for i, tramo in enumerate(base["tramos"]) for clave in tramo]
    for ruta in rutas:
        roto = json.loads(json.dumps(base))
        padre = roto
        for paso in ruta[:-1]:
            padre = padre[paso]
        del padre[ruta[-1]]
        assert procedencia.verificar_entrega(documento, roto, contexto(almacen)), ruta
    for destino in [lambda m: m, lambda m: m["tramos"][datos.draw(st.integers(0, len(m["tramos"]) - 1))]]:
        roto = json.loads(json.dumps(base))
        destino(roto)["campo_ajeno"] = 1
        assert procedencia.verificar_entrega(documento, roto, contexto(almacen))
    # Omitir un tramo entero (de cualquier tipo, incluida una cita en forma «rubro», cuyo texto no dispara la alarma).
    for i in range(len(base["tramos"])):
        roto = json.loads(json.dumps(base))
        del roto["tramos"][i]
        assert procedencia.verificar_entrega(documento, roto, contexto(almacen)), base["tramos"][i]["tipo"]


JSON_ARBITRARIO = st.recursive(st.none() | st.booleans() | st.integers(-5, 10**6) | st.floats(allow_nan=False) | st.text(max_size=10),
                               lambda hijos: st.lists(hijos, max_size=4) | st.dictionaries(st.text(max_size=10), hijos, max_size=4), max_leaves=20)


@PROPIEDADES
@given(st.data())
def test_ningun_manifiesto_hace_lanzar_a_la_comprobacion(datos):
    """Un manifiesto arbitrario, o uno válido con un valor cualquiera reemplazado por JSON arbitrario, nunca produce una
    excepción: produce BLOCKED (salvo que el reemplazo deje el mismo valor)."""
    almacen = datos.draw(evidencias())
    borrador, _ = datos.draw(borradores(almacen, FUENTES))
    r = ensamblar(borrador, almacen, FUENTES)
    documento = r.texto.encode("utf-8")
    assert procedencia.verificar_entrega(documento, datos.draw(JSON_ARBITRARIO), contexto(almacen))
    base = procedencia.manifiesto(r.texto, borrador, r, "prueba")
    rutas = [(clave,) for clave in base] + [("tramos", i, clave) for i, tramo in enumerate(base["tramos"]) for clave in tramo]
    ruta = datos.draw(st.sampled_from(rutas))
    roto = json.loads(json.dumps(base))
    padre = roto
    for paso in ruta[:-1]:
        padre = padre[paso]
    valor = datos.draw(JSON_ARBITRARIO)
    padre[ruta[-1]] = valor
    resultado = procedencia.verificar_entrega(documento, roto, contexto(almacen))
    # Única excepción legítima: version_plugin es informativo (cualquier texto vale).
    assert isinstance(resultado, list) and (resultado or roto == base or (ruta == ("version_plugin",) and isinstance(valor, str)))


@PROPIEDADES
@given(st.data(), st.sampled_from(["retirada", "otra", "contenido"]))
def test_la_entrega_se_reverifica_contra_la_evidencia_viva(datos, cambio):
    almacen = datos.draw(evidencias())
    borrador, pedidas = datos.draw(borradores(almacen))
    if not pedidas:
        return
    r = ensamblar(borrador, almacen)
    documento, manifiesto = r.texto.encode("utf-8"), procedencia.manifiesto(r.texto, borrador, r, "prueba")
    registro = datos.draw(st.sampled_from(sorted({reg for reg, _ in pedidas})))
    vivo = dict(almacen)
    if cambio == "retirada":  # venció o se invalidó después de ensamblar
        del vivo[registro]
    elif cambio == "otra":  # hay una evidencia vigente distinta de la que se usó
        vivo[registro] = dict(almacen[registro], sha256_resultado="f" * 64)
    else:  # misma huella declarada, datos oficiales distintos: el texto ya no es el de su evidencia
        oficial = json.loads(almacen[registro]["datos_oficiales"])
        vivo[registro] = dict(almacen[registro], datos_oficiales=json.dumps(dict(oficial, rubro=oficial["rubro"] + " X", clave=oficial["clave"] + "X", registro=registro + "Z")))
    assert procedencia.verificar_entrega(documento, manifiesto, contexto(almacen)) == []
    assert procedencia.verificar_entrega(documento, manifiesto, contexto(vivo))


@pytest.mark.parametrize("cambio", ["fuente_cambiada", "fuente_ausente", "referencia_que_ya_no_esta"])
def test_la_cita_ajena_conserva_su_procedencia_literal(cambio):
    borrador = "La autoridad invoca [[CITA_AJENA:1a./J. 45/2019 (10a.)|exp/acto.md]]."
    r = ensamblar(borrador, {}, FUENTES)
    documento, manifiesto = r.texto.encode("utf-8"), procedencia.manifiesto(r.texto, borrador, r, "prueba")
    assert procedencia.verificar_entrega(documento, manifiesto, contexto({})) == []
    if cambio == "fuente_cambiada":
        vivas = {"exp/acto.md": (FUENTE_ACTO + " Adición.", procedencia.sha256(FUENTE_ACTO + " Adición."))}
    elif cambio == "fuente_ausente":
        vivas = {}
    else:  # la misma huella declarada, pero el texto vivo ya no contiene la referencia
        vivas = {"exp/acto.md": ("La autoridad no invoca nada.", procedencia.sha256(FUENTE_ACTO))}
    assert procedencia.verificar_entrega(documento, manifiesto, contexto({}, vivas))
