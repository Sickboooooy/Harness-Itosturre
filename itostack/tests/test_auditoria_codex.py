"""Regresiones de la auditoría cruzada con Codex (0.1.2): juez de otra familia, compuerta holdout, D-04, N-01, B-02,
N-07, N-08, D-10, D-17 y los hallazgos de las revisiones adversariales de Codex sobre el propio diff. Cada prueba falla
con el defecto y pasa con la corrección."""

import http.server
import json
import os
import shutil
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

import pytest
from hypothesis import HealthCheck, event, given, settings, strategies as st

from conftest import RAIZ, SCRIPTS, correr_hook, decision, requiere_navegador, verificar
from nucleo import citas, juez

RUBRO_0001 = "CRITERIO FICTICIO DE PRUEBA. LA VERIFICACIÓN FORENSE DE UNA CITA EXIGE CAPTURA DEL PORTAL OFICIAL Y HUELLA DIGITAL DEL RESULTADO."
RUBRICA_VERIFICACION = RAIZ / "evals" / "rubricas" / "verificacion.md"


def criterio(cumple="si", evidencia="«cita textual»", numero=None):
    datos = {"criterio": "c", "cumple": cumple, "evidencia": evidencia}
    if numero is not None:
        datos["numero"] = numero
    return datos


def numerados(*valores, evidencia="«cita textual»"):
    return [criterio(v, evidencia, i) for i, v in enumerate(valores, 1)]


def respuesta(criterios, fallos=(), **extra):
    """Respuesta completa del modelo según el esquema del juez (sin valores por omisión)."""
    return {"criterios": criterios, "fallos_criticos": list(fallos), "observaciones": "", **extra}


ARTEFACTO = "el artefacto contiene la cita textual que el juez señala"


# ---------------------------------------------------------------- D-17: el puntaje lo calcula el programa

class TestContratoJuez:
    def test_no_aplicable_no_cuenta_ni_como_cumplido_ni_como_fallado(self):
        r = juez.calificar(respuesta(numerados("si", "si", "si", "si", "si", "no_aplicable"), puntaje=3), 6, ARTEFACTO)
        assert (r["puntaje"], r["aplicables"], r["no_aplicables"], r["aprobado"]) == (10.0, 5, 1, True)

    def test_un_no_impide_aprobar(self):
        r = juez.calificar(respuesta(numerados("si", "no")), 2, ARTEFACTO)
        assert r["puntaje"] == 5.0 and not r["aprobado"] and juez.codigo_salida("juez", r) == 1

    def test_fallo_critico_es_cero_aunque_el_modelo_diga_diez(self):
        r = juez.calificar(respuesta(numerados("si"), ["rubro escrito a mano"], puntaje=10), 1, ARTEFACTO)
        assert r["puntaje"] == 0.0 and not r["aprobado"]

    def test_nada_aplicable_es_blocked_no_pass(self):
        r = juez.calificar(respuesta(numerados("no_aplicable")), 1)
        assert r["puntaje"] is None and juez.codigo_salida("juez", r) == 2

    def test_omitir_criterios_no_sube_la_nota(self):
        r = juez.calificar(respuesta(numerados("si")), 6, ARTEFACTO)
        assert r["puntaje"] is None and not r["aprobado"] and juez.codigo_salida("juez", r) == 2

    def test_repetir_un_criterio_no_cubre_los_demas(self):
        r = juez.calificar(respuesta([criterio(numero=1)] * 5), 5, ARTEFACTO)
        assert r["puntaje"] is None and not r["aprobado"]
        sin_numero = juez.calificar(respuesta([criterio()] * 5), 5, ARTEFACTO)
        assert sin_numero["puntaje"] is None and sin_numero["contrato"]

    def test_si_sin_evidencia_cuenta_como_no(self):
        r = juez.calificar(respuesta([criterio("si", "", 1), criterio(numero=2)]), 2, ARTEFACTO)
        assert r["criterios"][0]["cumple"] == "no" and not r["aprobado"]

    def test_evidencia_inventada_cuenta_como_no(self):
        r = juez.calificar(respuesta([criterio("si", "«frase que el documento no contiene»", 1)]), 1, "el documento dice otra cosa")
        assert r["criterios"][0]["cumple"] == "no" and r["criterios"][0]["evidencia_verificada"] is False and not r["aprobado"]
        # La compuerta, sin el artefacto, respeta la anotación del revisor.
        assert not juez.calificar(r, 1)["aprobado"]

    def test_evidencia_literal_con_formato_y_elision(self):
        artefacto = "| c01 | **FICT-0001** | ✅ VERIFICADO |\nConclusión: «Citas verificadas (PASS): 1.» y nada más."
        assert juez.evidencia_en_artefacto("La matriz dice «| c01 | FICT-0001 | ✅ VERIFICADO»", artefacto)
        assert juez.evidencia_en_artefacto("«Conclusión: … Citas verificadas (PASS): 1.»", artefacto)
        assert not juez.evidencia_en_artefacto("sin comillas: Citas verificadas (PASS): 1.", artefacto)

    @pytest.mark.parametrize("cumple", [True, False, "sí", "SI", "true", "n/a", ["raro"], None])
    def test_valores_fuera_del_esquema_son_blocked(self, cumple):
        # Antes un booleano o «sí» se leía como «si» y podía aprobar: ahora ningún valor fuera del enum se interpreta.
        r = juez.calificar(respuesta([criterio(cumple, numero=1)]), 1, ARTEFACTO)
        assert r["puntaje"] is None and not r["aprobado"] and r["contrato"] and juez.codigo_salida("juez", r) == 2

    def test_criterios_de_las_rubricas_congeladas(self):
        cuentas = {r.name: len(juez.criterios_de_rubrica(r.read_text(encoding="utf-8"))) for r in (RAIZ / "evals" / "rubricas").glob("*.md")}
        assert cuentas == {"escrito-con-citas.md": 6, "informe-vvca.md": 6, "verificacion.md": 5}

    def test_material_excedido_no_se_recorta(self):
        with pytest.raises(juez.MaterialExcedido):
            juez.armar_prompt("adversarial", "x" * 101, None, 100)

    def test_instantanea_una_sola_lectura(self, tmp_path):
        archivo = tmp_path / "a.md"
        archivo.write_bytes(b"version uno")
        texto, huellas = juez.instantanea([archivo], "")
        archivo.write_bytes(b"version dos")
        assert "version uno" in texto and huellas == [juez.sha256(b"version uno")]

    @pytest.mark.parametrize("modelo", ["claude-sonnet-5-5", "opus", "Haiku", "anthropic/x", "fable"])
    def test_familia_claude(self, modelo):
        assert juez.es_familia_claude(modelo)

    def test_otra_familia(self):
        assert not juez.es_familia_claude("gpt-6.1-sol") and not juez.es_familia_claude("qwen2.5:14b")


# ---------------------------------------------------------------- revisar_codex.py y revisar_ollama.py

CODEX_FALSO = textwrap.dedent('''
    import json, os, sys
    argv = sys.argv[1:]
    if argv == ["--version"]:
        print("codex-cli prueba"); sys.exit(0)
    prompt = sys.stdin.read()
    registro = {"argv": argv, "cwd": os.getcwd(), "listado": os.listdir(os.getcwd()), "prompt": prompt}
    open(os.environ["CODEX_FALSO_REGISTRO"], "w", encoding="utf-8").write(json.dumps(registro))
    salida = argv[argv.index("-o") + 1]
    open(salida, "w", encoding="utf-8").write(os.environ["CODEX_FALSO_RESPUESTA"])
''')


def correr_codex(proyecto, tmp_path, respuesta, *argumentos: str):
    falso = tmp_path / "codex_falso.py"
    falso.write_text(CODEX_FALSO, encoding="utf-8")
    entorno = {**os.environ, "ITOSTACK_CODEX": str(falso), "CODEX_FALSO_RESPUESTA": respuesta if isinstance(respuesta, str) else json.dumps(respuesta),
               "CODEX_FALSO_REGISTRO": str(tmp_path / "registro.json"), "PYTHONUTF8": "1"}
    entorno.pop("ITOSTACK_PROYECTO", None)
    return subprocess.run([sys.executable, str(SCRIPTS / "revisar_codex.py"), *argumentos], cwd=proyecto, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", env=entorno, timeout=120)


def declarar_entorno(proyecto, entorno: str):
    ruta = proyecto / ".itostack" / "config.json"
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    datos["entorno"] = entorno
    ruta.write_text(json.dumps(datos), encoding="utf-8")


class TestRevisarCodex:
    APROBADO = {"criterios": [criterio("si", "«contenido del informe»", 1), criterio("no_aplicable", "sin ocasión", 2)], "fallos_criticos": [], "observaciones": ""}

    def _artefactos(self, tmp_path, rubrica=b"1. algo\n2. otra cosa\n\nFallos criticos: ninguno\n"):
        carpeta = tmp_path / "evals" / "verificar-cita" / "holdout-secreto"
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / "informe.md").write_text("contenido del informe", encoding="utf-8")
        (tmp_path / "rubrica.md").write_bytes(rubrica)
        return carpeta / "informe.md", tmp_path / "rubrica.md"

    def _juez(self, proyecto, tmp_path, respuesta, *extra, **kw):
        declarar_entorno(proyecto, "desarrollo")
        artefacto, rubrica = self._artefactos(tmp_path, **kw)
        return correr_codex(proyecto, tmp_path, respuesta, "--rol", "juez", "--rubrica", str(rubrica), "--archivo", str(artefacto), *extra)

    def test_sin_entorno_desarrollo_se_niega(self, proyecto, tmp_path):
        artefacto, rubrica = self._artefactos(tmp_path)
        salida = correr_codex(proyecto, tmp_path, self.APROBADO, "--rol", "juez", "--rubrica", str(rubrica), "--archivo", str(artefacto))
        assert salida.returncode == 3 and "desarrollo" in salida.stderr
        assert not (tmp_path / "registro.json").exists()

    def test_rechaza_modelo_claude(self, proyecto, tmp_path):
        declarar_entorno(proyecto, "desarrollo")
        artefacto, _ = self._artefactos(tmp_path)
        assert correr_codex(proyecto, tmp_path, self.APROBADO, "--modelo", "claude-opus-5-5", "--archivo", str(artefacto)).returncode == 3

    def test_juez_aislado_sin_herramientas_y_con_puntaje_calculado(self, proyecto, tmp_path):
        salida = self._juez(proyecto, tmp_path, self.APROBADO, "--caso", "verificar-cita.pass-exacto")
        assert salida.returncode == 0, salida.stderr
        resultado = json.loads(salida.stdout)
        assert resultado["puntaje"] == 10.0 and resultado["aprobado"] and resultado["criterios"][0]["evidencia_verificada"]
        assert resultado["juez"]["familia"] == "openai" and resultado["juez"]["modelo"] == "gpt-6.1-sol"
        assert resultado["juez"]["version"] == "codex-cli prueba"
        assert resultado["material"]["rubrica"]["criterios"] == 2 and resultado["material"]["caso"] == "verificar-cita.pass-exacto"
        registro = json.loads((tmp_path / "registro.json").read_text(encoding="utf-8"))
        argv = registro["argv"]
        assert argv[argv.index("-s") + 1] == "read-only"
        assert {"--ephemeral", "--ignore-user-config", "--skip-git-repo-check", "--output-schema"} <= set(argv)
        desactivadas = {argv[i + 1] for i, a in enumerate(argv) if a == "--disable"}
        assert {"shell_tool", "browser_use", "computer_use", "apps", "plugins"} <= desactivadas
        # Directorio neutro y vacío; el artefacto va numerado, sin la ruta que delata el examen.
        assert os.path.basename(registro["cwd"]).startswith("trabajo-") and registro["listado"] == []
        assert "holdout" not in registro["prompt"] and "=== documento 1 ===" in registro["prompt"]
        bitacora = (proyecto / ".itostack" / "bitacora" / "juez.tsv").read_text(encoding="utf-8")
        assert "openai\tcodex\tgpt-6.1-sol\thigh\tcodex-cli prueba\tverificar-cita.pass-exacto" in bitacora

    def test_huella_de_rubrica_crlf_igual_a_la_de_la_compuerta(self, proyecto, tmp_path):
        rubrica = b"1. algo\r\n2. otra cosa\r\n\r\nFallos criticos: ninguno\r\n"
        resultado = json.loads(self._juez(proyecto, tmp_path, self.APROBADO, rubrica=rubrica).stdout)
        assert resultado["material"]["rubrica"]["sha256"] == juez.sha256(rubrica)

    def test_juez_no_aprueba_con_un_criterio_incumplido(self, proyecto, tmp_path):
        respuesta = {"criterios": [criterio("si", "«contenido del informe»", 1), criterio("no", "", 2)], "fallos_criticos": [], "observaciones": ""}
        assert self._juez(proyecto, tmp_path, respuesta).returncode == 1

    def test_evidencia_inventada_por_el_juez_no_aprueba(self, proyecto, tmp_path):
        respuesta = {"criterios": [criterio("si", "«texto que el juez inventó»", 1), criterio("no_aplicable", "x", 2)], "fallos_criticos": [], "observaciones": ""}
        assert self._juez(proyecto, tmp_path, respuesta).returncode == 1

    def test_juez_que_omite_criterios_es_blocked(self, proyecto, tmp_path):
        respuesta = {"criterios": [criterio("si", "«contenido del informe»", 1)], "fallos_criticos": [], "observaciones": ""}
        assert self._juez(proyecto, tmp_path, respuesta).returncode == 2

    def test_respuesta_invalida_es_blocked(self, proyecto, tmp_path):
        declarar_entorno(proyecto, "desarrollo")
        artefacto, _ = self._artefactos(tmp_path)
        assert correr_codex(proyecto, tmp_path, "esto no es json", "--archivo", str(artefacto)).returncode == 2

    def test_material_demasiado_grande_es_blocked(self, proyecto, tmp_path):
        declarar_entorno(proyecto, "desarrollo")
        grande = tmp_path / "grande.md"
        grande.write_text("x" * 150_001, encoding="utf-8")
        salida = correr_codex(proyecto, tmp_path, self.APROBADO, "--archivo", str(grande))
        assert salida.returncode == 2 and not (tmp_path / "registro.json").exists()

    def test_juez_sin_rubrica_se_niega(self, proyecto, tmp_path):
        declarar_entorno(proyecto, "desarrollo")
        artefacto, _ = self._artefactos(tmp_path)
        assert correr_codex(proyecto, tmp_path, self.APROBADO, "--rol", "juez", "--archivo", str(artefacto)).returncode == 3


class TestOllamaLocal:
    @pytest.mark.parametrize("url,local", [
        ("http://127.0.0.1:11434/api/generate", True),
        ("http://localhost:11434/api/generate", True),
        ("http://[::1]:11434/api/generate", True),
        ("http://localhost.atacante.example/api/generate", False),
        ("http://127.0.0.1.atacante.example/api/generate", False),
        ("http://usuario:clave@localhost:11434/api/generate", False),
        ("https://localhost:11434/api/generate", False),
        ("http://localhost:no-es-puerto/api/generate", False),
    ])
    def test_solo_hosts_locales_exactos(self, url, local):
        sys.path.insert(0, str(SCRIPTS))
        import revisar_ollama

        assert revisar_ollama.endpoint_local(url) is local

    def test_un_proxy_del_entorno_no_se_usa(self, monkeypatch):
        sys.path.insert(0, str(SCRIPTS))
        import revisar_ollama

        class Ollama(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                cuerpo = json.dumps({"response": json.dumps({"veredicto": "aprobar", "hallazgos": []})}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(cuerpo)

            def log_message(self, *args):
                pass

        servidor = http.server.HTTPServer(("127.0.0.1", 0), Ollama)
        threading.Thread(target=servidor.serve_forever, daemon=True).start()
        try:
            # Un proxy inalcanzable: si se usara, la consulta fallaría (y el texto saldría de la máquina).
            monkeypatch.setenv("http_proxy", "http://192.0.2.1:9")
            monkeypatch.setenv("HTTP_PROXY", "http://192.0.2.1:9")
            monkeypatch.delenv("no_proxy", raising=False)
            monkeypatch.delenv("NO_PROXY", raising=False)
            resultado = revisar_ollama.consultar("qwen", "hola", f"http://127.0.0.1:{servidor.server_port}/api/generate", timeout=10)
            assert resultado["veredicto"] == "aprobar"
        finally:
            servidor.shutdown()


# ---------------------------------------------------------------- compuerta holdout con juez (N-07, N-08, N-09)

def veredicto(tmp_path, nombre: str, artefacto: str, *, modelo="gpt-6.1-sol", familia="openai", version="codex-cli 1", aprobado=True, cubiertos=5, caso=None):
    rubrica = RUBRICA_VERIFICACION.read_bytes()
    # Como lo guarda el revisor: cada «si» con la evidencia ya cotejada contra el artefacto que tuvo a la vista.
    criterios = [dict(c, evidencia_verificada=True) if c["cumple"] == "si" else c for c in numerados(*["si" if aprobado else "no"] * cubiertos)]
    datos = {"criterios": criterios, "fallos_criticos": [], "observaciones": "", "aprobado": True,
             "juez": {"familia": familia, "herramienta": "codex", "modelo": modelo, "esfuerzo": "high", "version": version, "rol": "juez"},
             "material": juez.material([juez.sha256(artefacto)], rubrica, caso)}
    ruta = tmp_path / nombre
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    return ruta


def refrescar(ruta):
    ahora = time.time() + 2
    os.utime(ruta, (ahora, ahora))
    return ruta


def casos_holdout(compuerta):
    return sorted(compuerta._casos("verificar-cita", "holdout"))


def veredictos_holdout(tmp_path, compuerta, prefijo="vh", artefactos=None, **kw):
    rutas = []
    for i, caso in enumerate(casos_holdout(compuerta)):
        artefacto = (artefactos or {}).get(i, f"{prefijo}-artefacto-{i}")
        rutas.append(refrescar(veredicto(tmp_path, f"{prefijo}-{i}.json", artefacto, caso=caso, **kw)))
    return rutas


@pytest.fixture
def compuerta(tmp_path, monkeypatch):
    sys.path.insert(0, str(RAIZ / "evals"))
    import compuerta_holdout

    proyecto = tmp_path / "proyecto"
    (proyecto / ".itostack" / "bitacora").mkdir(parents=True)
    monkeypatch.setenv("ITOSTACK_PROYECTO", str(proyecto))
    monkeypatch.setattr(compuerta_holdout, "COMPUERTA", tmp_path / "compuerta")
    monkeypatch.setattr(compuerta_holdout, "HISTORIAL", tmp_path / "compuerta" / "historial.tsv")
    # Las pruebas del protocolo simulan una reserva aislada; la reserva real está contaminada (TestReservaContaminada).
    (tmp_path / "reserva.json").write_text(json.dumps({"estado": "aislada"}), encoding="utf-8")
    monkeypatch.setattr(compuerta_holdout, "RESERVA_ESTADO", tmp_path / "reserva.json")
    desarrollo = {"cases": [{"name": n, "aggregates": {"score": 1.0}} for n in compuerta_holdout._casos("verificar-cita", "desarrollo")]}
    (tmp_path / "dev.json").write_text(json.dumps(desarrollo), encoding="utf-8")
    holdout = {"cases": [{"name": n, "aggregates": {"score": 1.0}} for n in compuerta_holdout._casos("verificar-cita", "holdout")]}
    (tmp_path / "h.json").write_text(json.dumps(holdout), encoding="utf-8")
    return compuerta_holdout


def historial(tmp_path) -> str:
    return (tmp_path / "compuerta" / "historial.tsv").read_text(encoding="utf-8")


def escribir_bitacora(tmp_path, filas):
    ruta = tmp_path / "proyecto" / ".itostack" / "bitacora" / "juez.tsv"
    encabezado = "fecha\tfamilia\therramienta\tmodelo\tesfuerzo\tversion\tcaso\tsha256_artefactos\tsha256_rubrica\tpuntaje\taprobado\n"
    ruta.write_text(encabezado + "".join("\t".join(f) + "\n" for f in filas), encoding="utf-8")


class TestCompuertaConJuez:
    def _congelar_con_juez(self, compuerta, tmp_path):
        assert compuerta.congelar("verificar-cita", tmp_path / "dev.json", [veredicto(tmp_path, "v.json", "artefacto-dev")]) == 0

    def _registrar(self, compuerta, tmp_path, jueces):
        return compuerta.holdout("verificar-cita", refrescar(tmp_path / "h.json"), [], jueces)

    def test_no_congela_sin_juez_ni_motivo(self, compuerta, tmp_path):
        assert compuerta.congelar("verificar-cita", tmp_path / "dev.json") == 1

    def test_congela_sin_juez_solo_con_motivo_registrado(self, compuerta, tmp_path):
        assert compuerta.congelar("verificar-cita", tmp_path / "dev.json", sin_juez_externo="Codex sin cuota hoy") == 0
        assert "sin juez externo: Codex sin cuota hoy" in historial(tmp_path)

    def test_juez_de_la_familia_claude_no_cuenta(self, compuerta, tmp_path):
        v = veredicto(tmp_path, "v.json", "a", modelo="claude-haiku", familia="anthropic")
        assert compuerta.congelar("verificar-cita", tmp_path / "dev.json", [v]) == 1

    def test_aprobado_editado_a_mano_no_cuenta(self, compuerta, tmp_path):
        assert compuerta.congelar("verificar-cita", tmp_path / "dev.json", [veredicto(tmp_path, "v.json", "a", aprobado=False)]) == 1

    def test_veredicto_que_omite_criterios_no_cuenta(self, compuerta, tmp_path):
        assert compuerta.congelar("verificar-cita", tmp_path / "dev.json", [veredicto(tmp_path, "v.json", "a", cubiertos=1)]) == 1

    def test_rubrica_no_congelada_no_cuenta(self, compuerta, tmp_path):
        v = veredicto(tmp_path, "v.json", "a")
        datos = json.loads(v.read_text(encoding="utf-8"))
        datos["material"]["rubrica"]["sha256"] = juez.sha256("1. una rúbrica inventada")
        v.write_text(json.dumps(datos), encoding="utf-8")
        assert compuerta.congelar("verificar-cita", tmp_path / "dev.json", [v]) == 1

    def test_no_se_vuelve_a_congelar_la_misma_candidata(self, compuerta, tmp_path):
        self._congelar_con_juez(compuerta, tmp_path)
        assert compuerta.congelar("verificar-cita", tmp_path / "dev.json", sin_juez_externo="quitar el juez") == 1
        # Ni aunque se borre el archivo de la candidata: el historial guarda la huella congelada.
        (tmp_path / "compuerta" / "verificar-cita.json").unlink()
        assert compuerta.congelar("verificar-cita", tmp_path / "dev.json", sin_juez_externo="quitar el juez") == 1

    def test_flujo_completo_aceptado(self, compuerta, tmp_path):
        self._congelar_con_juez(compuerta, tmp_path)
        candidata = json.loads((tmp_path / "compuerta" / "verificar-cita.json").read_text(encoding="utf-8"))
        assert candidata["juez"]["modelo"] == "gpt-6.1-sol" and candidata["huella_holdout"] and candidata["artefactos_desarrollo"]
        assert compuerta.reservar("verificar-cita") == 0
        assert self._registrar(compuerta, tmp_path, veredictos_holdout(tmp_path, compuerta)) == 0
        assert "\tACEPTADA\t" in historial(tmp_path)

    def test_falta_el_veredicto_de_un_caso_holdout(self, compuerta, tmp_path):
        self._congelar_con_juez(compuerta, tmp_path)
        compuerta.reservar("verificar-cita")
        assert self._registrar(compuerta, tmp_path, veredictos_holdout(tmp_path, compuerta)[:-1]) == 1
        assert "\tholdout\t" not in historial(tmp_path)

    def test_registrar_sin_reserva_no_vale(self, compuerta, tmp_path):
        self._congelar_con_juez(compuerta, tmp_path)
        assert self._registrar(compuerta, tmp_path, veredictos_holdout(tmp_path, compuerta)) == 1
        assert "\tholdout\t" not in historial(tmp_path)

    def test_resultados_anteriores_a_la_reserva_no_valen(self, compuerta, tmp_path):
        self._congelar_con_juez(compuerta, tmp_path)
        viejo = time.time() - 600
        os.utime(tmp_path / "h.json", (viejo, viejo))
        compuerta.reservar("verificar-cita")
        assert compuerta.holdout("verificar-cita", tmp_path / "h.json", [], veredictos_holdout(tmp_path, compuerta)) == 1

    def test_veredicto_de_desarrollo_presentado_como_holdout(self, compuerta, tmp_path):
        self._congelar_con_juez(compuerta, tmp_path)
        compuerta.reservar("verificar-cita")
        reciclados = veredictos_holdout(tmp_path, compuerta, artefactos={0: "artefacto-dev"})
        assert self._registrar(compuerta, tmp_path, reciclados) == 1

    def test_el_mismo_juez_ya_reprobo_en_otra_corrida(self, compuerta, tmp_path):
        self._congelar_con_juez(compuerta, tmp_path)
        compuerta.reservar("verificar-cita")
        rubrica = juez.sha256(RUBRICA_VERIFICACION.read_bytes())
        escribir_bitacora(tmp_path, [["2026-11-18T00:00:00+00:00", "openai", "codex", "gpt-6.1-sol", "high", "codex-cli 1", "", juez.sha256("vh-artefacto-0"), rubrica, "6.0", "no"]])
        assert self._registrar(compuerta, tmp_path, veredictos_holdout(tmp_path, compuerta)) == 1
        assert "RECHAZADA" in historial(tmp_path)

    def test_reprobado_de_otro_juez_no_veta(self, compuerta, tmp_path):
        self._congelar_con_juez(compuerta, tmp_path)
        compuerta.reservar("verificar-cita")
        rubrica = juez.sha256(RUBRICA_VERIFICACION.read_bytes())
        escribir_bitacora(tmp_path, [
            ["2026-11-18T00:00:00+00:00", "ollama", "ollama", "qwen2.5:14b", "None", "None", "", juez.sha256("vh-artefacto-0"), rubrica, "6.0", "no"],
            # Mismo modelo y versión, pero otro esfuerzo: para la compuerta es otro juez.
            ["2026-11-18T00:00:00+00:00", "openai", "codex", "gpt-6.1-sol", "low", "codex-cli 1", "", juez.sha256("vh-artefacto-1"), rubrica, "6.0", "no"],
        ])
        assert self._registrar(compuerta, tmp_path, veredictos_holdout(tmp_path, compuerta)) == 0

    def test_antecedente_con_artefactos_en_otro_orden(self, compuerta, tmp_path):
        self._congelar_con_juez(compuerta, tmp_path)
        compuerta.reservar("verificar-cita")
        a, b = juez.sha256("x1"), juez.sha256("x2")
        rubrica = juez.sha256(RUBRICA_VERIFICACION.read_bytes())
        escribir_bitacora(tmp_path, [["2026-11-18T00:00:00+00:00", "openai", "codex", "gpt-6.1-sol", "high", "codex-cli 1", "", f"{max(a, b)},{min(a, b)}", rubrica, "6.0", "no"]])
        rutas = veredictos_holdout(tmp_path, compuerta)
        datos = json.loads(rutas[0].read_text(encoding="utf-8"))
        datos["material"]["sha256_artefactos"] = [a, b]
        rutas[0].write_text(json.dumps(datos), encoding="utf-8")
        assert self._registrar(compuerta, tmp_path, [refrescar(r) for r in rutas]) == 1

    def test_cambiar_de_juez_tras_congelar_no_se_permite(self, compuerta, tmp_path):
        self._congelar_con_juez(compuerta, tmp_path)
        compuerta.reservar("verificar-cita")
        assert self._registrar(compuerta, tmp_path, veredictos_holdout(tmp_path, compuerta, "otro", version="codex-cli 2")) == 1
        assert self._registrar(compuerta, tmp_path, veredictos_holdout(tmp_path, compuerta)) == 0

    def test_juez_que_reprueba_el_holdout_rechaza(self, compuerta, tmp_path):
        self._congelar_con_juez(compuerta, tmp_path)
        compuerta.reservar("verificar-cita")
        assert self._registrar(compuerta, tmp_path, veredictos_holdout(tmp_path, compuerta, aprobado=False)) == 1
        assert "RECHAZADA" in historial(tmp_path)

    def test_la_decision_se_escribe_una_sola_vez(self, compuerta, tmp_path):
        self._congelar_con_juez(compuerta, tmp_path)
        compuerta.reservar("verificar-cita")
        huella = compuerta.huella("verificar-cita")
        (tmp_path / "compuerta" / f"verificar-cita.{huella[:16]}.decidido").write_text("otra invocación", encoding="utf-8")
        assert self._registrar(compuerta, tmp_path, veredictos_holdout(tmp_path, compuerta)) == 1
        assert "\tholdout\t" not in historial(tmp_path)

    def test_reserva_consume_el_intento_aunque_se_interrumpa(self, compuerta, tmp_path):
        self._congelar_con_juez(compuerta, tmp_path)
        assert compuerta.reservar("verificar-cita") == 0
        assert compuerta.reservar("verificar-cita") == 1  # otra invocación o un reintento tras interrumpir

    def test_resultados_ilegibles_rechazan_y_consumen(self, compuerta, tmp_path):
        compuerta.congelar("verificar-cita", tmp_path / "dev.json", sin_juez_externo="prueba")
        compuerta.reservar("verificar-cita")
        (tmp_path / "roto.json").write_text("{no es json", encoding="utf-8")
        assert compuerta.holdout("verificar-cita", tmp_path / "roto.json", []) == 1
        assert compuerta.holdout("verificar-cita", refrescar(tmp_path / "h.json"), []) == 1  # ya consumido

    def test_sin_juez_la_aceptacion_lo_dice(self, compuerta, tmp_path):
        compuerta.congelar("verificar-cita", tmp_path / "dev.json", sin_juez_externo="prueba")
        compuerta.reservar("verificar-cita")
        assert compuerta.holdout("verificar-cita", refrescar(tmp_path / "h.json"), []) == 0
        assert "ACEPTADA SIN JUEZ EXTERNO" in historial(tmp_path)

    def test_marca_previa_impide_correr_sin_resultados(self, compuerta, tmp_path):
        compuerta.congelar("verificar-cita", tmp_path / "dev.json", sin_juez_externo="prueba")
        huella = compuerta.huella("verificar-cita")
        (tmp_path / "compuerta" / f"verificar-cita.{huella[:16]}.consumido").write_text("2026-11-18T00:00:00+00:00\n", encoding="utf-8")
        assert compuerta.holdout("verificar-cita", None, []) == 1  # no lanza claude plugin eval

    def test_reserva_cambiada_tras_congelar(self, compuerta, tmp_path, monkeypatch):
        compuerta.congelar("verificar-cita", tmp_path / "dev.json", sin_juez_externo="prueba")
        monkeypatch.setattr(compuerta, "huella_holdout", lambda skill: "otra")
        assert compuerta.reservar("verificar-cita") == 1

    def test_la_huella_cubre_rubricas_y_agentes(self, compuerta):
        antes = compuerta.huella("verificar-cita")
        original = RUBRICA_VERIFICACION.read_bytes()
        try:
            RUBRICA_VERIFICACION.write_bytes(original + b"\n")
            assert compuerta.huella("verificar-cita") != antes
        finally:
            RUBRICA_VERIFICACION.write_bytes(original)
        assert compuerta.huella("verificar-cita") == antes


# ---------------------------------------------------------------- D-04 y N-01: citas

def marcas(linea: str) -> dict:
    return {c.valor: c.marcada_no_verificada for c in citas.extraer(linea)}


class TestMarcaNoVerificada:
    @pytest.mark.parametrize("palabra", ["INEXISTENTE", "NO VERIFICABLE", "BLOQUEADO", "NO VERIFICADO", "⚠ NO VERIFICADO", "❌"])
    def test_palabra_dentro_del_rubro_no_exime(self, palabra):
        linea = f'Tesis registro digital FICT-0009, de rubro: "LA ACCIÓN {palabra} NO PROCEDE CONTRA ACTOS FUTUROS."'
        assert not citas.extraer(linea)[0].marcada_no_verificada

    def test_advertencia_de_contexto_no_exime(self):
        assert not citas.extraer("Registro digital FICT-0002 ⚠ Tesis aislada: criterio orientador.")[0].marcada_no_verificada

    @pytest.mark.parametrize("marca", ["⚠ NO VERIFICADO", "⚠ CITA NO VERIFICADA", "⚠ no verificable", "❌"])
    def test_marca_explicita_fuera_de_comillas(self, marca):
        assert citas.extraer(f"Cita ajena: registro digital FICT-0404 {marca}.")[0].marcada_no_verificada

    @pytest.mark.parametrize("linea", [
        "Cita ajena: registro digital FICT-0404 ❌; es aplicable el registro digital FICT-0009.",
        "Registro digital FICT-0404 ❌. Es aplicable el registro digital FICT-0009.",
        "Registro digital FICT-0404 ❌, pero se aplica el registro digital FICT-0009.",
    ])
    def test_la_marca_de_una_cita_no_exime_a_la_siguiente(self, linea):
        assert marcas(linea) == {"FICT-0404": True, "FICT-0009": False}

    def test_la_marca_no_alcanza_a_una_cita_previa_separada_por_palabras(self):
        assert marcas("Registro digital FICT-0009 y registro digital FICT-0404 ❌.") == {"FICT-0009": False, "FICT-0404": True}

    def test_clave_y_registro_de_la_misma_cita(self):
        assert all(marcas("Jurisprudencia 1a./J. 45/2019 (10a.), registro digital 1999999 ⚠ NO VERIFICADO.").values())

    def test_el_punto_de_un_rubro_no_separa_la_cita_de_su_marca(self):
        assert marcas("Registro digital FICT-0404, rubro: “CRITERIO AJENO. SU TEXTO ES ÉSTE.” ❌") == {"FICT-0404": True}

    def test_fila_de_matriz_con_clave_y_marca_al_final(self):
        fila = "| c02 | FICT-0404 | FICT.4o.P. J/9 P (12a.) | ❌ NO VERIFICABLE — DISCREPANTE O INEXISTENTE |"
        assert all(c.marcada_no_verificada for c in citas.extraer(fila))

    def test_la_marca_no_se_propaga_al_parrafo(self):
        parrafo = "Cita ajena: registro digital FICT-0404 ❌.\nEs aplicable el registro digital FICT-0009, de rubro: \"OTRO RUBRO SUFICIENTEMENTE LARGO.\""
        estado = {r.registro: r.marcada_no_verificada for r in citas.agrupar_referencias(parrafo)}
        assert estado == {"FICT-0404": True, "FICT-0009": False}

    def test_d04_en_el_guardia(self, proyecto):
        texto = 'Es aplicable la tesis registro digital FICT-0009, de rubro: "LA PRUEBA INEXISTENTE NO GENERA EFECTOS JURÍDICOS."\n'
        salida = correr_hook("guardia_escritura.py", {
            "tool_name": "Write", "cwd": str(proyecto),
            "tool_input": {"file_path": str(proyecto / "salidas/escrito.md"), "content": texto},
        })
        assert decision(salida) == "deny"


class TestRubroContraEvidencia:
    OFICIAL = {"FICT-0001": {"rubro": RUBRO_0001}, "FICT-0002": {"rubro": "CRITERIO DOS DE PRUEBA SUFICIENTE."}}

    def _buscar(self, registro, clave):
        return self.OFICIAL.get(registro)

    def test_rubro_alterado_con_evidencia_se_detecta(self):
        texto = 'Tesis registro digital FICT-0001, de rubro: "CRITERIO FICTICIO DE PRUEBA. LA VERIFICACIÓN NO EXIGE CAPTURA."'
        assert citas.rubros_discrepantes(texto, self._buscar)

    def test_variacion_tipografica_pasa(self):
        texto = f'Tesis registro digital FICT-0001, de rubro: «{RUBRO_0001.lower()}»'
        assert citas.rubros_discrepantes(texto, self._buscar) == []

    @pytest.mark.parametrize("texto", [
        "Registro digital FICT-0001. Rubro: LA VERIFICACIÓN FORENSE ES OPCIONAL.",
        "Registro digital FICT-0001. Rubro: LA VERIFICACIÓN FORENSE DE UNA CITA ES OPCIONAL SIEMPRE Y EN TODO CASO.",
        "Registro digital FICT-0001. RUBRO: LA VERIFICACIÓN ES OPCIONAL.",
        'Registro digital FICT-0001, rubro: "FALSO"',
    ])
    def test_rubro_declarado_no_se_salta_el_cotejo(self, texto):
        assert citas.rubros_discrepantes(texto, self._buscar)

    def test_rubro_declarado_sin_comillas_correcto_pasa(self):
        assert citas.rubros_discrepantes(f"Registro digital FICT-0001. Rubro: {RUBRO_0001}", self._buscar) == []

    def test_bloque_en_mayusculas_sin_la_palabra_rubro_no_se_coteja(self):
        texto = "Tesis registro digital FICT-0001. OTRO TEXTO EN MAYÚSCULAS QUE NO ES UN RUBRO NI LO DICE."
        assert citas.rubros_discrepantes(texto, self._buscar) == []

    def test_varias_citas_ensambladas_en_una_linea(self):
        r2 = self.OFICIAL["FICT-0002"]["rubro"]
        linea = (f"Jurisprudencia FICT.1o.P. J/1 P (12a.), de rubro: «{RUBRO_0001}», emitida por T, registro digital FICT-0001 y "
                 f"Tesis FICT.2o.P. J/2 P (12a.), de rubro: «{r2}», emitida por T, registro digital FICT-0002.")
        assert citas.rubros_discrepantes(linea, self._buscar) == []
        alterada = linea.replace(r2, "CRITERIO DOS ALTERADO A MANO.")
        problemas = citas.rubros_discrepantes(alterada, self._buscar)
        assert len(problemas) == 1 and "FICT-0002" in problemas[0]

    def test_varias_citas_con_rubro_antes_del_registro(self):
        r2 = self.OFICIAL["FICT-0002"]["rubro"]
        linea = f"La de rubro «{RUBRO_0001}», registro digital FICT-0001; y la de rubro «{r2}», registro digital FICT-0002."
        assert citas.rubros_discrepantes(linea, self._buscar) == []

    @requiere_navegador
    def test_n01_en_el_guardia_con_evidencia_real(self, proyecto):
        assert verificar(proyecto, "tesis", "--registro", "FICT-0001", "--rubro", RUBRO_0001).returncode == 0
        bueno = f'Tesis registro digital FICT-0001, de rubro: "{RUBRO_0001}"\n'
        falso = 'Tesis registro digital FICT-0001, de rubro: "CRITERIO FICTICIO DE PRUEBA. LA VERIFICACIÓN FORENSE ES OPCIONAL."\n'
        sin_comillas = "Tesis registro digital FICT-0001. Rubro: LA VERIFICACIÓN FORENSE ES OPCIONAL.\n"
        for texto, esperado in ((bueno, None), (falso, "deny"), (sin_comillas, "deny")):
            salida = correr_hook("guardia_escritura.py", {
                "tool_name": "Write", "cwd": str(proyecto),
                "tool_input": {"file_path": str(proyecto / "salidas/escrito.md"), "content": texto},
            })
            assert decision(salida) == esperado, texto


# ---------------------------------------------------------------- B-02: la compuerta humana no se aprueba sola

class TestCompuertaHumana:
    @pytest.mark.parametrize("modo,esperado", [("default", "ask"), ("acceptEdits", "ask"), ("plan", "ask"),
                                               ("auto", "deny"), ("bypassPermissions", "deny"), ("dontAsk", "deny"), (None, "deny")])
    def test_push_a_main_segun_modo(self, modo, esperado):
        entrada = {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}}
        if modo:
            entrada["permission_mode"] = modo
        assert decision(correr_hook("guardia_bash.py", entrada)) == esperado

    def test_envio_mcp_en_modo_auto_se_deniega(self, tmp_path):
        entrada = {"tool_name": "mcp__Gmail__send_message", "tool_input": {"body": "hola"}, "cwd": str(tmp_path), "permission_mode": "auto"}
        assert decision(correr_hook("guardia_externo.py", entrada)) == "deny"

    def test_lista_curada_por_el_operador(self, proyecto):
        ruta = proyecto / ".itostack" / "config.json"
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        datos["acciones_externas_permitidas"] = ["mcp__plugin_telegram_telegram__reply"]
        ruta.write_text(json.dumps(datos), encoding="utf-8")
        base = {"cwd": str(proyecto), "permission_mode": "auto", "tool_input": {"text": "listo"}}
        assert decision(correr_hook("guardia_externo.py", {**base, "tool_name": "mcp__plugin_telegram_telegram__reply"})) is None
        assert decision(correr_hook("guardia_externo.py", {**base, "tool_name": "mcp__Gmail__send_message"})) == "deny"

    def test_la_lista_no_salta_las_citas_sin_evidencia(self, proyecto):
        ruta = proyecto / ".itostack" / "config.json"
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        datos["acciones_externas_permitidas"] = ["mcp__*"]
        ruta.write_text(json.dumps(datos), encoding="utf-8")
        entrada = {"tool_name": "mcp__Slack__slack_send_message", "cwd": str(proyecto), "tool_input": {"text": "Aplica la tesis registro digital FICT-0001"}}
        assert decision(correr_hook("guardia_externo.py", entrada)) == "deny"


# ---------------------------------------------------------------- N-08: la reserva no se lee

class TestReservaHoldout:
    RUTA = "/x/itostack/evals/verificar-cita/holdout-fail-clave/case.yaml"

    def test_read_de_holdout_se_deniega(self):
        assert decision(correr_hook("guardia_lectura.py", {"tool_name": "Read", "tool_input": {"file_path": self.RUTA}})) == "deny"

    def test_glob_y_grep_dirigidos_se_deniegan(self):
        assert decision(correr_hook("guardia_lectura.py", {"tool_name": "Glob", "tool_input": {"pattern": "evals/*/holdout-*/**"}})) == "deny"
        assert decision(correr_hook("guardia_lectura.py", {"tool_name": "Grep", "tool_input": {"pattern": "x", "path": "evals/verificar-cita/holdout-fail-clave"}})) == "deny"

    @pytest.mark.parametrize("ruta", ["evals", "evals/verificar-cita", str(RAIZ / "evals")])
    def test_grep_amplio_sobre_evals_se_deniega(self, ruta):
        assert decision(correr_hook("guardia_lectura.py", {"tool_name": "Grep", "tool_input": {"pattern": ".", "path": ruta}, "cwd": str(RAIZ)})) == "deny"

    def test_buscar_en_un_caso_de_desarrollo_o_en_codigo_pasa(self):
        for datos in ({"pattern": "holdout-", "path": "evals/compuerta_holdout.py"}, {"pattern": ".", "path": "evals/verificar-cita/pass-exacto"}, {"pattern": ".", "path": "scripts"}):
            assert decision(correr_hook("guardia_lectura.py", {"tool_name": "Grep", "tool_input": datos, "cwd": str(RAIZ)})) is None
        assert decision(correr_hook("guardia_lectura.py", {"tool_name": "Read", "tool_input": {"file_path": "/x/evals/verificar-cita/pass-exacto/case.yaml"}})) is None

    @pytest.mark.parametrize("comando", [f"cat {RUTA}", "rg -n . evals/verificar-cita", "grep -r rubro evals", "cat evals/verificar-cita/*/case.yaml"])
    def test_bash_que_lee_o_busca_en_la_reserva_se_deniega(self, comando):
        assert decision(correr_hook("guardia_bash.py", {"tool_name": "Bash", "tool_input": {"command": comando}, "cwd": str(RAIZ)})) == "deny"

    @pytest.mark.parametrize("comando", ["python evals/compuerta_holdout.py estado", "rg -n rubro evals/verificar-cita/pass-exacto", "rg -n rubro scripts", "ls evals/verificar-cita"])
    def test_bash_sobre_desarrollo_o_codigo_pasa(self, comando):
        assert decision(correr_hook("guardia_bash.py", {"tool_name": "Bash", "tool_input": {"command": comando}, "cwd": str(RAIZ)})) is None


# ---------------------------------------------------------------- D-10: lint --diff no aprueba en vacío

def git(repo, *argumentos):
    subprocess.run(["git", *argumentos], cwd=repo, check=True, capture_output=True)


def lint_diff(repo, *argumentos):
    return subprocess.run([sys.executable, str(RAIZ / "guardias" / "lint_itosturre.py"), "--diff", *argumentos], cwd=repo,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", env={**os.environ, "PYTHONUTF8": "1"}, timeout=60)


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "prueba@example.invalid")
    git(tmp_path, "config", "user.name", "Prueba")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "Agrega el archivo inicial de prueba")
    return tmp_path


ANTIPATRON = "from fast" + "api import FastAPI\n"  # partido para que el lint no marque este archivo de pruebas


class TestLintDiff:
    def test_sin_cambios_no_acredita(self, repo):
        salida = lint_diff(repo)
        assert salida.returncode == 2 and "0 archivos" in salida.stdout

    @pytest.mark.parametrize("nombre", ["nuevo.py", "app_node_modules_extra.py", "nuevo_ñ.py"])
    def test_archivo_nuevo_sin_rastrear_se_examina(self, repo, nombre):
        (repo / "app.py").write_text("x = 2\n", encoding="utf-8")
        (repo / nombre).write_text(ANTIPATRON, encoding="utf-8")
        salida = lint_diff(repo)
        assert salida.returncode == 1 and "IT003" in salida.stdout, salida.stdout

    def test_base_invalida_falla_explicitamente(self, repo):
        (repo / "app.py").write_text("x = 2\n", encoding="utf-8")
        salida = lint_diff(repo, "no-existe-esta-base")
        assert salida.returncode == 2 and "falló" in salida.stdout

    def test_cambio_limpio_reporta_cobertura(self, repo):
        (repo / "app.py").write_text("x = 2\n", encoding="utf-8")
        salida = lint_diff(repo)
        assert salida.returncode == 0 and "examinados 1 archivo(s)" in salida.stdout


# ---------------------------------------------------------------- tercera revisión adversarial de Codex

class TestRondaCuatro:
    @pytest.mark.parametrize("numero", [True, 1.9, "1"])
    def test_numero_debe_ser_entero_json(self, numero):
        r = juez.calificar(respuesta([criterio("si", numero=numero)]), 1, ARTEFACTO)
        assert r["puntaje"] is None and not r["aprobado"] and any("numero" in e for e in r["contrato"])

    def test_aprobar_por_conteos_no_por_puntaje_redondeado(self):
        valores = ["si"] * 2499 + ["no"]
        r = juez.calificar(respuesta(numerados(*valores)), 2500, ARTEFACTO)
        assert r["puntaje"] == 10.0 and not r["aprobado"]

    def test_evidencia_en_orden_y_sin_descartar_tramos(self):
        artefacto = "primero viene esto y despues aquello otro"
        assert juez.evidencia_en_artefacto("«primero viene … aquello otro»", artefacto)
        assert not juez.evidencia_en_artefacto("«aquello otro … primero viene»", artefacto)
        assert not juez.evidencia_en_artefacto("«FALSO … aquello otro»", artefacto)
        assert juez.evidencia_en_artefacto("«PASS»", "VEREDICTO: PASS")

    def test_congelar_es_una_transicion_unica(self, compuerta, tmp_path):
        huella = compuerta.huella("verificar-cita")
        (tmp_path / "compuerta").mkdir(parents=True, exist_ok=True)
        (tmp_path / "compuerta" / f"verificar-cita.{huella[:16]}.congelado").write_text("otra invocación", encoding="utf-8")
        assert compuerta.congelar("verificar-cita", tmp_path / "dev.json", sin_juez_externo="prueba") == 1

    def test_resultados_de_justo_antes_de_la_reserva_no_valen(self, compuerta, tmp_path):
        compuerta.congelar("verificar-cita", tmp_path / "dev.json", [veredicto(tmp_path, "v.json", "artefacto-dev")])
        jueces = veredictos_holdout(tmp_path, compuerta)
        casi = time.time() - 0.5
        for ruta in [tmp_path / "h.json", *jueces]:
            os.utime(ruta, (casi, casi))
        compuerta.reservar("verificar-cita")
        assert compuerta.holdout("verificar-cita", tmp_path / "h.json", [], jueces) == 1

    OFICIAL = {"FICT-0001": {"rubro": "RUBRO A OFICIAL.", "clave": "FICT.1o.P. J/1 P (12a.)"},
               "FICT-0002": {"rubro": "RUBRO B OFICIAL.", "clave": "FICT.2o.P. J/2 P (12a.)"}}

    def _buscar(self, registro, clave):
        return self.OFICIAL.get(registro)

    @pytest.mark.parametrize("texto", [
        "registro digital FICT-0001\nRUBRO: «FALSO A»\nregistro digital FICT-0002\nRUBRO: «FALSO B»",
        "registro digital FICT-0001, rubro: «RUBRO A OFICIAL.», registro digital FICT-0002, clave FICT.2o.P. J/2 P (12a.), rubro: «FALSO»",
        "Tesis FICT.2o.P. J/2 P (12a.), registro digital FICT-0001, rubro: «RUBRO A OFICIAL.»",
        "registro digital FICT-0001, RUBRO: «" + "X" * 801 + "»",
        "rubro «RUBRO A OFICIAL.», registro digital FICT-0001, rubro «FALSO», registro digital FICT-0002",
    ])
    def test_casos_de_la_tercera_revision_se_rechazan(self, texto):
        assert citas.rubros_discrepantes(texto, self._buscar)

    @pytest.mark.parametrize("texto", [
        "registro digital FICT-0001\nRUBRO: «RUBRO A OFICIAL.»\nregistro digital FICT-0002\nRUBRO: «RUBRO B OFICIAL.»",
        "Tesis FICT.1o.P. J/1 P (12a.), registro digital FICT-0001, rubro: «RUBRO A OFICIAL.»",
        "registro digital FICT-0001, rubro: «RUBRO A OFICIAL.», registro digital FICT-0002, clave FICT.2o.P. J/2 P (12a.), rubro: «RUBRO B OFICIAL.»",
    ])
    def test_variantes_correctas_pasan(self, texto):
        assert citas.rubros_discrepantes(texto, self._buscar) == []

    def test_get_content_en_minusculas_sobre_holdout(self):
        comando = 'powershell -Command "get-content evals/verificar-cita/holdout-x/case.yaml"'
        assert decision(correr_hook("guardia_bash.py", {"tool_name": "Bash", "tool_input": {"command": comando}, "cwd": str(RAIZ)})) == "deny"

    def test_busqueda_desde_un_directorio_con_reserva(self):
        cwd = str(RAIZ / "evals" / "verificar-cita")
        assert decision(correr_hook("guardia_lectura.py", {"tool_name": "Grep", "tool_input": {"pattern": "."}, "cwd": cwd})) == "deny"
        assert decision(correr_hook("guardia_bash.py", {"tool_name": "Bash", "tool_input": {"command": "rg -n ."}, "cwd": cwd})) == "deny"

    def test_ruta_con_variable_sin_expandir(self):
        comando = 'rg -n . "$R/evals/verificar-cita"'
        assert decision(correr_hook("guardia_bash.py", {"tool_name": "Bash", "tool_input": {"command": comando}, "cwd": str(RAIZ)})) == "deny"

    def test_lint_respeta_la_codificacion_declarada(self, repo):
        (repo / "app.py").write_text("x = 2\n", encoding="utf-8")
        (repo / "latino.py").write_bytes(("# -*- coding: cp1252 -*-\nnombre = 'acción'\n" + ANTIPATRON).encode("cp1252"))
        salida = lint_diff(repo)
        assert salida.returncode == 1 and "IT003" in salida.stdout, salida.stdout

    def test_lint_con_archivo_ilegible_es_incompleto(self, repo):
        (repo / "app.py").write_text("x = 2\n", encoding="utf-8")
        (repo / "roto.js").write_bytes(b"var x = '\xff\xfe';\n")
        salida = lint_diff(repo)
        assert salida.returncode == 2 and "roto.js" in salida.stdout


# ---------------------------------------------------------------- cuarta revisión adversarial de Codex

class TestRondaCinco:
    OFICIAL = {"1999999": {"rubro": "OFICIAL LARGO DE PRUEBA.", "clave": "1a./J. 45/2019 (10a.)"},
               "FICT-0001": {"rubro": 'DERECHO A LA "VERDAD". ALCANCE.'},
               "FICT-0002": {"rubro": "LEGALIDAD. SU ALCANCE."}}

    def _buscar(self, registro, clave):
        return self.OFICIAL.get(registro) or ({"rubro": "OTRO RUBRO.", "clave": clave} if clave else None)

    def test_un_segundo_rubro_para_la_misma_cita_se_rechaza(self):
        assert citas.rubros_discrepantes("registro digital 1999999, rubro: «OFICIAL LARGO DE PRUEBA.»; rubro: «FALSO»", self._buscar)

    def test_registro_y_clave_en_segmentos_distintos_son_dos_citas(self):
        texto = "registro digital 1999999 ❌; 1a./J. 45/2019 (10a.), rubro: «FALSO»"
        assert citas.rubros_discrepantes(texto, self._buscar)

    def test_marca_dentro_de_una_cita_de_varias_lineas_no_exime(self):
        assert marcas("Texto citado: «\nregistro digital 1999999 ❌\n»") == {"1999999": False}

    def test_comillas_interiores_de_otro_tipo(self):
        assert citas.rubros_discrepantes('registro digital FICT-0001, rubro: «DERECHO A LA "VERDAD". ALCANCE.»', self._buscar) == []

    def test_rubro_declarado_con_puntos_propios_entre_varias_citas(self):
        texto = 'registro digital FICT-0002, Rubro: LEGALIDAD. SU ALCANCE. Y registro digital FICT-0001, rubro: «DERECHO A LA "VERDAD". ALCANCE.»'
        assert citas.rubros_discrepantes(texto, self._buscar) == []

    def test_la_rubrica_debe_ser_la_asignada_a_la_skill(self, compuerta, tmp_path):
        v = veredicto(tmp_path, "v.json", "a")
        datos = json.loads(v.read_text(encoding="utf-8"))
        otra = (RAIZ / "evals" / "rubricas" / "informe-vvca.md").read_bytes()
        datos["material"]["rubrica"] = {"sha256": juez.sha256(otra), "criterios": 6}
        datos["criterios"] = numerados(*["si"] * 6)
        v.write_text(json.dumps(datos), encoding="utf-8")
        assert compuerta.congelar("verificar-cita", tmp_path / "dev.json", [v]) == 1

    def test_ruta_entrecomillada_con_espacios(self, tmp_path):
        reserva = tmp_path / "mi proyecto" / "evals" / "verificar-cita" / "holdout-x"
        reserva.mkdir(parents=True)
        comando = f'cat "{(tmp_path / "mi proyecto" / "evals" / "verificar-cita").as_posix()}/*/case.yaml"'
        assert decision(correr_hook("guardia_bash.py", {"tool_name": "Bash", "tool_input": {"command": comando}, "cwd": str(RAIZ)})) == "deny"

    def test_holdout_en_mayusculas(self):
        ruta = "/x/itostack/evals/verificar-cita/HOLDOUT-fail-clave/case.yaml"
        assert decision(correr_hook("guardia_lectura.py", {"tool_name": "Read", "tool_input": {"file_path": ruta}})) == "deny"

    @pytest.mark.skipif(os.name != "nt", reason="solo en un sistema de archivos que no distingue mayúsculas")
    def test_evals_en_mayusculas_en_windows(self):
        comando = "Get-Content EVALS/verificar-cita/*/case.yaml"
        assert decision(correr_hook("guardia_bash.py", {"tool_name": "Bash", "tool_input": {"command": comando}, "cwd": str(RAIZ)})) == "deny"

    @pytest.mark.parametrize("datos", [
        [], None, "texto", {},
        {"criterios": [criterio(numero=1)]},                                         # sin fallos_criticos ni observaciones
        {"criterios": [criterio(numero=1)], "observaciones": ""},                    # R4-10a: sin fallos_criticos
        {"criterios": "x", "fallos_criticos": [], "observaciones": ""},
        respuesta([criterio(numero=1)], [None]),                                     # fallo crítico que no es texto
        respuesta([dict(criterio(numero=1), extra="x")]),                            # campo fuera del esquema
        respuesta([criterio(numero=1)], veredicto="aprobar"),
    ])
    def test_respuesta_del_juez_fuera_de_contrato(self, datos):
        assert juez.errores_contrato("juez", datos)

    def test_respuesta_del_juez_completa(self):
        assert juez.errores_contrato("juez", respuesta([criterio(numero=1)])) == []


# ---------------------------------------------------------------- cierre de 0.1.2: invariantes, no hallazgos
#
# Cada prueba de esta sección demuestra un invariante de la matriz (pruebas-manuales/fase-codex/matriz-invariantes.md)
# para una familia de entradas, no un caso suelto.

def _sin(clave):
    return lambda v: v.pop(clave)


def _poner(valor, *ruta):
    def mutar(v):
        destino = v
        for paso in ruta[:-1]:
            destino = destino[paso]
        destino[ruta[-1]] = valor
    return mutar


# R4-10 y su familia: todo lo que un veredicto guardado puede traer mal, y ningún valor por omisión que lo complete.
FUERA_DE_CONTRATO = {
    "lista": "[]", "null": "null", "texto": '"aprobado"', "objeto_vacio": "{}", "bytes_no_utf8": b"\xff\xfe{",
    "sin_fallos_criticos": _sin("fallos_criticos"), "fallos_criticos_null": _poner(None, "fallos_criticos"),
    "sin_observaciones": _sin("observaciones"), "criterios_null": _poner(None, "criterios"),
    "cumple_booleano": _poner(True, "criterios", 0, "cumple"), "cumple_con_acento": _poner("sí", "criterios", 0, "cumple"),
    "numero_texto": _poner("1", "criterios", 0, "numero"), "numero_booleano": _poner(True, "criterios", 0, "numero"),
    "evidencia_null": _poner(None, "criterios", 0, "evidencia"),
    "evidencia_verificada_texto": _poner("true", "criterios", 0, "evidencia_verificada"),
    "campo_ajeno_en_criterio": _poner(10, "criterios", 0, "puntaje"), "campo_ajeno_arriba": _poner("aprobar", "veredicto"),
    "juez_texto": _poner("codex", "juez"), "sin_material": _sin("material"),
    "artefactos_null": _poner(None, "material", "sha256_artefactos"), "rubrica_texto": _poner("verificacion.md", "material", "rubrica"),
}

JSON = st.recursive(
    st.none() | st.booleans() | st.integers(-3, 3) | st.floats(allow_nan=False, allow_infinity=False) | st.text(max_size=8),
    lambda hijos: st.lists(hijos, max_size=4) | st.dictionaries(st.text(max_size=12), hijos, max_size=4),
    max_leaves=25,
)
# Respuestas «casi válidas»: las claves del esquema con valores del tipo correcto o de otro. El texto libre no trae
# comillas: así la única evidencia que existe en ARTEFACTO es «cita textual» y el oráculo no depende del cotejo.
_VALOR = (st.none() | st.booleans() | st.integers(-1, 3) | st.floats(min_value=0.01, max_value=0.99)
          | st.text(alphabet=st.characters(blacklist_characters='"«»“”'), max_size=6) | st.sampled_from(["si", "no", "no_aplicable", "«cita textual»"]))
_CRITERIO = st.dictionaries(st.sampled_from(["numero", "criterio", "cumple", "evidencia", "extra"]), _VALOR, max_size=5)
CASI_RESPUESTA = st.dictionaries(
    st.sampled_from(["criterios", "fallos_criticos", "observaciones", "otro"]),
    _VALOR | st.lists(_CRITERIO, max_size=3) | st.lists(_VALOR, max_size=2),
    max_size=4,
)


@st.composite
def respuestas_perturbadas(draw):
    """Una respuesta válida de n criterios con, a lo sumo, una perturbación: borrar, reemplazar o agregar un campo.
    Sin perturbación aprueba a menudo, así que la propiedad «aprobar ⇒ contrato» no queda vacía."""
    n = draw(st.integers(1, 3))
    criterios = [{"numero": i, "criterio": "c", "cumple": draw(st.sampled_from(["si", "si", "si", "no_aplicable", "no"])), "evidencia": "«cita textual»"}
                 for i in range(1, n + 1)]
    datos = {"criterios": criterios, "fallos_criticos": [], "observaciones": ""}
    accion = draw(st.sampled_from(["nada", "nada", "borrar", "reemplazar", "agregar"]))
    if accion != "nada":
        rutas = [("fallos_criticos",), ("observaciones",), ("criterios",)] + [("criterios", i, k) for i in range(n) for k in ("numero", "criterio", "cumple", "evidencia")]
        ruta = draw(st.sampled_from(rutas))
        padre = datos
        for paso in ruta[:-1]:
            padre = padre[paso]
        if accion == "borrar":
            del padre[ruta[-1]]
        elif accion == "reemplazar":
            padre[ruta[-1]] = draw(_VALOR)
        else:
            padre["extra"] = draw(_VALOR)
    return n, datos
PROPIEDADES = settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])

# Salidas de `claude plugin eval` con la forma del esquema 1 (cases[].name + aggregates.score) y valores arbitrarios:
# el JSON aleatorio casi nunca trae la clave «cases», así que esa rama necesita su propia estrategia.
RESULTADOS = JSON | st.fixed_dictionaries({"cases": st.lists(
    JSON | st.fixed_dictionaries({}, optional={"name": JSON | st.sampled_from(["verificar-cita.holdout-fail-clave", "x.y"]),
                                               "aggregates": JSON | st.fixed_dictionaries({}, optional={"score": JSON})}),
    max_size=4)})

# Cada campo obligatorio de una respuesta que aprobaría: quitarlo o darle otro tipo debe bloquear (exhaustivo).
OBLIGATORIOS = [("criterios",), ("fallos_criticos",), ("observaciones",)] + [("criterios", 0, k) for k in ("numero", "criterio", "cumple", "evidencia")]

CONFIG_OPERADOR = {"modo": "real", "entorno": "desarrollo", "acciones_externas_permitidas": ["mcp__*"], "comparacion": {"ignorar_acentos": False},
                   "evidencia": {"vigencia_dias": 1}, "salidas_juridicas": ["**"], "modo_estricto_md": True}

CARRERA = textwrap.dedent('''
    import sys, time
    from pathlib import Path
    sys.path.insert(0, sys.argv[1])
    import compuerta_holdout as c
    c.COMPUERTA = Path(sys.argv[2]); c.HISTORIAL = c.COMPUERTA / "historial.tsv"; c.RESERVA_ESTADO = c.COMPUERTA.parent / "reserva.json"
    salida = Path(sys.argv[3])
    salida.with_suffix(".listo").write_text("")
    while not (salida.parent / "ya").exists():
        time.sleep(0.001)
    rc = c.reservar("verificar-cita") if sys.argv[4] == "reservar" else c.holdout("verificar-cita", Path(sys.argv[5]), [])
    salida.write_text(str(rc))
''')


class TestCierre012:
    # ---- I-2: Ollama no sigue redirecciones (una redirección podría llevar el texto fuera de la máquina)

    def test_ollama_no_sigue_redirecciones(self):
        sys.path.insert(0, str(SCRIPTS))
        import urllib.error

        import revisar_ollama

        visitas = []

        class Destino(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                visitas.append(self.path)
                cuerpo = json.dumps({"response": json.dumps({"veredicto": "aprobar", "hallazgos": []})}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(cuerpo)

            do_POST = do_GET

            def log_message(self, *args):
                pass

        destino = http.server.HTTPServer(("127.0.0.1", 0), Destino)

        class Redirige(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                # 303 es la redirección que urllib sí seguiría por omisión con un POST (convertido en GET).
                self.send_response(303)
                self.send_header("Location", f"http://127.0.0.1:{destino.server_port}/fuera")
                self.end_headers()

            def log_message(self, *args):
                pass

        origen = http.server.HTTPServer(("127.0.0.1", 0), Redirige)
        for servidor in (destino, origen):
            threading.Thread(target=servidor.serve_forever, daemon=True).start()
        try:
            with pytest.raises(urllib.error.HTTPError):
                revisar_ollama.consultar("qwen", "texto", f"http://127.0.0.1:{origen.server_port}/api/generate", timeout=10)
            assert visitas == []
        finally:
            destino.shutdown()
            origen.shutdown()

    # ---- I-7 / R4-10: la compuerta consumidora no acepta nada fuera de contrato, y BLOCKED no consume el intento

    def _escribir(self, ruta, variante, base):
        mutacion = FUERA_DE_CONTRATO[variante]
        if isinstance(mutacion, bytes):
            ruta.write_bytes(mutacion)
        elif isinstance(mutacion, str):
            ruta.write_text(mutacion, encoding="utf-8")
        else:
            datos = json.loads(base.read_text(encoding="utf-8"))
            mutacion(datos)
            ruta.write_text(json.dumps(datos), encoding="utf-8")
        return refrescar(ruta)

    @pytest.mark.parametrize("variante", sorted(FUERA_DE_CONTRATO))
    def test_veredicto_fuera_de_contrato_es_blocked_en_la_compuerta(self, compuerta, tmp_path, variante):
        base = veredicto(tmp_path, "base.json", "a")
        ruta = self._escribir(tmp_path / "v.json", variante, base)
        identidad, errores, desaprobados, _, _ = compuerta.veredictos_juez([ruta], proyecto=tmp_path / "proyecto", skill="verificar-cita")
        assert errores and not desaprobados and identidad is None  # BLOCKED: ni aprobado ni reprobado
        assert compuerta.congelar("verificar-cita", tmp_path / "dev.json", [ruta]) == 1

    def test_veredicto_incompleto_es_blocked_no_reprobado(self, compuerta, tmp_path):
        # Cumple el esquema pero omite un criterio de la rúbrica: no hay puntaje, así que no decide ni a favor ni en contra.
        ruta = veredicto(tmp_path, "v.json", "a", cubiertos=4)
        identidad, errores, desaprobados, _, _ = compuerta.veredictos_juez([ruta], proyecto=tmp_path / "proyecto", skill="verificar-cita")
        assert errores and not desaprobados and identidad is None

    @pytest.mark.parametrize("variante", ["sin_fallos_criticos", "lista", "null", "cumple_booleano", "bytes_no_utf8"])
    def test_blocked_en_el_holdout_no_decide_ni_consume(self, compuerta, tmp_path, variante):
        assert compuerta.congelar("verificar-cita", tmp_path / "dev.json", [veredicto(tmp_path, "v.json", "artefacto-dev")]) == 0
        assert compuerta.reservar("verificar-cita") == 0
        validos = veredictos_holdout(tmp_path, compuerta)
        roto = self._escribir(tmp_path / "roto.json", variante, validos[0])
        assert compuerta.holdout("verificar-cita", refrescar(tmp_path / "h.json"), [], [roto, *validos[1:]]) == 1
        huella = compuerta.huella("verificar-cita")
        assert "\tholdout\t" not in historial(tmp_path) and not (tmp_path / "compuerta" / f"verificar-cita.{huella[:16]}.decidido").exists()
        # El intento sigue reservado: con veredictos válidos del mismo juez se decide una sola vez.
        assert compuerta.holdout("verificar-cita", refrescar(tmp_path / "h.json"), [], [refrescar(v) for v in validos]) == 0
        assert historial(tmp_path).count("\tholdout\t") == 1

    @pytest.mark.parametrize("ruta", OBLIGATORIOS, ids=lambda r: ".".join(map(str, r)))
    @pytest.mark.parametrize("cambio", ["quitar", "null", "booleano", "otro_tipo"])
    def test_quitar_o_alterar_cualquier_campo_obligatorio_bloquea(self, ruta, cambio):
        datos = respuesta(numerados("si", "si"))
        assert juez.calificar(datos, 2, ARTEFACTO)["aprobado"]  # sin alterar, aprobaría
        padre = datos
        for paso in ruta[:-1]:
            padre = padre[paso]
        if cambio == "quitar":
            del padre[ruta[-1]]
        elif cambio == "otro_tipo":
            padre[ruta[-1]] = {list: "x", str: ["x"], int: "1"}[type(padre[ruta[-1]])]
        else:
            padre[ruta[-1]] = {"null": None, "booleano": True}[cambio]
        r = juez.calificar(datos, 2, ARTEFACTO)
        assert not r["aprobado"] and r["puntaje"] is None and juez.codigo_salida("juez", r) == 2

    def test_si_sin_evidencia_verificada_no_cuenta_en_la_compuerta(self):
        # Antes, sin artefacto, un «si» sin la anotación del revisor contaba como cumplido.
        assert not juez.calificar(respuesta(numerados("si")), 1)["aprobado"]
        assert juez.calificar(respuesta([dict(criterio(numero=1), evidencia_verificada=True)]), 1)["aprobado"]

    @pytest.mark.parametrize("esperados", [None, 0, True, "5"])
    def test_sin_rubrica_no_hay_aprobado(self, esperados):
        r = juez.calificar(respuesta(numerados("si")), esperados, ARTEFACTO)
        assert r["puntaje"] is None and not r["aprobado"] and juez.codigo_salida("juez", r) == 2

    @PROPIEDADES
    @given(datos=JSON)
    def test_propiedad_cualquier_json_como_veredicto_es_blocked_sin_excepcion(self, compuerta, tmp_path, datos):
        ruta = tmp_path / "arbitrario.json"
        ruta.write_text(json.dumps(datos), encoding="utf-8")
        identidad, errores, desaprobados, _, _ = compuerta.veredictos_juez([ruta], proyecto=tmp_path / "proyecto", skill="verificar-cita")
        assert errores and not desaprobados and identidad is None

    @PROPIEDADES
    @given(caso=st.one_of(respuestas_perturbadas(), respuestas_perturbadas(), st.tuples(st.integers(1, 3), CASI_RESPUESTA)))
    def test_propiedad_aprobar_exige_contrato_completo(self, caso):
        esperados, datos = caso
        r = juez.calificar(datos, esperados, ARTEFACTO)
        event(f"aprobado={r['aprobado']}")
        if r["aprobado"]:
            # Oráculo semántico independiente del validador: todo lo que una aprobación supone, explícito en la respuesta.
            assert set(datos) == {"criterios", "fallos_criticos", "observaciones"} and isinstance(datos["observaciones"], str)
            assert all(isinstance(f, str) and not f.strip() for f in datos["fallos_criticos"])
            assert sorted(c["numero"] for c in datos["criterios"]) == list(range(1, esperados + 1))
            assert all(set(c) == {"numero", "criterio", "cumple", "evidencia"} and c["cumple"] in {"si", "no_aplicable"} for c in datos["criterios"])
            assert all(type(c["numero"]) is int for c in datos["criterios"])
            assert any(c["cumple"] == "si" for c in datos["criterios"])
            assert all(c["evidencia"] == "«cita textual»" for c in datos["criterios"] if c["cumple"] == "si")
        if r["puntaje"] is None:
            assert juez.codigo_salida("juez", r) == 2

    @PROPIEDADES
    @given(datos=CASI_RESPUESTA | respuestas_perturbadas().map(lambda caso: caso[1]))
    def test_propiedad_el_validador_coincide_con_jsonschema(self, datos):
        jsonschema = pytest.importorskip("jsonschema")
        valido = jsonschema.Draft202012Validator(juez.ESQUEMAS["juez"]).is_valid(datos)
        assert (juez.errores_contrato("juez", datos) == []) == valido

    @PROPIEDADES
    @given(datos=RESULTADOS)
    def test_propiedad_resultados_arbitrarios_no_lanzan(self, compuerta, tmp_path, datos):
        compuerta.puntajes(datos)
        ruta = tmp_path / "resultados.json"
        ruta.write_text(json.dumps(datos), encoding="utf-8")
        minimo, _, faltantes = compuerta._evaluar("verificar-cita", "holdout", ruta)
        assert minimo == 0.0 and faltantes  # sin los casos holdout con nombre, nunca un mínimo que apruebe

    @pytest.mark.parametrize("contenido", [
        b"\xff\xfe{", b'{"cases": ["x", 5, null]}', b'{"cases": [{"name": "verificar-cita.holdout-fail-clave", "aggregates": 3}]}',
        b'{"cases": [{"name": "verificar-cita.holdout-fail-clave", "aggregates": {"score": true}}]}',
    ], ids=["no_utf8", "casos_que_no_son_objetos", "agregados_numero", "puntaje_booleano"])
    def test_resultados_mal_formados_rechazan_una_sola_vez(self, compuerta, tmp_path, contenido):
        # La decisión se escribe ANTES de leer los resultados: una excepción ahí dejaría la marca sin decisión registrada.
        compuerta.congelar("verificar-cita", tmp_path / "dev.json", sin_juez_externo="prueba")
        compuerta.reservar("verificar-cita")
        (tmp_path / "roto.json").write_bytes(contenido)
        assert compuerta.holdout("verificar-cita", refrescar(tmp_path / "roto.json"), []) == 1
        assert historial(tmp_path).count("\tholdout\t") == 1 and "RECHAZADA" in historial(tmp_path)

    # ---- I-4: un solo intento y una sola decisión, con procesos simultáneos reales

    def _carrera(self, compuerta, tmp_path, accion, *extra, procesos=8):
        guion = tmp_path / "carrera.py"
        guion.write_text(CARRERA, encoding="utf-8")
        carpeta = tmp_path / "carrera"
        carpeta.mkdir()
        entorno = {**os.environ, "ITOSTACK_PROYECTO": str(tmp_path / "proyecto"), "PYTHONUTF8": "1"}
        hijos = [subprocess.Popen([sys.executable, str(guion), str(RAIZ / "evals"), str(compuerta.COMPUERTA), str(carpeta / f"p{i}.txt"), accion, *extra],
                                  env=entorno, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for i in range(procesos)]
        limite = time.time() + 120
        while len(list(carpeta.glob("*.listo"))) < procesos and time.time() < limite:
            time.sleep(0.05)
        (carpeta / "ya").write_text("")
        for hijo in hijos:
            hijo.wait(timeout=120)
        return sorted(int((carpeta / f"p{i}.txt").read_text()) for i in range(procesos))

    def test_carrera_de_reservas_reserva_exactamente_una(self, compuerta, tmp_path):
        compuerta.congelar("verificar-cita", tmp_path / "dev.json", sin_juez_externo="prueba")
        codigos = self._carrera(compuerta, tmp_path, "reservar")
        assert codigos.count(0) == 1 and codigos.count(1) == len(codigos) - 1
        assert historial(tmp_path).count("\tholdout-iniciado\t") == 1

    def test_carrera_de_decisiones_decide_exactamente_una_vez(self, compuerta, tmp_path):
        compuerta.congelar("verificar-cita", tmp_path / "dev.json", sin_juez_externo="prueba")
        assert compuerta.reservar("verificar-cita") == 0
        codigos = self._carrera(compuerta, tmp_path, "holdout", str(refrescar(tmp_path / "h.json")))
        assert codigos.count(0) == 1 and historial(tmp_path).count("\tholdout\t") == 1

    # ---- CR-4: la huella cubre lo que determina el caso, y nada más

    def test_la_configuracion_del_operador_no_cambia_la_huella(self, compuerta, tmp_path):
        antes = compuerta.huella("verificar-cita")
        (tmp_path / "proyecto" / ".itostack" / "config.json").write_text(json.dumps(CONFIG_OPERADOR), encoding="utf-8")
        assert compuerta.huella("verificar-cita") == antes

    @pytest.fixture
    def plugin_copia(self, compuerta, tmp_path, monkeypatch):
        copia = tmp_path / "plugin"
        shutil.copytree(RAIZ, copia, ignore=shutil.ignore_patterns("node_modules", "__pycache__", ".pytest_cache", ".hypothesis", "results", "compuerta"))
        monkeypatch.setattr(compuerta, "PLUGIN", copia)
        monkeypatch.setattr(compuerta, "EVALS", copia / "evals")
        monkeypatch.setattr(compuerta, "RUBRICAS", copia / "evals" / "rubricas")
        return copia

    @pytest.mark.parametrize("relativo", ["scripts/nucleo/config.py", "scripts/inicializar.py", "evals/_comun/preparar.sh", "evals/verificar-cita/pass-exacto/case.yaml",
                                          "evals/fixtures/sjf/basico.json", "evals/rubricas/por_skill.json", "skills/verificar-cita/SKILL.md", "hooks/guardia_escritura.py", "agents/juez-evals.md"])
    def test_la_huella_cambia_con_lo_que_determina_el_caso(self, compuerta, plugin_copia, relativo):
        antes = compuerta.huella("verificar-cita")
        archivo = plugin_copia / relativo
        archivo.write_bytes(archivo.read_bytes() + b"\n")
        assert compuerta.huella("verificar-cita") != antes

    def test_la_reserva_tiene_su_propia_huella(self, compuerta, plugin_copia):
        antes, reserva = compuerta.huella("verificar-cita"), compuerta.huella_holdout("verificar-cita")
        caso = sorted((plugin_copia / "evals" / "verificar-cita").glob("holdout-*"))[0] / "case.yaml"
        caso.write_bytes(caso.read_bytes() + b"\n")
        assert compuerta.huella("verificar-cita") == antes and compuerta.huella_holdout("verificar-cita") != reserva

    def test_el_caso_no_ve_la_configuracion_del_operador(self, tmp_path, monkeypatch):
        """Comprobación previa a revertir la configuración en la huella: con el andamiaje real (preparar.sh) el caso
        arranca con la configuración del plugin y la del operador no le llega."""
        sys.path.insert(0, str(RAIZ / "evals"))
        import autoprueba
        from nucleo import config as cfg

        try:
            bash = autoprueba.ubicar_bash()
        except SystemExit:
            pytest.skip("requiere Git Bash")
        operador = tmp_path / "operador"
        (operador / ".itostack").mkdir(parents=True)
        (operador / ".itostack" / "config.json").write_text(json.dumps(CONFIG_OPERADOR), encoding="utf-8")
        espacio = tmp_path / "espacio"
        espacio.mkdir()
        entorno = {k: v for k, v in os.environ.items() if not k.startswith("ITOSTACK_")}
        caso = RAIZ / "evals" / "verificar-cita" / "pass-exacto"
        preparado = subprocess.run([bash, str(caso / "preparar.sh")], cwd=espacio, env=entorno, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", timeout=300)
        assert preparado.returncode == 0, preparado.stderr
        monkeypatch.delenv("ITOSTACK_PROYECTO", raising=False)
        monkeypatch.delenv("ITOSTACK_MODO", raising=False)
        assert cfg.raiz_proyecto(espacio) == espacio.resolve()
        efectiva = cfg.cargar(espacio)
        for clave, valor in cfg.CONFIG_DEFECTO.items():
            if clave not in {"modo", "sjf", "navegador"}:
                assert efectiva[clave] == valor, clave
        assert efectiva["modo"] == "fixture"
        fixture = RAIZ / "evals" / "fixtures" / "sjf" / "basico.json"
        assert os.path.normcase(str(Path(efectiva["sjf"]["fixture"]).resolve())) == os.path.normcase(str(fixture.resolve()))
        # El comportamiento, no solo el archivo: la lista curada del operador abre la salida en su proyecto y no en el caso.
        envio = {"tool_name": "mcp__Slack__slack_send_message", "tool_input": {"text": "listo"}, "permission_mode": "auto"}
        assert decision(correr_hook("guardia_externo.py", {**envio, "cwd": str(operador)}, cwd=operador)) is None
        assert decision(correr_hook("guardia_externo.py", {**envio, "cwd": str(espacio)}, cwd=espacio)) == "deny"
        # Límite conocido (CR-3 en 0.2.0): una variable ITOSTACK_PROYECTO en el entorno de la corrida sí redirige el caso.
        monkeypatch.setenv("ITOSTACK_PROYECTO", str(operador))
        assert cfg.raiz_proyecto(espacio) == operador.resolve()


# ---------------------------------------------------------------- 0.2.0: la reserva contaminada no admite holdouts

class TestReservaContaminada:
    """Decisión del operador (2026-11-19): los casos holdout-* actuales están contaminados. No se corre ningún holdout
    hasta que CR-2 los aísle; la compuerta lo impide por estructura, no por promesa."""

    def _real(self, compuerta, monkeypatch):
        monkeypatch.setattr(compuerta, "RESERVA_ESTADO", RAIZ / "evals" / "reserva.json")

    def test_la_reserva_versionada_esta_contaminada(self, compuerta, monkeypatch):
        self._real(compuerta, monkeypatch)
        assert "contaminada" in compuerta.reserva_bloqueada()

    def test_contaminada_no_reserva_ni_registra_ni_corre(self, compuerta, tmp_path, monkeypatch):
        self._real(compuerta, monkeypatch)
        assert compuerta.congelar("verificar-cita", tmp_path / "dev.json", sin_juez_externo="prueba") == 0  # desarrollo sigue
        assert compuerta.reservar("verificar-cita") == 1
        assert compuerta.holdout("verificar-cita", refrescar(tmp_path / "h.json"), []) == 1
        assert compuerta.holdout("verificar-cita", None, []) == 1  # tampoco lanza claude plugin eval
        marcas = [p.name for p in (tmp_path / "compuerta").iterdir() if p.suffix in {".consumido", ".decidido"}]
        assert marcas == [] and "holdout" not in historial(tmp_path).replace("holdout-", "")

    @PROPIEDADES
    @given(datos=JSON)
    def test_propiedad_solo_aislada_admite_un_holdout(self, compuerta, tmp_path, datos):
        (tmp_path / "reserva.json").write_text(json.dumps(datos), encoding="utf-8")
        admitida = isinstance(datos, dict) and datos.get("estado") == "aislada"
        assert (compuerta.reserva_bloqueada() is None) == admitida

    def test_estado_ilegible_bloquea(self, compuerta, tmp_path):
        (tmp_path / "reserva.json").write_bytes(bytes([0xFF, 0x7B]))
        assert compuerta.reserva_bloqueada()
        (tmp_path / "reserva.json").unlink()
        assert compuerta.reserva_bloqueada()
