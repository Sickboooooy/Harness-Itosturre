"""Genera la matriz de invariantes de itostack 0.1.2 (paso 5 del protocolo de cierre) a partir de evidencia ejecutada.

Por cada invariante: corre sus pruebas nombradas, lee la evidencia en vivo (evidencia-vivo/*.json) y el pase de
mutantes (mutantes-cierre.txt), y escribe matriz-invariantes.md. El estado no se escribe a mano:
- «Demostrado»: alcance demostrable + todas sus pruebas pasan + su evidencia en vivo (si la tiene) es PASS + todos
  sus mutantes (al menos uno) detectados.
- «Parcial» / «No demostrado»: el alcance de 0.1.2 no lo permite; se dice qué falta y qué cambio de 0.2.0 lo cubre.
- «FALLA»: alguna prueba o evidencia requerida falla.

Uso (raíz del repo): python -I pruebas-manuales/fase-codex/matriz_invariantes.py
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PLUGIN = AQUI.parents[1] / "itostack"
VIVO = AQUI / "evidencia-vivo"
T = "tests/test_auditoria_codex.py"

MATRIZ = [
    # ---------------------------------------------------------------- controles de seguridad
    {"id": "I-1", "grupo": "Controles de seguridad", "invariante": "Ninguna acción hacia afuera sin compuerta humana efectiva",
     "criterio": "En default/acceptEdits/plan el guardia pregunta; en auto/dontAsk/bypassPermissions o sin dato deniega; la lista curada no salta el control de citas. En vivo: sesiones reales `claude -p` en cada modo con el push preaprobado.",
     "pruebas": [f"{T}::TestCompuertaHumana", "tests/test_guardias.py::TestGuardiaExterno", "tests/test_guardias.py::TestGuardiaBash"],
     "vivo": "compuerta-humana-vivo.json", "mutantes": "I-1", "alcance": "demostrable",
     "limites": "Cubre las acciones que reconocen los guardias (push a main/master, push forzado, envíos MCP). Una salida que ningún patrón reconoce no pasa por la compuerta; la lista de patrones no es exhaustiva."},
    {"id": "I-2", "grupo": "Controles de seguridad", "invariante": "En producción, los datos no salen de la máquina",
     "criterio": "Sin `\"entorno\": \"desarrollo\"`, `revisar_codex.py` sale con 3 sin invocar a Codex. Ollama: solo hosts locales exactos, sin proxy del entorno y sin seguir redirecciones.",
     "pruebas": [f"{T}::TestRevisarCodex::test_sin_entorno_desarrollo_se_niega", f"{T}::TestOllamaLocal", f"{T}::TestCierre012::test_ollama_no_sigue_redirecciones"],
     "vivo": None, "mutantes": "I-2", "alcance": "demostrable",
     "limites": "Cubre los revisores de itostack. Otras herramientas de la sesión (MCP, WebFetch) dependen de I-1 y de la configuración de Claude Code."},
    {"id": "I-3", "grupo": "Controles de seguridad", "invariante": "El juez externo solo ve el mensaje",
     "criterio": "Opciones exactas del juez (sin shell, navegador, apps ni plugins; sandbox de solo lectura; directorio neutro vacío; artefactos sin ruta). En vivo: 0 intentos de herramienta (registro `--json` + enrutador en stderr) y canario ausente, con un control que sí registra intentos cuando la terminal existe.",
     "pruebas": [f"{T}::TestRevisarCodex::test_juez_aislado_sin_herramientas_y_con_puntaje_calculado"],
     "vivo": "aislamiento-juez-vivo.json", "mutantes": "I-3", "alcance": "demostrable",
     "limites": "Medido con codex-cli 0.167 y el modelo configurado; una versión nueva de Codex puede cambiar nombres de funciones o el registro. Repetir la medición al actualizar Codex."},
    # ---------------------------------------------------------------- integridad del holdout
    {"id": "I-4", "grupo": "Integridad del holdout", "invariante": "Un solo intento y una sola decisión por candidata",
     "criterio": "Reservar, congelar y decidir son transiciones únicas (creación exclusiva). Con 8 procesos simultáneos reales: exactamente una reserva y una decisión. Resultados mal formados deciden una sola vez, sin excepción.",
     "pruebas": [f"{T}::TestCompuertaConJuez::test_reserva_consume_el_intento_aunque_se_interrumpa", f"{T}::TestCompuertaConJuez::test_la_decision_se_escribe_una_sola_vez",
                 f"{T}::TestCompuertaConJuez::test_resultados_ilegibles_rechazan_y_consumen", f"{T}::TestCompuertaConJuez::test_marca_previa_impide_correr_sin_resultados",
                 f"{T}::TestRondaCuatro::test_congelar_es_una_transicion_unica", f"{T}::TestCierre012::test_carrera_de_reservas_reserva_exactamente_una",
                 f"{T}::TestCierre012::test_carrera_de_decisiones_decide_exactamente_una_vez", f"{T}::TestCierre012::test_resultados_mal_formados_rechazan_una_sola_vez",
                 "tests/test_mejora.py::test_compuerta_holdout_un_solo_intento"],
     "vivo": None, "mutantes": "I-4", "alcance": "demostrable",
     "limites": "Frente a invocaciones repetidas o simultáneas. No frente al borrado deliberado de las marcas: `evals/compuerta/` es escribible por el agente hasta CR-2 (almacén de decisiones de solo lectura para el agente)."},
    {"id": "I-5", "grupo": "Integridad del holdout", "invariante": "La reserva no es legible para quien mejora la skill",
     "criterio": "0.2.0 (CR-2): toda vía de lectura como el usuario del agente falla con «acceso denegado» del sistema operativo; centinela ausente de todo lo legible tras un holdout completo.",
     "pruebas": [f"{T}::TestReservaHoldout", f"{T}::TestRondaCuatro::test_get_content_en_minusculas_sobre_holdout", f"{T}::TestRondaCuatro::test_busqueda_desde_un_directorio_con_reserva",
                 f"{T}::TestRondaCuatro::test_ruta_con_variable_sin_expandir", f"{T}::TestRondaCinco::test_ruta_entrecomillada_con_espacios",
                 f"{T}::TestRondaCinco::test_holdout_en_mayusculas", f"{T}::TestRondaCinco::test_evals_en_mayusculas_en_windows"],
     "vivo": None, "mutantes": None,
     "alcance": "no demostrado: los guardias de 0.1.2 inspeccionan comandos como texto y siempre hay otra vía. Además, los 15 archivos de los casos `holdout-*` actuales los escribió el mismo agente y están en la historia de Git (2 commits): ya no son una reserva. Las pruebas listadas verifican la mitigación, no el invariante. Lo cubre CR-2.",
     "limites": "Tratar los casos `holdout-*` actuales como quemados; un ACEPTADA de 0.1.2 no demuestra generalización."},
    {"id": "I-6", "grupo": "Integridad del holdout", "invariante": "Lo congelado es inmutable y la huella cubre exactamente lo que determina el caso",
     "criterio": "Cambiar skill, scripts, hooks, agentes, rúbricas, fixtures, andamiaje o casos cambia la huella; la reserva tiene su propia huella; juez y exención no cambian tras congelar; no se re-congela. La configuración del operador no cambia la huella, y con el andamiaje real (`preparar.sh`) el caso no la ve (comprobación previa a revertir CR-4).",
     "pruebas": [f"{T}::TestCompuertaConJuez::test_cambiar_de_juez_tras_congelar_no_se_permite", f"{T}::TestCompuertaConJuez::test_reserva_cambiada_tras_congelar",
                 f"{T}::TestCompuertaConJuez::test_no_se_vuelve_a_congelar_la_misma_candidata", f"{T}::TestCompuertaConJuez::test_la_huella_cubre_rubricas_y_agentes",
                 f"{T}::TestCierre012::test_la_huella_cambia_con_lo_que_determina_el_caso", f"{T}::TestCierre012::test_la_reserva_tiene_su_propia_huella",
                 f"{T}::TestCierre012::test_la_configuracion_del_operador_no_cambia_la_huella", f"{T}::TestCierre012::test_el_caso_no_ve_la_configuracion_del_operador"],
     "vivo": None, "mutantes": ("I-6", "CR-4"), "alcance": "demostrable",
     "limites": "Condición de la corrida: sin `ITOSTACK_PROYECTO` ni `ITOSTACK_MODO` en el entorno de `claude plugin eval` (redirigen el caso a otro proyecto; la prueba lo caracteriza). `autoprueba.py` los quita; a mano es responsabilidad del operador hasta CR-3."},
    {"id": "I-7", "grupo": "Integridad del holdout", "invariante": "Aceptar exige desarrollo 1.0, holdout 1.0 en todos los casos y el visto bueno del juez de otra familia por caso, con la rúbrica de la skill y cobertura completa",
     "criterio": "Ningún veredicto o resultado ilegible, fuera de contrato, incompleto o mal formado produce aceptación ni excepción (R4-10 cerrado en la compuerta): exploración exhaustiva de campos obligatorios, propiedades con oráculo semántico y con `jsonschema` como oráculo independiente, y mutantes.",
     "pruebas": [f"{T}::TestContratoJuez", f"{T}::TestCompuertaConJuez", f"{T}::TestRondaCuatro::test_numero_debe_ser_entero_json",
                 f"{T}::TestRondaCuatro::test_aprobar_por_conteos_no_por_puntaje_redondeado", f"{T}::TestRondaCuatro::test_evidencia_en_orden_y_sin_descartar_tramos",
                 f"{T}::TestRondaCuatro::test_resultados_de_justo_antes_de_la_reserva_no_valen", f"{T}::TestRondaCinco::test_la_rubrica_debe_ser_la_asignada_a_la_skill",
                 f"{T}::TestRondaCinco::test_respuesta_del_juez_fuera_de_contrato", f"{T}::TestRondaCinco::test_respuesta_del_juez_completa",
                 f"{T}::TestCierre012::test_veredicto_fuera_de_contrato_es_blocked_en_la_compuerta", f"{T}::TestCierre012::test_veredicto_incompleto_es_blocked_no_reprobado",
                 f"{T}::TestCierre012::test_blocked_en_el_holdout_no_decide_ni_consume", f"{T}::TestCierre012::test_quitar_o_alterar_cualquier_campo_obligatorio_bloquea",
                 f"{T}::TestCierre012::test_si_sin_evidencia_verificada_no_cuenta_en_la_compuerta", f"{T}::TestCierre012::test_sin_rubrica_no_hay_aprobado",
                 f"{T}::TestCierre012::test_propiedad_cualquier_json_como_veredicto_es_blocked_sin_excepcion", f"{T}::TestCierre012::test_propiedad_aprobar_exige_contrato_completo",
                 f"{T}::TestCierre012::test_propiedad_el_validador_coincide_con_jsonschema", f"{T}::TestCierre012::test_propiedad_resultados_arbitrarios_no_lanzan"],
     "vivo": None, "mutantes": "I-7",
     "alcance": "parcial: demostrado para lo que la compuerta recibe (contrato, cobertura, rúbrica asignada, identidad del juez, fechas). No demostrada la procedencia: que los archivos entregados sean los de la corrida reservada y los artefactos de cada caso holdout. Lo cubre CR-3 (la compuerta produce resultados y veredictos).",
     "limites": "Una corrida BLOCKED del juez queda en la bitácora como «no aprobado» y veta esos artefactos para ese juez (falla cerrado); CR-3 distingue BLOCKED de reprobado."},
    # ---------------------------------------------------------------- exactitud de las citas jurídicas
    {"id": "I-8", "grupo": "Exactitud de las citas", "invariante": "Ninguna cita en un entregable sin evidencia PASS vigente o advertencia visible de no verificada",
     "criterio": "0.2.0 (CR-1): propiedad «el guardia del borrador deniega si y solo si hay un patrón de cita fuera de un marcador» + comprobación de entrega por manifiesto.",
     "pruebas": [f"{T}::TestMarcaNoVerificada", "tests/test_guardias.py::TestGuardiaEscritura"],
     "vivo": None, "mutantes": None,
     "alcance": "no demostrado por construcción: el guardia deduce de la prosa qué cita es cuál (heurístico). Las pruebas listadas son regresiones por caso, no una demostración. Lo cubre CR-1.",
     "limites": "No usar los entregables jurídicos de 0.1.2 sin revisión humana de cada cita."},
    {"id": "I-9", "grupo": "Exactitud de las citas", "invariante": "El rubro y la clave mostrados son los de la evidencia",
     "criterio": "0.2.0 (CR-1): propiedad «rubro, clave, órgano y época del entregable == evidencia» para borradores con marcadores.",
     "pruebas": [f"{T}::TestRubroContraEvidencia", f"{T}::TestRondaCuatro::test_casos_de_la_tercera_revision_se_rechazan", f"{T}::TestRondaCuatro::test_variantes_correctas_pasan",
                 f"{T}::TestRondaCinco::test_un_segundo_rubro_para_la_misma_cita_se_rechaza", f"{T}::TestRondaCinco::test_registro_y_clave_en_segmentos_distintos_son_dos_citas",
                 f"{T}::TestRondaCinco::test_comillas_interiores_de_otro_tipo", f"{T}::TestRondaCinco::test_rubro_declarado_con_puntos_propios_entre_varias_citas"],
     "vivo": None, "mutantes": None,
     "alcance": "parcial: con `ensamblar_documento.py` y marcadores el rubro sale de la evidencia; el texto escrito a mano se coteja con heurísticas que cubren los casos probados, no todos. Lo cubre CR-1.",
     "limites": "Idem I-8."},
    {"id": "I-10", "grupo": "Exactitud de las citas", "invariante": "El texto citado nunca cambia el estado de verificación (clase D-04)",
     "criterio": "0.2.0 (CR-1): las marcas ⚠/❌ solo las emite el renderizador; una marca escrita a mano en un borrador se deniega.",
     "pruebas": [f"{T}::TestMarcaNoVerificada", f"{T}::TestRondaCinco::test_marca_dentro_de_una_cita_de_varias_lineas_no_exime"],
     "vivo": None, "mutantes": None,
     "alcance": "parcial: las marcas cuentan solo fuera de comillas y pegadas a su grupo de citas (heurístico). Lo cubre CR-1.",
     "limites": "Idem I-8."},
    {"id": "I-11", "grupo": "Exactitud de las citas", "invariante": "La compuerta del lint nunca da verde sin cobertura",
     "criterio": "`lint --diff`: sin cambios, base inválida o archivo ilegible → 2; archivos nuevos sin rastrear examinados; codificación declarada respetada; cobertura informada.",
     "pruebas": [f"{T}::TestLintDiff", f"{T}::TestRondaCuatro::test_lint_respeta_la_codificacion_declarada", f"{T}::TestRondaCuatro::test_lint_con_archivo_ilegible_es_incompleto"],
     "vivo": None, "mutantes": "I-11", "alcance": "demostrable",
     "limites": "Cubre las reglas IT001–IT008; no es un análisis estático general."},
]


def correr_pruebas(nodos: list[str]) -> dict:
    entorno = {k: v for k, v in os.environ.items() if not k.startswith("ITOSTACK_")}
    entorno["PYTHONUTF8"] = "1"
    salida = subprocess.run([sys.executable, "-m", "pytest", *nodos, "-q", "-p", "no:cacheprovider"], cwd=PLUGIN, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", env=entorno, timeout=1200)
    cuenta = {k: int(n) for n, k in re.findall(r"(\d+) (passed|failed|skipped|error|errors)", salida.stdout)}
    return {"codigo": salida.returncode, "pasan": cuenta.get("passed", 0), "fallan": cuenta.get("failed", 0) + cuenta.get("error", 0) + cuenta.get("errors", 0),
            "omitidas": cuenta.get("skipped", 0)}


def leer_mutantes() -> list[tuple[str, str]]:
    ruta = AQUI / "mutantes-cierre.txt"
    if not ruta.is_file():
        return []
    return re.findall(r"^(DETECTADO|NO DETECTADO|MUTANTE INVÁLIDO|CONTROL FALLA)\s+(\S.*)$", ruta.read_text(encoding="utf-8", errors="replace"), re.M)


def mutantes_de(prefijos, todos) -> list[tuple[str, str]]:
    if not prefijos:
        return []
    prefijos = (prefijos,) if isinstance(prefijos, str) else prefijos
    return [(e, n) for e, n in todos if any(n.startswith(p + " ") for p in prefijos)]


def leer_vivo(nombre: str | None) -> dict | None:
    if not nombre:
        return None
    ruta = VIVO / nombre
    if not ruta.is_file():
        return {"veredicto": "AUSENTE", "fecha": None}
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return {"veredicto": datos.get("veredicto"), "fecha": datos.get("fecha"), "criterios": datos.get("criterios")}


def principal() -> int:
    todos = leer_mutantes()
    filas, detalle, fallas = [], [], 0
    for fila in MATRIZ:
        resultado = correr_pruebas(fila["pruebas"])
        muts = mutantes_de(fila["mutantes"], todos)
        vivo = leer_vivo(fila["vivo"])
        pruebas_ok = resultado["codigo"] == 0 and resultado["fallan"] == 0 and resultado["pasan"] > 0
        mut_ok = bool(muts) and all(e == "DETECTADO" for e, _ in muts)
        vivo_ok = vivo is None or vivo["veredicto"] == "PASS"
        if not pruebas_ok or (fila["alcance"] == "demostrable" and not (mut_ok and vivo_ok)):
            estado, fallas = "FALLA", fallas + 1
        elif fila["alcance"] == "demostrable":
            estado = "**Demostrado**"
        elif fila["alcance"].startswith("parcial"):
            estado = "Parcial"
        else:
            estado = "No demostrado"
        texto_mut = f"{sum(e == 'DETECTADO' for e, _ in muts)}/{len(muts)} detectados" if muts else "—"
        texto_vivo = f"{vivo['veredicto']} ({vivo['fecha']})" if vivo else "—"
        texto_pruebas = f"{resultado['pasan']} " + ("pasa" if resultado["pasan"] == 1 else "pasan") + (f", {resultado['fallan']} fallan" if resultado["fallan"] else "") + (f", {resultado['omitidas']} omitidas" if resultado["omitidas"] else "")
        filas.append(f"| {fila['id']} | {fila['invariante']} | {estado} | {texto_pruebas} | {texto_mut} | {texto_vivo} |")
        bloque = [f"### {fila['id']} · {fila['invariante']}", "", f"- **Estado:** {estado}" + ("" if fila["alcance"] == "demostrable" else f" — {fila['alcance']}"),
                  f"- **Criterio verificable:** {fila['criterio']}", f"- **Pruebas** ({texto_pruebas}):"]
        bloque += [f"  - `{n}`" for n in fila["pruebas"]]
        if muts:
            bloque.append(f"- **Mutantes** ({texto_mut}):")
            bloque += [f"  - {e}: {n}" for e, n in muts]
        if vivo:
            bloque.append(f"- **En vivo:** `evidencia-vivo/{fila['vivo']}` → {vivo['veredicto']}; criterios: " + ", ".join(f"{k} {'✔' if v else '✘'}" for k, v in (vivo.get("criterios") or {}).items()))
        bloque.append(f"- **Límites:** {fila['limites']}")
        detalle.append("\n".join(bloque))
    version = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    documento = "\n".join([
        f"# Matriz de invariantes · itostack {version}", "",
        f"Generada: {datetime.now(timezone.utc).isoformat(timespec='seconds')} con `python -I pruebas-manuales/fase-codex/matriz_invariantes.py` (no se edita a mano).", "",
        "Un invariante está **Demostrado** solo si su alcance lo permite en 0.1.2, todas sus pruebas nombradas pasan, su evidencia en vivo (si la tiene) es PASS y todos sus mutantes fueron detectados (las pruebas fallan con el defecto reintroducido). Lo demás es Parcial o No demostrado y va a «Límites conocidos» del CHANGELOG.", "",
        "**itostack 0.1.2 es una versión experimental de integración y evaluación cruzada con Codex. No es apta para producción jurídica.**", "",
        "| ID | Invariante | Estado | Pruebas | Mutantes | En vivo |", "|---|---|---|---|---|---|", *filas, "",
        "## Detalle", "", "\n\n".join(detalle), "",
        "## Reproducir", "",
        "- Batería: `bash pruebas-manuales/fase-codex/bateria_cierre.sh` → `bateria-cierre.txt`",
        "- Mutantes: `python -I pruebas-manuales/fase-codex/mutantes_cierre.py itostack` → `mutantes-cierre.txt`",
        "- Hallazgos de la ronda 4 contra la versión de cierre: `python -I pruebas-manuales/fase-codex/reproducir_r4.py itostack` → `reproduccion-r4.txt`",
        "- I-1 en vivo: `python -I pruebas-manuales/fase-codex/compuerta_humana_vivo.py itostack` (sesiones `claude -p` reales; remoto local)",
        "- I-3 en vivo: `python -I pruebas-manuales/fase-codex/aislamiento_juez_vivo.py itostack .` (requiere `\"entorno\": \"desarrollo\"`; envía material sintético a OpenAI)",
        "- Esta matriz: `python -I pruebas-manuales/fase-codex/matriz_invariantes.py`", "",
    ])
    (AQUI / "matriz-invariantes.md").write_text(documento, encoding="utf-8")
    print("\n".join(filas))
    print(f"\n{len(MATRIZ) - fallas}/{len(MATRIZ)} filas sin FALLA")
    return 0 if fallas == 0 else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(principal())
