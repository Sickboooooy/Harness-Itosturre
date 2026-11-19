"""Contrato técnico de CR-3 (docs/contrato-cr3.md): los esquemas describen la realidad observada y son estrictos.

Propiedad verificable: las dos salidas reales de `claude plugin eval` guardadas en tests/datos/ cumplen el esquema de
resultados, y cualquier salida a la que le falte un campo obligatorio, le sobre uno desconocido o cambie un tipo lo
incumple. Así la compuerta de CR-3 podrá rechazar (BLOCKED) lo que no reconoce en vez de interpretarlo.
"""

import copy
import json

import pytest

from conftest import RAIZ

jsonschema = pytest.importorskip("jsonschema")

ESQUEMAS = RAIZ / "evals" / "esquemas"
REALES = {
    "linux-sin-sesion": RAIZ / "tests" / "datos" / "resultado_claude_plugin_eval.json",
    "windows-sandbox-bloqueado": RAIZ / "tests" / "datos" / "resultado_plugin_eval_windows_bloqueado.json",
}


def validador(nombre):
    esquema = json.loads((ESQUEMAS / nombre).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(esquema)
    return jsonschema.Draft202012Validator(esquema)


def real(nombre):
    return json.loads(REALES[nombre].read_text(encoding="utf-8"))


def rutas_obligatorias(esquema, raiz, datos, ruta=()):
    """Cada campo obligatorio presente en `datos`, como ruta (para quitarlo uno por uno)."""
    if "$ref" in esquema:
        esquema = raiz["$defs"][esquema["$ref"].split("/")[-1]]
    if esquema.get("type") == "object" and isinstance(datos, dict):
        for campo in esquema.get("required", []):
            if campo in datos:
                yield ruta + (campo,)
                yield from rutas_obligatorias(esquema["properties"][campo], raiz, datos[campo], ruta + (campo,))
    elif esquema.get("type") == "array" and isinstance(datos, list) and datos:
        yield from rutas_obligatorias(esquema["items"], raiz, datos[0], ruta + (0,))


def test_los_esquemas_son_json_schema_validos():
    validador("resultado-plugin-eval.schema.json")
    validador("manifiesto-holdout.schema.json")


@pytest.mark.parametrize("nombre", sorted(REALES))
def test_las_salidas_reales_cumplen_el_esquema(nombre):
    errores = list(validador("resultado-plugin-eval.schema.json").iter_errors(real(nombre)))
    assert errores == [], [e.message for e in errores]


@pytest.mark.parametrize("nombre", sorted(REALES))
def test_quitar_cualquier_campo_obligatorio_incumple(nombre):
    v = validador("resultado-plugin-eval.schema.json")
    rutas = list(rutas_obligatorias(v.schema, v.schema, real(nombre)))
    assert len(rutas) > 30  # recorre de verdad suite, casos, corridas y calificadores
    for ruta in rutas:
        datos = real(nombre)
        padre = datos
        for paso in ruta[:-1]:
            padre = padre[paso]
        del padre[ruta[-1]]
        assert not v.is_valid(datos), ruta


@pytest.mark.parametrize("donde", [(), ("suite",), ("cases", 0), ("cases", 0, "arms", "with", 0), ("aggregates",)])
def test_un_campo_desconocido_incumple(donde):
    datos = real("linux-sin-sesion")
    destino = datos
    for paso in donde:
        destino = destino[paso]
    destino["campoNuevo"] = 1
    assert not validador("resultado-plugin-eval.schema.json").is_valid(datos)


@pytest.mark.parametrize("ruta,valor", [(("partial",), "false"), (("cases", 0, "arms", "with", 0, "score"), True),
                                        (("cases", 0, "arms", "with", 0, "score"), 1.5), (("schemaVersion",), 2),
                                        (("cases", 0, "arms", "with", 0, "error"), None), (("suite", "ablation"), "otra")])
def test_un_tipo_o_valor_fuera_del_esquema_incumple(ruta, valor):
    datos = real("linux-sin-sesion")
    padre = datos
    for paso in ruta[:-1]:
        padre = padre[paso]
    padre[ruta[-1]] = valor
    assert not validador("resultado-plugin-eval.schema.json").is_valid(datos)


def test_las_dos_salidas_reales_son_fallas_de_infraestructura_con_puntaje():
    """Hecho observado que motiva la regla R6 del contrato: una corrida con `error` puede traer puntaje distinto de 0
    (calificadores negativos que «pasan» sin que el agente hiciera nada). La compuerta debe clasificarla BLOCKED."""
    linux = real("linux-sin-sesion")["cases"][0]["arms"]["with"][0]
    windows = real("windows-sandbox-bloqueado")["cases"][0]["arms"]["with"][0]
    assert linux["error"] and linux["score"] > 0 and real("linux-sin-sesion")["partial"] is True
    assert windows["error"] and windows["turns"] == 0 and windows["graders"] == []


def test_ejemplo_minimo_de_manifiesto():
    h = "a" * 64
    manifiesto = {
        "contrato": "itostack/holdout@1", "fecha": "2026-11-19T00:00:00+00:00", "skill": "verificar-cita",
        "candidata": {"huella": h, "version_plugin": "0.2.0", "huella_copia": h},
        "reserva": {"huella": h, "estado": "aislada"},
        "entorno": {"sistema": "Linux (WSL2)", "usuario_de_servicio": "itostack-compuerta", "python": "3.12", "variables": ["PATH", "HOME"], "path": "/usr/bin:/bin"},
        "evaluador": {"claude_version": "2.1.327", "argv": ["claude", "plugin", "eval"], "modelo": "m", "modelo_calificador_llm": "haiku",
                      "ablation": "none", "runs": 1, "concurrencia": 1, "sha256_resultados": h},
        "juez": {"familia": "openai", "herramienta": "codex", "modelo": "gpt-6.1-sol", "esfuerzo": "high", "version": "codex-cli 0.167", "sha256_opciones": h},
        "rubrica": {"archivo": "verificacion.md", "sha256": h, "criterios": 5},
        "casos": [{"id": h, "sha256_caso": h, "sha256_rubrica": h, "sha256_evaluador": h,
                   "corridas": [{"score": 1.0, "turns": 5, "error": "", "sha256_traza": h}], "sha256_artefacto": h,
                   "juicios": [{"sha256_respuesta": h, "estado": "APRUEBA", "puntaje": 10.0}], "estado": "ACEPTA"}],
        "decision": {"estado": "ACEPTADA", "motivo": "holdout 1.0 y juez aprueba cada caso"},
        "diario": {"cabeza_sha256": h, "entradas": 7},
    }
    v = validador("manifiesto-holdout.schema.json")
    assert v.is_valid(manifiesto)
    for clave in ("reserva", "evaluador", "juez"):
        roto = copy.deepcopy(manifiesto)
        del roto[clave]
        assert not v.is_valid(roto)
    roto = copy.deepcopy(manifiesto)
    roto["reserva"]["estado"] = "contaminada"
    assert not v.is_valid(roto)  # un manifiesto de holdout solo existe con la reserva aislada
    # Cada caso ata su veredicto a su definición, su rúbrica autorizada, su evaluador y sus artefactos (decisión 5 del
    # operador): quitar cualquiera de esos vínculos invalida el manifiesto; un nombre legible en lugar del id también.
    for vinculo in ("id", "sha256_caso", "sha256_rubrica", "sha256_evaluador", "sha256_artefacto", "juicios"):
        roto = copy.deepcopy(manifiesto)
        del roto["casos"][0][vinculo]
        assert not v.is_valid(roto), vinculo
    roto = copy.deepcopy(manifiesto)
    roto["casos"][0]["id"] = "verificar-cita.holdout-x"
    assert not v.is_valid(roto)
