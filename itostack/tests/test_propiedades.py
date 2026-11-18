"""Verificación por propiedades (Hypothesis) y exploración exhaustiva del contrato de veredictos.

Es el análogo práctico de la verificación formal del texto fuente: en lugar de TLA+/Lean, se exploran
todas las combinaciones de estado del pipeline y se comprueban invariantes que nunca deben romperse.
"""

import itertools

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st  # noqa: E402

from nucleo import citas, normalizacion as norm, veredicto  # noqa: E402

LETRAS = st.text(alphabet="ABCDEFGHIJKLMNÑOPQRSTUVWXYZÁÉÍÓÚ ., ", min_size=5, max_size=120)


@given(LETRAS)
def test_normalizar_es_idempotente(texto):
    assert norm.normalizar_texto(norm.normalizar_texto(texto)) == norm.normalizar_texto(texto)


@given(LETRAS, st.sampled_from(["  ", "\n", "\t "]), st.booleans())
def test_variaciones_tipograficas_no_cambian_el_cotejo(texto, espacio, minusculas):
    variante = espacio.join(texto.split())
    variante = variante.lower() if minusculas else variante
    if norm.normalizar_texto(texto):
        assert norm.cotejar_rubro(variante, texto).estado in {"coincide", "tipografica"}


@settings(max_examples=300)
@given(st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ ", min_size=10, max_size=80), st.data())
def test_cambiar_una_letra_es_discrepancia(texto, datos):
    posiciones = [i for i, c in enumerate(texto) if c.isalpha()]
    if not posiciones:
        return
    i = datos.draw(st.sampled_from(posiciones))
    otra = datos.draw(st.sampled_from([c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if c != texto[i]]))
    alterado = texto[:i] + otra + texto[i + 1:]
    assert norm.cotejar_rubro(alterado, texto).estado == "discrepante"


@given(st.text(max_size=200), st.integers(min_value=100000, max_value=9999999))
def test_registro_insertado_siempre_se_detecta(ruido, registro):
    texto = f"{ruido}\nregistro digital {registro}\n"
    assert any(c.tipo == "registro" and c.valor == str(registro) for c in citas.extraer(texto))


@given(st.text(alphabet="abcdefghij ,.;:\n", max_size=300))
def test_texto_sin_digitos_no_tiene_registros(texto):
    assert not [c for c in citas.extraer(texto) if c.tipo == "registro"]


def test_exploracion_exhaustiva_del_contrato():
    """Ningún estado del pipeline produce PASS sin evidencia, portal, estructura y coincidencia."""
    oficial = {"registro": "2099999", "rubro": "RUBRO OFICIAL DE PRUEBA", "clave": "P./J. 1/2025 (12a.)"}
    rubros = {"igual": oficial["rubro"], "tipografico": "rubro oficial de prueba.", "distinto": "RUBRO OFICIAL DE PRUEBAS", "ausente": None}
    for consultado, captura_ok, portal, no_encontrado, estructura, rubro, modo in itertools.product(
        [True, False], [True, False], [True, False], [True, False], [True, False], rubros, ["cotejo", "existencia"]
    ):
        captura = {
            "consultado": consultado, "portal_disponible": portal, "no_encontrado": no_encontrado, "estructura_reconocida": estructura,
            "datos_oficiales": oficial, "visitas": [{"archivos": [{"tipo": "captura", "sha256": "f" * 64}]}] if captura_ok else [],
        }
        citado = {"registro": "2099999"}
        if rubros[rubro]:
            citado["rubro"] = rubros[rubro]
        r = veredicto.decidir_tesis(citado, captura, modo)
        if r.veredicto == "PASS":
            assert consultado and captura_ok and portal and not no_encontrado and estructura
            assert modo == "existencia" or rubro in {"igual", "tipografico"}
        if r.veredicto == "FAIL":
            assert consultado and captura_ok and portal, "FAIL exige evidencia positiva"
        if not (consultado and captura_ok):
            assert r.veredicto == "BLOCKED"
