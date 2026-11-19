"""CR-3.2a · orquestador del holdout: contrato de resultados, entorno, manifiesto, diario y transacción (pruebas sintéticas).

Todo con una reserva SINTÉTICA en un directorio temporal: ninguna prueba toca la reserva real (que está contaminada y
el orquestador se niega a usar). Propiedades críticas:
- una falla de infraestructura nunca produce una evaluación válida (ni ACEPTADA ni RECHAZADA), sea cual sea el puntaje;
- un resultado fuera de contrato se bloquea, nunca se interpreta;
- cada veredicto queda atado a su caso, su rúbrica autorizada, su evaluador y sus artefactos, y cualquier alteración del
  manifiesto, el diario o los resultados se detecta;
- el entorno de la evaluación se construye desde cero y las variables prohibidas nunca pasan.
"""

import copy
import json
import sys
import tempfile
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from conftest import RAIZ

sys.path.insert(0, str(RAIZ / "evals"))
import orquestador as orq  # noqa: E402
from nucleo import esquema  # noqa: E402

PROPIEDADES = settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
H = "a" * 64
CALIFICADORES = [("archivo", 3), ("mensaje", 1), ("no-afirma", 2)]
REALES = {"linux": RAIZ / "tests" / "datos" / "resultado_claude_plugin_eval.json",
          "windows": RAIZ / "tests" / "datos" / "resultado_plugin_eval_windows_bloqueado.json"}


def corrida(aprobados=(True, True, True), turns=3, error="", score=None, pesos=None):
    pesos = pesos or [w for _, w in CALIFICADORES]
    graders = [{"name": n, "passed": p, "weight": w, "explanation": "ok" if p else "no", "withOnly": False, "scored": True}
               for (n, _), p, w in zip(CALIFICADORES, aprobados, pesos)]
    total = sum(g["weight"] for g in graders)
    calculado = sum(g["weight"] for g in graders if g["passed"]) / total
    puntaje = calculado if score is None else score
    return {"score": puntaje, "passed": puntaje == 1, "turns": turns, "costUsd": 0.01, "judgeCostUsd": 0, "durationSeconds": 4, "startedAt": "2026-11-19T00:00:00Z",
            "error": error, "tracePath": "", "skippedPaidGraders": False, "graders": graders}


def resultado(casos, skill="sintetica", **suite):
    cases = []
    for nombre, corridas in casos.items():
        media = sum(c["score"] for c in corridas) / len(corridas) if corridas else 0
        cases.append({"name": nombre, "dir": f"evals/{nombre}", "source": "case_yaml", "promptMarkdown": "caso sintético", "runsPerCase": 1,
                      "timeoutSeconds": 600, "maxTurns": 25, "graders": [{"name": n, "type": "regex", "weight": w, "config": {}} for n, w in CALIFICADORES],
                      "arms": {"with": corridas}, "aggregates": {"score": media, "passRate": media}})
    base = {"root": "/ejecutor/copia", "ablation": "none", "modelOverride": "claude-haiku-5-5", "caseFilter": f"{skill}.*", "threshold": 1, "concurrency": 1,
            "plugins": [{"name": "itostack", "version": "0.2.0", "path": "/ejecutor/copia"}]}
    base.update(suite)
    return {"schemaVersion": 1, "claudeVersion": "2.1.327", "startedAt": "2026-11-19T00:00:00Z", "durationSeconds": 10, "costUsd": 0.05, "partial": False,
            "suite": base, "cases": cases, "aggregates": {"casesTotal": len(cases), "casesPassed": 0, "overallScore": 0, "overallPassRate": 0}}


def solicitud(casos=("sintetica.a", "sintetica.b"), **extra):
    datos = {"skill": "sintetica", "casos": frozenset(casos), "runs": 1, "modelo": "claude-haiku-5-5", "claude_version": "2.1.327",
             "plugin_path": "/ejecutor/copia", "plugin_version": "0.2.0"}
    datos.update(extra)
    return orq.Solicitud(**datos)


def exito():
    return resultado({"sintetica.a": [corrida()], "sintetica.b": [corrida()]})


# ---------------------------------------------------------------- validador mínimo de JSON Schema

JSON = st.recursive(st.none() | st.booleans() | st.integers(-3, 10) | st.floats(min_value=0.01, max_value=0.99) | st.text(max_size=6),
                    lambda h: st.lists(h, max_size=3) | st.dictionaries(st.text(max_size=8), h, max_size=3), max_leaves=12)


def rutas(valor, ruta=()):
    yield ruta
    if isinstance(valor, dict):
        for k, v in valor.items():
            yield from rutas(v, ruta + (k,))
    elif isinstance(valor, list):
        for i, v in enumerate(valor):
            yield from rutas(v, ruta + (i,))


class TestEsquemaMinimo:
    def test_las_salidas_reales_cumplen(self):
        for ruta in REALES.values():
            assert esquema.errores(json.loads(ruta.read_text(encoding="utf-8")), orq.ESQUEMA_RESULTADOS) == []

    @PROPIEDADES
    @given(st.data())
    def test_coincide_con_jsonschema_como_oraculo(self, datos):
        jsonschema = pytest.importorskip("jsonschema")
        base = datos.draw(st.sampled_from([exito(), json.loads(REALES["linux"].read_text(encoding="utf-8"))]))
        valor = copy.deepcopy(base)
        ruta = datos.draw(st.sampled_from([r for r in rutas(valor) if r]))
        padre = valor
        for paso in ruta[:-1]:
            padre = padre[paso]
        if datos.draw(st.booleans()) and isinstance(padre, dict):
            del padre[ruta[-1]]
        else:
            padre[ruta[-1]] = datos.draw(JSON)
        oraculo = jsonschema.Draft202012Validator(orq.ESQUEMA_RESULTADOS).is_valid(valor)
        assert (esquema.errores(valor, orq.ESQUEMA_RESULTADOS) == []) == oraculo


# ---------------------------------------------------------------- contrato de resultados (R1–R8)

class TestContratoDeResultados:
    def test_exito_sintetico_es_aceptable(self):
        c = orq.clasificar_resultados(exito(), solicitud())
        assert c.estado == "ACEPTABLE" and {e.estado for e in c.casos.values()} == {orq.ACEPTA}

    def test_fallo_de_la_candidata_es_rechazada(self):
        c = orq.clasificar_resultados(resultado({"sintetica.a": [corrida()], "sintetica.b": [corrida((True, False, True))]}), solicitud())
        assert c.estado == "RECHAZADA" and c.casos["sintetica.b"].estado == orq.RECHAZA

    @pytest.mark.parametrize("nombre", sorted(REALES))
    def test_las_fallas_reales_de_infraestructura_nunca_son_evaluacion_valida(self, nombre):
        """Regresión: la salida de Linux trae puntaje 0.2857 con «Not logged in»; la de Windows, 0 turnos."""
        datos = json.loads(REALES[nombre].read_text(encoding="utf-8"))
        suite = datos["suite"]
        s = orq.Solicitud("verificar-cita", frozenset(c["name"] for c in datos["cases"]), len(datos["cases"][0]["arms"]["with"]), suite["modelOverride"],
                          datos["claudeVersion"], suite["plugins"][0]["path"], suite["plugins"][0]["version"], suite["caseFilter"])
        c = orq.clasificar_resultados(datos, s)
        assert c.estado == orq.INFRAESTRUCTURA
        assert c.reintentable == (nombre == "windows")  # en Windows el agente no llegó a correr (0 turnos)

    @PROPIEDADES
    @given(st.data(), st.sampled_from(["error", "sin_turnos", "calificador_lanzo", "omitidos_por_costo", "parcial"]))
    def test_una_falla_de_infraestructura_nunca_produce_una_evaluacion_valida(self, datos, falla):
        casos = {}
        for nombre in ("sintetica.a", "sintetica.b"):
            casos[nombre] = [corrida(tuple(datos.draw(st.booleans()) for _ in CALIFICADORES), turns=datos.draw(st.integers(1, 9)))]
        valor = resultado(casos)
        afectada = valor["cases"][datos.draw(st.integers(0, 1))]["arms"]["with"][0]
        if falla == "error":
            afectada["error"] = "exit 1: " + datos.draw(st.text(min_size=1, max_size=20))
        elif falla == "sin_turnos":
            afectada["turns"] = 0
        elif falla == "calificador_lanzo":
            afectada["graders"][datos.draw(st.integers(0, 2))]["explanation"] = "grader threw: judge call failed"
        elif falla == "omitidos_por_costo":
            afectada["skippedPaidGraders"] = True
        else:
            valor["partial"], valor["partialReason"] = True, "auth_failed"
        c = orq.clasificar_resultados(valor, solicitud())
        assert c.estado == orq.INFRAESTRUCTURA

    @pytest.mark.parametrize("alteracion", [
        "version_claude", "modelo", "filtro", "ablacion", "concurrencia", "umbral", "ruta_plugin", "caso_extra", "caso_faltante",
        "caso_repetido", "corridas_de_mas", "brazo_sin_plugin", "calificadores_ajenos", "puntaje_incoherente", "campo_desconocido",
        "version_de_esquema", "puntaje_booleano"])
    def test_un_resultado_fuera_de_contrato_se_bloquea(self, alteracion):
        valor = exito()
        caso, primera = valor["cases"][0], valor["cases"][0]["arms"]["with"][0]
        cambios = {
            "version_claude": lambda: valor.update(claudeVersion="2.2.0"),
            "modelo": lambda: valor["suite"].update(modelOverride="otro"),
            "filtro": lambda: valor["suite"].update(caseFilter="*"),
            "ablacion": lambda: valor["suite"].update(ablation="with-without"),
            "concurrencia": lambda: valor["suite"].update(concurrency=2),
            "umbral": lambda: valor["suite"].update(threshold=0.5),
            "ruta_plugin": lambda: valor["suite"]["plugins"][0].update(path="/otra/copia"),
            "caso_extra": lambda: valor["cases"].append(dict(copy.deepcopy(caso), name="sintetica.c")),
            "caso_faltante": lambda: valor["cases"].pop(),
            "caso_repetido": lambda: valor["cases"].append(copy.deepcopy(caso)),
            "corridas_de_mas": lambda: caso["arms"]["with"].append(corrida()),
            "brazo_sin_plugin": lambda: caso["arms"].update(without=[corrida()]),
            "calificadores_ajenos": lambda: primera["graders"][0].update(name="otro"),
            "puntaje_incoherente": lambda: primera.update(score=0.5),
            "campo_desconocido": lambda: primera.update(nuevo=1),
            "version_de_esquema": lambda: valor.update(schemaVersion=2),
            "puntaje_booleano": lambda: primera.update(score=True),
        }
        cambios[alteracion]()
        assert orq.clasificar_resultados(valor, solicitud()).estado == orq.FUERA_DE_CONTRATO

    @PROPIEDADES
    @given(st.lists(st.tuples(st.booleans(), st.integers(1, 5)), min_size=3, max_size=3), st.floats(min_value=0.001, max_value=0.2))
    def test_r7_el_puntaje_debe_ser_el_recalculado(self, calificadores, desvio):
        aprobados, pesos = zip(*calificadores)
        valor = resultado({"sintetica.a": [corrida(aprobados, pesos=list(pesos))], "sintetica.b": [corrida()]})
        assert orq.clasificar_resultados(valor, solicitud()).estado in {"ACEPTABLE", "RECHAZADA"}
        primera = valor["cases"][0]["arms"]["with"][0]
        primera["score"] = primera["score"] - desvio if primera["score"] >= desvio else primera["score"] + desvio
        assert orq.clasificar_resultados(valor, solicitud()).estado == orq.FUERA_DE_CONTRATO


# ---------------------------------------------------------------- entorno e invocación

NOMBRES_SEGUROS = ["PATH", "HOME", "LANG", "TMPDIR", "CLAUDE_CODE_OAUTH_TOKEN", "TERM"]
NOMBRES_PROHIBIDOS = ["ITOSTACK_PROYECTO", "ITOSTACK_MODO", "PYTHONPATH", "PYTHONSTARTUP", "NODE_OPTIONS", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"]


class TestEntorno:
    @PROPIEDADES
    @given(st.dictionaries(st.sampled_from(NOMBRES_SEGUROS + NOMBRES_PROHIBIDOS + ["AWS_SECRET_ACCESS_KEY", "GH_TOKEN", "OTRA"]), st.text(max_size=5)),
           st.lists(st.sampled_from(NOMBRES_SEGUROS), unique=True))
    def test_solo_pasa_lo_permitido_y_nunca_lo_prohibido(self, base, permitidas):
        entorno, nombres = orq.construir_entorno(base, permitidas, {"LANG": "C.UTF-8"})
        assert set(entorno) <= set(permitidas) | {"LANG"} and nombres == sorted(entorno)
        assert not any(orq.PROHIBIDAS.match(n) for n in entorno) and "AWS_SECRET_ACCESS_KEY" not in entorno

    @pytest.mark.parametrize("nombre", NOMBRES_PROHIBIDOS)
    def test_una_prohibida_en_la_configuracion_es_un_error(self, nombre):
        with pytest.raises(ValueError):
            orq.construir_entorno({}, [nombre], {})
        with pytest.raises(ValueError):
            orq.construir_entorno({}, [], {nombre: "x"})

    def test_la_invocacion_no_publica_y_escribe_en_el_almacen(self, tmp_path):
        argv = orq.argv_evaluacion("claude", tmp_path / "copia", solicitud(), tmp_path / "almacen", "haiku", 2.0, {"Bash", "Write"})
        assert "--no-publish" in argv and "--publish-report" not in argv
        for opcion, valor in (("--ablation", "none"), ("--concurrency", "1"), ("--judge-model", "haiku"), ("--case", "sintetica.*")):
            assert argv[argv.index(opcion) + 1] == valor
        for opcion in ("--output-dir", "--json"):
            assert Path(argv[argv.index(opcion) + 1]).is_relative_to(tmp_path / "almacen")


# ---------------------------------------------------------------- diario encadenado

class TestDiario:
    def _diario(self, tmp_path, n=4):
        diario = orq.Diario(tmp_path / "diario.jsonl")
        for i in range(n):
            diario.anotar(f"evento{i}", {"i": i})
        return diario

    def test_un_diario_intacto_se_verifica(self, tmp_path):
        diario = self._diario(tmp_path)
        cabeza, cantidad, errores = orq.verificar_diario(diario.ruta)
        assert errores == [] and cantidad == 4 and cabeza == diario.entradas()[-1]["huella"]

    @pytest.mark.parametrize("alteracion", ["editar", "quitar", "reordenar", "insertar"])
    def test_cualquier_alteracion_se_detecta(self, tmp_path, alteracion):
        diario = self._diario(tmp_path)
        lineas = diario.ruta.read_text(encoding="utf-8").splitlines()
        if alteracion == "editar":
            lineas[1] = lineas[1].replace('"i": 1', '"i": 7')
        elif alteracion == "quitar":
            del lineas[1]
        elif alteracion == "reordenar":
            lineas[1], lineas[2] = lineas[2], lineas[1]
        else:
            lineas.insert(2, lineas[1])
        diario.ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        assert orq.verificar_diario(diario.ruta)[2]


# ---------------------------------------------------------------- la transacción (A3-1, A3-2)

RUBRICA = RAIZ / "evals" / "rubricas" / "verificacion.md"
ARTEFACTO = b"Informe sintetico. VEREDICTO PASS con evidencia capturada."


def respuesta_juez(aprueba=True):
    criterios = [{"numero": i, "criterio": "c", "cumple": "si" if aprueba or i > 1 else "no", "evidencia": "«VEREDICTO PASS»"} for i in range(1, 6)]
    return {"criterios": criterios, "fallos_criticos": [], "observaciones": ""}


def preparar(base: Path, estado="aislada"):
    for caso in ("a", "b"):
        carpeta = base / "reserva" / "sintetica" / caso
        carpeta.mkdir(parents=True)
        (carpeta / "case.yaml").write_text(f"name: sintetica.{caso}\n# caso SINTÉTICO de prueba\n", encoding="utf-8")
    (base / "estado.json").write_text(json.dumps({"estado": estado}), encoding="utf-8")
    return orq.Orquestacion(
        skill="sintetica", reserva=base / "reserva", estado_reserva=base / "estado.json", almacen=base / "almacen", rubrica=RUBRICA,
        evaluador={"claude_version": "2.1.327", "argv": ["claude", "plugin", "eval"], "modelo": "claude-haiku-5-5", "modelo_calificador_llm": "haiku",
                   "ablation": "none", "runs": 1, "concurrencia": 1},
        juez={"familia": "openai", "herramienta": "codex", "modelo": "gpt-6.1-sol", "esfuerzo": "high", "version": "codex-cli 0.167", "sha256_opciones": H},
        candidata={"huella": "b" * 64, "version_plugin": "0.2.0", "huella_copia": "c" * 64, "ruta_copia": "/ejecutor/copia"}, huella_reserva="d" * 64,
        entorno={"sistema": "Linux", "usuario_de_servicio": "ejecutor", "python": "3.12", "variables": ["HOME", "LANG", "PATH"], "path": "/usr/bin:/bin"})


class Juez:
    """Juez falso que registra lo que recibe y responde según un guion."""

    def __init__(self, guion):
        self.guion, self.llamadas = list(guion), []

    def __call__(self, artefacto, rubrica):
        self.llamadas.append((artefacto, rubrica))
        return self.guion.pop(0) if len(self.guion) > 1 else self.guion[0]


def correr(o, datos, juez):
    return orq.ejecutar(o, lambda s: datos, lambda nombre: ARTEFACTO, juez)


class TestTransaccion:
    @pytest.mark.parametrize("estado", ["contaminada", "aislada?", ""])
    def test_una_reserva_no_aislada_no_se_toca(self, tmp_path, estado):
        o = preparar(tmp_path, estado)
        with pytest.raises(orq.ReservaNoAislada):
            correr(o, exito(), Juez([respuesta_juez()]))
        assert not o.almacen.exists()  # ni marca, ni diario: el intento no se consumió

    def test_la_reserva_real_contaminada_no_se_toca(self, tmp_path):
        o = preparar(tmp_path)
        o.estado_reserva = RAIZ / "evals" / "reserva.json"
        with pytest.raises(orq.ReservaNoAislada):
            correr(o, exito(), Juez([respuesta_juez()]))

    def test_aceptada_y_verificable_con_la_rubrica_autorizada(self, tmp_path):
        o, juez = preparar(tmp_path), Juez([respuesta_juez()])
        m = correr(o, exito(), juez)
        assert m["decision"]["estado"] == "ACEPTADA" and orq.verificar_manifiesto(m, o.almacen) == []
        assert len(juez.llamadas) == 2 and all(r == RUBRICA.read_bytes() and a == ARTEFACTO for a, r in juez.llamadas)  # A3-2

    def test_el_juez_reprueba_un_caso(self, tmp_path):
        m = correr(preparar(tmp_path), exito(), Juez([respuesta_juez(), respuesta_juez(aprueba=False)]))
        assert m["decision"]["estado"] == "RECHAZADA" and sorted(c["estado"] for c in m["casos"]) == ["ACEPTA", "RECHAZA"]

    def test_un_juez_fuera_de_contrato_deja_pendiente_y_reintenta(self, tmp_path):
        o, juez = preparar(tmp_path), Juez([[]])
        m = correr(o, exito(), juez)
        assert m["decision"]["estado"] == "PENDIENTE_DE_JUICIO" and all(len(c["juicios"]) == 1 + o.reintentos_juez for c in m["casos"])

    def test_un_juez_blocked_y_luego_valido(self, tmp_path):
        m = correr(preparar(tmp_path), exito(), Juez([None, respuesta_juez(), respuesta_juez()]))
        assert m["decision"]["estado"] == "ACEPTADA" and [len(c["juicios"]) for c in m["casos"]] == [2, 1]

    @pytest.mark.parametrize("turnos,decision", [(2, "INCONCLUSA"), (0, "REINTENTABLE")])
    def test_una_falla_de_infraestructura_no_se_juzga_ni_acepta(self, tmp_path, turnos, decision):
        datos = resultado({"sintetica.a": [corrida(turns=turnos, error="exit 1: Not logged in")], "sintetica.b": [corrida(turns=turnos)]})
        juez = Juez([respuesta_juez()])
        m = correr(preparar(tmp_path), datos, juez)
        assert m["decision"]["estado"] == decision and juez.llamadas == [] and orq.verificar_manifiesto(m, tmp_path / "almacen") == []

    def test_un_resultado_fuera_de_contrato_es_inconcluso_y_no_se_juzga(self, tmp_path):
        datos = exito()
        datos["claudeVersion"] = "9.9.9"
        juez = Juez([respuesta_juez()])
        m = correr(preparar(tmp_path), datos, juez)
        assert m["decision"]["estado"] == "INCONCLUSA" and juez.llamadas == [] and all(c["estado"] == "BLOCKED" for c in m["casos"])

    def test_el_fallo_de_la_candidata_rechaza_sin_juzgar_ese_caso(self, tmp_path):
        datos = resultado({"sintetica.a": [corrida()], "sintetica.b": [corrida((False, True, True))]})
        juez = Juez([respuesta_juez()])
        m = correr(preparar(tmp_path), datos, juez)
        assert m["decision"]["estado"] == "RECHAZADA" and len(juez.llamadas) == 1

    def test_un_solo_intento(self, tmp_path):
        o = preparar(tmp_path)
        correr(o, exito(), Juez([respuesta_juez()]))
        with pytest.raises(orq.IntentoConsumido):
            correr(o, exito(), Juez([respuesta_juez()]))

    @pytest.mark.parametrize("alteracion", ["estado_del_caso", "evaluador", "rubrica", "decision", "diario", "resultados", "quitar_juicio"])
    def test_cualquier_alteracion_posterior_se_detecta(self, tmp_path, alteracion):
        o = preparar(tmp_path)
        m = correr(o, resultado({"sintetica.a": [corrida()], "sintetica.b": [corrida((True, False, True))]}), Juez([respuesta_juez()]))
        caso = next(c for c in m["casos"] if c["estado"] == "RECHAZA")
        if alteracion == "estado_del_caso":
            caso["estado"] = "ACEPTA"
        elif alteracion == "evaluador":
            m["evaluador"]["modelo"] = "otro"
        elif alteracion == "rubrica":
            caso["sha256_rubrica"] = "e" * 64
        elif alteracion == "decision":
            m["decision"]["estado"] = "ACEPTADA"
        elif alteracion == "diario":
            ruta = o.almacen / "diario.jsonl"
            ruta.write_text(ruta.read_text(encoding="utf-8").replace("RECHAZADA", "ACEPTADA"), encoding="utf-8")
        elif alteracion == "resultados":
            (o.almacen / "evaluacion" / "resultados.json").write_bytes(b"{}")
        else:
            aceptado = next(c for c in m["casos"] if c["estado"] == "ACEPTA")
            aceptado["juicios"] = []
        assert orq.verificar_manifiesto(m, o.almacen)

    @settings(max_examples=60, deadline=None)
    @given(st.lists(st.sampled_from(["acepta", "rechaza", "infra", "infra_sin_turnos"]), min_size=2, max_size=2),
           st.lists(st.sampled_from(["aprueba", "reprueba", "blocked"]), min_size=2, max_size=2))
    def test_propiedad_la_decision_sigue_las_reglas_y_siempre_se_verifica(self, evaluacion, juicios):
        corridas = {"acepta": lambda: corrida(), "rechaza": lambda: corrida((True, False, True)),
                    "infra": lambda: corrida(error="exit 1: falla"), "infra_sin_turnos": lambda: corrida(turns=0)}
        respuestas = {"aprueba": respuesta_juez(), "reprueba": respuesta_juez(aprueba=False), "blocked": []}
        datos = resultado({"sintetica.a": [corridas[evaluacion[0]]()], "sintetica.b": [corridas[evaluacion[1]]()]})
        guion = [respuestas[j] for j, e in zip(juicios, evaluacion) if e == "acepta" for _ in range(3 if j == "blocked" else 1)] or [respuesta_juez()]
        with tempfile.TemporaryDirectory() as base:
            o = preparar(Path(base))
            m = correr(o, datos, Juez(guion + [respuesta_juez()]))
            assert orq.verificar_manifiesto(m, o.almacen) == []
            decision = m["decision"]["estado"]
            hay_infra = any(e.startswith("infra") for e in evaluacion)
            if hay_infra:
                assert decision in {"INCONCLUSA", "REINTENTABLE"}  # nunca una evaluación válida
            if decision == "ACEPTADA":
                assert set(evaluacion) == {"acepta"} and set(juicios) == {"aprueba"}
            if decision == "REINTENTABLE":
                assert set(evaluacion) <= {"infra_sin_turnos", "acepta", "rechaza"} and all(r["turns"] == 0 for c in m["casos"] for r in c["corridas"])
