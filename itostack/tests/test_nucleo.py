"""Núcleo determinista: normalización, contrato de veredictos, contexto, citas y evidencia."""

import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from nucleo import citas, contexto, normalizacion as norm, veredicto
from nucleo.config import CONFIG_DEFECTO
from nucleo.evidencia import AlmacenEvidencia, sha256_resultado

OFICIAL = {
    "registro": "2099999", "rubro": "PRISIÓN PREVENTIVA OFICIOSA. SU REVISIÓN PERIÓDICA ES OBLIGATORIA.",
    "clave": "PR.P.CN. J/9 P (12a.)", "epoca": "Duodécima Época", "instancia": "Pleno Regional en Materia Penal",
    "tipo": "Jurisprudencia", "fecha_publicacion": "2025-11-07", "materia": "Penal",
}


def captura(**cambios):
    base = {
        "consultado": True, "portal_disponible": True, "no_encontrado": False, "estructura_reconocida": True,
        "datos_oficiales": dict(OFICIAL), "visitas": [{"archivos": [{"tipo": "captura", "sha256": "ab" * 32, "ruta": "/x.png"}]}],
    }
    base.update(cambios)
    return base


class TestNormalizacion:
    def test_variaciones_tipograficas(self):
        assert norm.normalizar_texto("  “Prisión  preventiva.”  ") == norm.normalizar_texto('PRISION PREVENTIVA')

    def test_clave_sin_espacios(self):
        assert norm.normalizar_clave("1a./J. 45/2019 (10a.)") == norm.normalizar_clave("1a./J.45/2019(10a.)")

    @pytest.mark.parametrize("texto,numero", [("Undécima Época", 11), ("Décima Época", 10), ("(12a.)", 12), ("Novena", 9), ("Duodécima", 12)])
    def test_epocas(self, texto, numero):
        assert norm.epoca_a_numero(texto) == numero

    @pytest.mark.parametrize("texto,iso", [("2025-11-07", "2025-11-07"), ("07/11/2025", "2025-11-07"), ("viernes 7 de noviembre de 2025", "2025-11-07")])
    def test_fechas(self, texto, iso):
        assert norm.parsear_fecha(texto).isoformat() == iso


class TestVeredicto:
    def test_pass_con_cotejo(self):
        r = veredicto.decidir_tesis({"registro": "2099999", "rubro": OFICIAL["rubro"].lower(), "clave": OFICIAL["clave"]}, captura())
        assert r.veredicto == "PASS" and r.vvca["auditable"]

    def test_un_rubro_discrepante_basta_para_fail(self):
        r = veredicto.decidir_tesis({"registro": "2099999", "rubro": "PRISIÓN PREVENTIVA OFICIOSA. SU REVISIÓN PERIÓDICA ES OPCIONAL."}, captura())
        assert r.veredicto == "FAIL" and "rubro" in r.motivo

    def test_sin_captura_no_hay_pass(self):
        r = veredicto.decidir_tesis({"registro": "2099999", "rubro": OFICIAL["rubro"]}, captura(visitas=[]))
        assert r.veredicto == "BLOCKED"

    def test_portal_caido_es_blocked_no_fail(self):
        assert veredicto.decidir_tesis({"registro": "1", "rubro": "x"}, captura(portal_disponible=False)).veredicto == "BLOCKED"

    def test_inexistente_es_fail(self):
        assert veredicto.decidir_tesis({"registro": "1", "rubro": "x"}, captura(no_encontrado=True)).veredicto == "FAIL"

    def test_estructura_desconocida_es_blocked(self):
        assert veredicto.decidir_tesis({"registro": "1", "rubro": "x"}, captura(estructura_reconocida=False)).veredicto == "BLOCKED"

    def test_otro_registro_es_fail(self):
        assert veredicto.decidir_tesis({"registro": "2000000", "rubro": OFICIAL["rubro"]}, captura()).veredicto == "FAIL"

    def test_nada_que_cotejar(self):
        assert veredicto.decidir_tesis({"registro": "2099999"}, captura()).veredicto == "BLOCKED"
        assert veredicto.decidir_tesis({"registro": "2099999"}, captura(), modo="existencia").veredicto == "PASS"

    def test_campo_menor_sin_confirmar_es_advertencia(self):
        oficial = dict(OFICIAL)
        oficial.pop("fecha_publicacion")
        r = veredicto.decidir_tesis({"registro": "2099999", "rubro": OFICIAL["rubro"], "fecha_publicacion": "2025-11-07"}, captura(datos_oficiales=oficial))
        assert r.veredicto == "PASS" and r.advertencias

    def test_veredicto_invalido(self):
        with pytest.raises(ValueError):
            veredicto.Resultado("CASI", "x")

    def test_app(self):
        base = {"app_alcanzable": True, "visitas": captura()["visitas"], "pasos": [{"indice": 1, "accion": "clic", "fallo": "selector_ausente", "selector": "#x"}]}
        assert veredicto.decidir_app(base).veredicto == "BLOCKED"
        base["pasos"] = [{"indice": 1, "accion": "esperar_texto", "fallo": "expectativa", "detalle": "no apareció"}]
        assert veredicto.decidir_app(base).veredicto == "FAIL"
        base["pasos"] = [{"indice": 1, "accion": "ir", "fallo": None}]
        assert veredicto.decidir_app(base).veredicto == "PASS"
        assert veredicto.decidir_app({**base, "app_alcanzable": False}).veredicto == "BLOCKED"


class TestContexto:
    def test_sala_extinta_y_cortes(self):
        avisos = contexto.advertencias_tesis(
            {"instancia": "Segunda Sala", "epoca": "Décima Época", "fecha_publicacion": "2019-03-15", "tipo": "Jurisprudencia", "materia": "Común"},
            CONFIG_DEFECTO,
        )
        texto = " ".join(avisos)
        assert "Sala extinta" in texto and "reforma judicial" in texto and "Ley de Amparo" in texto

    def test_criterio_reciente_sin_avisos(self):
        assert contexto.advertencias_tesis(OFICIAL, CONFIG_DEFECTO) == []

    def test_aislada_orientadora(self):
        assert any("orientador" in a for a in contexto.advertencias_tesis({**OFICIAL, "tipo": "Aislada"}, CONFIG_DEFECTO))


class TestCitas:
    TEXTO = (
        "Es aplicable la jurisprudencia 1a./J. 45/2019 (10a.), registro digital 2020123, de rubro: \"UN RUBRO DE PRUEBA SUFICIENTEMENTE LARGO.\"\n"
        "También [[CITA:2099999|rubro]].\n"
        "Cita ajena ❌: registro digital 1999999.\n"
    )

    def test_extrae_registro_clave_y_marcador(self):
        tipos = {(c.tipo, c.valor) for c in citas.extraer(self.TEXTO)}
        assert ("registro", "2020123") in tipos and ("marcador", "2099999") in tipos
        assert any(t == "clave" and "45/2019" in v for t, v in tipos)

    def test_marcada_no_verificada(self):
        marcada = [c for c in citas.extraer(self.TEXTO) if c.valor == "1999999"][0]
        assert marcada.marcada_no_verificada

    def test_claves_diversas(self):
        for clave in ("P./J. 12/2020 (10a.)", "2a. XXI/2018 (10a.)", "I.1o.P.45 P (10a.)", "PR.P.CN. J/5 P (11a.)", "XVII.2o.C.T. J/3 (9a.)"):
            assert any(c.tipo == "clave" for c in citas.extraer(f"Véase la tesis {clave} aplicable.")), clave

    def test_agrupa_rubro(self):
        referencia = citas.agrupar_referencias(self.TEXTO)[0]
        assert referencia.registro == "2020123" and referencia.rubro.startswith("UN RUBRO DE PRUEBA")


class TestEvidencia:
    def _resultado(self, tmp_path, veredicto_="PASS", modo="real", hace_dias=0):
        png = tmp_path / "c.png"
        png.write_bytes(b"\x89PNG prueba")
        import hashlib

        resultado = {
            "tipo": "tesis", "identificador": "2099999", "veredicto": veredicto_, "motivo": "m", "modo_fuente": modo,
            "datos_citados": {}, "datos_oficiales": OFICIAL, "advertencias": [],
            "visitas": [{"archivos": [{"tipo": "captura", "ruta": str(png), "sha256": hashlib.sha256(png.read_bytes()).hexdigest()}]}],
            "marca_tiempo": (datetime.now(timezone.utc) - timedelta(days=hace_dias)).isoformat(), "herramienta": "t",
        }
        resultado["sha256_resultado"] = sha256_resultado(resultado)
        ruta = tmp_path / f"r-{veredicto_}-{modo}-{hace_dias}.json"
        ruta.write_text(json.dumps(resultado), encoding="utf-8")
        return resultado, ruta

    def test_vigente_e_inmutable(self, tmp_path):
        almacen = AlmacenEvidencia(tmp_path / "e.db")
        almacen.registrar(*self._resultado(tmp_path))
        assert almacen.vigente("tesis", "2099999", 30)
        assert almacen.vigente_por_clave("PR.P.CN.  J/9 P (12a.)", 30)
        with sqlite3.connect(tmp_path / "e.db") as conexion, pytest.raises(sqlite3.DatabaseError):
            conexion.execute("UPDATE verificaciones SET veredicto = 'PASS'")
        with sqlite3.connect(tmp_path / "e.db") as conexion, pytest.raises(sqlite3.DatabaseError):
            conexion.execute("DELETE FROM verificaciones")

    def test_caducidad_fixture_y_alteracion(self, tmp_path):
        almacen = AlmacenEvidencia(tmp_path / "e.db")
        almacen.registrar(*self._resultado(tmp_path, hace_dias=40))
        assert almacen.vigente("tesis", "2099999", 30) is None
        almacen2 = AlmacenEvidencia(tmp_path / "f.db")
        almacen2.registrar(*self._resultado(tmp_path, modo="fixture"))
        assert almacen2.vigente("tesis", "2099999", 30) is None
        assert almacen2.vigente("tesis", "2099999", 30, ("real", "fixture"))
        (tmp_path / "c.png").write_bytes(b"alterada")
        assert almacen2.vigente("tesis", "2099999", 30, ("real", "fixture")) is None
        assert almacen2.auditar()

    def test_ultimo_fail_anula_pass_previo(self, tmp_path):
        almacen = AlmacenEvidencia(tmp_path / "e.db")
        almacen.registrar(*self._resultado(tmp_path, hace_dias=1))
        almacen.registrar(*self._resultado(tmp_path, veredicto_="FAIL"))
        assert almacen.vigente("tesis", "2099999", 30) is None
