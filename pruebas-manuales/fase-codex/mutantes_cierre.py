"""Pase de mutantes del cierre de 0.1.2: ¿las pruebas de la matriz detectan el defecto que dicen demostrar?

Para cada mutante: copia el plugin (sin node_modules) a un directorio temporal, reintroduce UN defecto con un reemplazo
exacto y corre solo las pruebas del invariante. «Detectado» = las pruebas fallan con el defecto. Un mutante no
detectado es una prueba que no demuestra su invariante.

Uso: python -I mutantes_cierre.py <raíz del plugin itostack> [cierre-0.1.2|cr1|reserva|cr12]
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN = Path(sys.argv[1]).resolve()
PRUEBAS = "tests/test_auditoria_codex.py"
GATE = "evals/compuerta_holdout.py"
JUEZ = "scripts/nucleo/juez.py"

# (invariante · defecto reintroducido, archivo, [(fragmento original, fragmento mutado), ...], filtro -k de pytest)
MUTANTES = [
    ("I-7 · R4-10: la compuerta no valida el contrato del veredicto guardado", GATE,
     [('contrato = contrato_juez.errores_contrato("juez", veredicto, guardado=True)', "contrato = []")],
     "test_veredicto_fuera_de_contrato_es_blocked_en_la_compuerta or test_propiedad_cualquier_json"),
    ("I-7 · R4-10a: fallos_criticos ausente se supone vacío", JUEZ,
     [('errores = errores_contrato("juez", respuesta_del_modelo(resultado)) if', 'errores = errores_contrato("juez", {"fallos_criticos": [], **respuesta_del_modelo(resultado)}) if'),
      ('fallos = [f for f in resultado["fallos_criticos"] if f.strip()]', 'fallos = [f for f in resultado.get("fallos_criticos", []) if f.strip()]')],
     "test_quitar_o_alterar_cualquier_campo_obligatorio_bloquea or test_propiedad_aprobar_exige_contrato_completo"),
    ("I-7 · un booleano o «sí» se lee como «si»", JUEZ,
     [('    if errores:\n        return _bloqueado(resultado, errores)\n    criterios = []',
       '    if errores and all("cumple" in e for e in errores):\n        resultado = dict(resultado, criterios=[dict(c, cumple="si" if c.get("cumple") in (True, "sí", "SI", "true") else c.get("cumple")) for c in resultado["criterios"]])\n        errores = errores_contrato("juez", respuesta_del_modelo(resultado))\n    if errores:\n        return _bloqueado(resultado, errores)\n    criterios = []')],
     "test_valores_fuera_del_esquema_son_blocked"),
    ("I-7 · «si» sin evidencia_verificada cuenta en la compuerta", JUEZ,
     [('criterio.get("evidencia_verificada") is not True', 'criterio.get("evidencia_verificada") is False')],
     "test_si_sin_evidencia_verificada_no_cuenta_en_la_compuerta"),
    ("I-7 · un veredicto incompleto se trata como reprobado y decide", GATE,
     [('if calificado["puntaje"] is None:', "if False:")],
     "test_veredicto_incompleto_es_blocked_no_reprobado"),
    ("I-7 · resultados con forma inesperada lanzan excepción después de escribir la decisión", GATE,
     [("            if not isinstance(caso, dict):\n                continue\n", "")],
     "test_resultados_mal_formados_rechazan_una_sola_vez or test_propiedad_resultados_arbitrarios_no_lanzan"),
    ("I-4 · la reserva no es exclusiva", GATE,
     [('with open(_marca(skill, actual), "x", encoding="utf-8") as marca:', 'with open(_marca(skill, actual), "a", encoding="utf-8") as marca:')],
     "test_carrera_de_reservas_reserva_exactamente_una or test_reserva_consume_el_intento"),
    ("I-4 · la decisión no es exclusiva", GATE,
     [('with open(COMPUERTA / f"{skill}.{actual[:16]}.decidido", "x", encoding="utf-8") as decidido:',
       'with open(COMPUERTA / f"{skill}.{actual[:16]}.decidido", "a", encoding="utf-8") as decidido:')],
     "test_carrera_de_decisiones_decide_exactamente_una_vez or test_la_decision_se_escribe_una_sola_vez"),
    ("CR-4 · la configuración del operador vuelve a la huella", GATE,
     [("    resumen = hashlib.sha256()\n    fuentes = [",
       "    resumen = hashlib.sha256()\n    resumen.update(json.dumps(cfg.cargar(cfg.raiz_proyecto()), sort_keys=True, default=str).encode())\n    fuentes = [")],
     "test_la_configuracion_del_operador_no_cambia_la_huella"),
    ("I-6 · la huella omite el andamiaje común de los casos", GATE,
     [('EVALS / "fixtures", EVALS / "_comun",', 'EVALS / "fixtures",')],
     "test_la_huella_cambia_con_lo_que_determina_el_caso"),
    ("I-1 · la compuerta humana pregunta en cualquier modo (el anfitrión auto-aprobaría)", "hooks/_comun.py",
     [("    if modo in MODOS_QUE_PREGUNTAN:\n", "    if True:\n")],
     "TestCompuertaHumana"),
    ("I-2 · revisar_codex.py corre sin «entorno»: «desarrollo»", "scripts/revisar_codex.py",
     [('if config.get("entorno") != "desarrollo":', "if False:")],
     "test_sin_entorno_desarrollo_se_niega"),
    ("I-2 · Ollama sigue redirecciones", "scripts/revisar_ollama.py",
     [("urllib.request.build_opener(urllib.request.ProxyHandler({}), _SinRedirecciones)", "urllib.request.build_opener(urllib.request.ProxyHandler({}))")],
     "test_ollama_no_sigue_redirecciones"),
    ("I-2 · Ollama usa el proxy del entorno", "scripts/revisar_ollama.py",
     [("urllib.request.build_opener(urllib.request.ProxyHandler({}), _SinRedirecciones)", "urllib.request.build_opener(_SinRedirecciones)")],
     "test_un_proxy_del_entorno_no_se_usa"),
    ("I-3 · el juez Codex conserva la terminal", "scripts/revisar_codex.py",
     [('HERRAMIENTAS_DESACTIVADAS = ("shell_tool", ', "HERRAMIENTAS_DESACTIVADAS = (")],
     "test_juez_aislado_sin_herramientas_y_con_puntaje_calculado"),
    ("I-11 · lint --diff aprueba sin examinar nada", "guardias/lint_itosturre.py",
     [("Esto no acredita el cambio.\")\n            return 2", "Esto no acredita el cambio.\")\n            return 0")],
     "TestLintDiff"),
]


# CR-1.1 (0.2.0): contrato estructurado de citas. Pruebas: tests/test_procedencia.py.
PROC = "scripts/nucleo/procedencia.py"
MUTANTES_CR1 = [
    ("I-8 · un «[[» que no es marcador válido se ignora", PROC,
     [("        if hallado is None:\n            errores.append(", "        if hallado is None:\n            (lambda *a: None)(")],
     "test_gramatica_todo_doble_corchete_es_un_marcador_valido_o_un_error"),
    ("I-8 · una CITA sin evidencia se degrada a no verificada", PROC,
     [("                if not permitir_pendientes:\n", "                if False:\n")],
     "test_sin_evidencia_no_hay_documento"),
    ("I-8 · la alarma no ve registros digitales", PROC,
     [('("registro", re.compile(r"(?i)(?:registro|ius)', '("registro", re.compile(r"(?!)(?:registro|ius)')],
     "test_alarma_un_patron_de_cita_fuera_de_marcador_impide_ensamblar"),
    ("I-10 · la alarma no ve marcas de verificación", PROC,
     [("for tipo, patron in _ALARMA for m in patron.finditer(texto)", "for tipo, patron in _ALARMA[:-1] for m in patron.finditer(texto)")],
     "test_alarma_un_patron_de_cita_fuera_de_marcador_impide_ensamblar"),
    ("I-9 · tramos con posiciones corridas", PROC,
     [("tramos.append(Tramo(inicio=largo, fin=largo + len(fragmento), **tramo))", "tramos.append(Tramo(inicio=largo, fin=largo + len(fragmento) - 1, **tramo))")],
     "test_cada_cita_del_entregable_es_exactamente_la_de_su_evidencia"),
    ("I-9 · la forma «clave» no muestra la clave de la evidencia", PROC,
     [("return f\"{oficial.get('clave', '—')} (registro digital {registro}){nota}\"", "return f\"{oficial.get('registro', '—')} (registro digital {registro}){nota}\"")],
     "test_cada_cita_del_entregable_es_exactamente_la_de_su_evidencia"),
    ("A1-4 · la cita ajena no se coteja con su fuente", PROC,
     [("            if not literal_en(referencia, contenido):\n                resultado.errores.append(", "            if False:\n                resultado.errores.append(")],
     "test_cita_ajena_solo_si_aparece_literal_en_la_fuente"),
    ("A1-5 · la entrega no comprueba la huella del documento", PROC,
     [('if sha256(documento) != datos_manifiesto.get("sha256_documento"):', "if False:")],
     "test_el_entregable_se_verifica_y_cualquier_cambio_lo_invalida"),
    ("I-8 · la entrega no busca citas fuera de los tramos", PROC,
     [("        if not _dentro(a, b, intervalos):\n            errores.append(f\"línea {_linea(texto, a)}: {tipo} «", "        if False:\n            errores.append(f\"línea {_linea(texto, a)}: {tipo} «")],
     "test_una_cita_a_mano_se_detecta_aunque_se_rehaga_la_huella"),
    ("I-9 · la entrega no coteja el texto de cada tramo", PROC,
     [('if _es_hex(tramo.get("sha256_texto")) and sha256(texto[inicio:fin]) != tramo["sha256_texto"]:', "if False:")],
     "test_editar_dentro_de_un_tramo_se_detecta_aunque_se_rehaga_la_huella"),
    ("A1-5 · un borrador con pendientes pasa por entregable", PROC,
     [('"entregable": not ensamblado.pendientes,', '"entregable": True,')],
     "test_pendientes_permitidos_dan_un_borrador_no_entregable"),
]

# 0.2.0: la reserva contaminada no admite holdouts (decisión del operador). Pruebas: TestReservaContaminada.
MUTANTES_RESERVA = [
    ("Reserva · reservar ignora el estado de la reserva", GATE,
     [("    if bloqueo := reserva_bloqueada():\n        print(f\"No se reserva:", "    if False:\n        print(f\"No se reserva:")],
     "TestReservaContaminada"),
    ("Reserva · registrar o correr el holdout ignora el estado", GATE,
     [("    if bloqueo := reserva_bloqueada():\n        print(f\"No se registra", "    if False:\n        print(f\"No se registra")],
     "TestReservaContaminada"),
    ("Reserva · cualquier estado declarado admite un holdout", GATE,
     [('estado.get("estado") != "aislada"', 'estado.get("estado") is None')],
     "TestReservaContaminada"),
]

# CR-1.2 (0.2.0): la comprobación de entrega conectada a hooks, informe y CLI. Pruebas: test_entrega.py y test_procedencia.py.
ESCRITURA = "hooks/guardia_escritura.py"
MUTANTES_CR12 = [
    ("CR-1.2 · un entregable jurídico se puede escribir a mano", ESCRITURA,
     [("    if es_salida_juridica(ruta, proyecto, config):\n        _comun.denegar(", "    if False:\n        _comun.denegar(")],
     "test_ningun_entregable_se_escribe_a_mano or test_editar_un_entregable"),
    ("CR-1.2 · el borrador se revisa en el texto nuevo, no en cómo queda", ESCRITURA,
     [("procedencia.problemas_de_borrador(contenido_resultante(nombre, datos, ruta))", "procedencia.problemas_de_borrador(\" \".join(textos_nuevos(nombre, datos)))")],
     "test_una_edicion_que_completa_una_cita"),
    ("CR-1.2 · un manifiesto se puede escribir a mano", ESCRITURA,
     [("    if normalizada.endswith(\".procedencia.json\"):", "    if False:")],
     "test_manifiestos_y_estado_de_la_reserva_protegidos"),
    ("CR-1.2 · el estado de la reserva se puede escribir a mano", ESCRITURA,
     [(" or normalizada.endswith(\"/evals/reserva.json\")", "")],
     "test_manifiestos_y_estado_de_la_reserva_protegidos"),
    ("CR-1.2 · el cierre de sesión no comprueba los entregables", "hooks/guardia_cierre.py",
     [("        bloqueados = entregables_bloqueados(entrada, inicio_de_sesion(ruta))", "        bloqueados = []")],
     "TestCierreDeSesion"),
    ("CR-1.2 · un envío MCP saca un entregable que no es válido", "hooks/guardia_externo.py",
     [("                if motivos:\n                    _comun.denegar(f\"«{ruta.name}» no es entregable", "                if False:\n                    _comun.denegar(f\"«{ruta.name}» no es entregable")],
     "TestSalidaExterna"),
    ("CR-1.2 · el manifiesto admite campos ajenos o faltantes", PROC,
     [("    if set(datos) != esperados:", "    if False:")],
     "test_quitar_o_agregar_cualquier_campo or test_manifiesto_incompleto_o_ajeno"),
    ("CR-1.2 · un tramo de cita puede omitirse del manifiesto", PROC,
     [("        errores += _notas_incoherentes(texto, [t for t in tramos if isinstance(t, dict)])", "        pass")],
     "test_quitar_o_agregar_cualquier_campo"),
    ("CR-1.2 · se declara entregable un manifiesto con citas pendientes", PROC,
     [("        if datos.get(\"entregable\") is True and \"CITA_PENDIENTE\" in tipos:", "        if False:")],
     "test_pendientes_permitidos"),
    ("CR-1.2 · la evidencia retirada después de ensamblar no bloquea", PROC,
     [("            if not fila:\n                errores.append(f\"tramo {i}: la cita", "            if not fila:\n                (lambda *a: None)(f\"tramo {i}: la cita")],
     "test_la_entrega_se_reverifica_contra_la_evidencia_viva"),
    ("CR-1.2 · otra evidencia vigente pasa por la que se usó", PROC,
     [("            elif fila[\"sha256_resultado\"] != tramo[\"sha256_evidencia\"]:", "            elif False:")],
     "test_la_entrega_se_reverifica_contra_la_evidencia_viva"),
    ("CR-1.2 · el texto de la cita no se coteja con su evidencia viva", PROC,
     [("            elif formatear(json.loads(fila[\"datos_oficiales\"]), tramo[\"forma\"], tramo[\"nota\"]) != fragmento:", "            elif False:")],
     "test_la_entrega_se_reverifica_contra_la_evidencia_viva"),
    ("CR-1.2 · una fuente cambiada no invalida la cita ajena", PROC,
     [("            if huella != tramo[\"sha256_fuente\"]:", "            if False:")],
     "test_la_cita_ajena_conserva or test_la_fuente_de_la_cita_ajena"),
    ("CR-1.2 · la cita ajena no se recoteja literal contra su fuente", PROC,
     [("            elif tramo[\"tipo\"] == \"CITA_AJENA\" and (not literal_en(tramo[\"referencia\"], contenido)", "            elif tramo[\"tipo\"] == \"CITA_AJENA\" and (False")],
     "test_la_cita_ajena_conserva"),
    ("CR-1.2 · las citas del informe no se recotejan con el documento auditado", PROC,
     [("                        if not literal_en(valor, contenido):", "                        if False:")],
     "test_las_citas_del_manifiesto_deben_ser_literales"),
    ("CR-1.2 · el informe no exige procedencia literal antes de escribirse", "scripts/reporte_vvca.py",
     [("    if no_literales:", "    if False:")],
     "test_un_rubro_corregido_hacia_el_oficial"),
    ("CR-1.2 · un .docx viejo pasa por su origen nuevo", "scripts/verificar_entrega.py",
     [(" or procedencia.sha256(origen.read_bytes()) != datos[\"sha256_origen\"]", "")],
     "test_derivado_docx"),
    ("CR-1.2 · la comprobación lanza en vez de bloquear", PROC,
     [("    if not isinstance(tipo_documento, str) or tipo_documento not in _CAMPOS_DOCUMENTO:", "    if tipo_documento not in _CAMPOS_DOCUMENTO:")],
     "test_ningun_manifiesto_hace_lanzar"),
    ("CR-1.2 · un marcador sin resolver llega al entregable", PROC,
     [("    if \"[[\" in texto:\n        errores.append(", "    if False:\n        errores.append(")],
     "test_un_marcador_sin_resolver"),
    ("CR-1.2 · la gramática admite marcadores anidados", PROC,
     [("\"NO_VERIFICADO\": re.compile(r\"\\[\\[NO_VERIFICADO:([^\\[\\]\\n]+)\\]\\]\")", "\"NO_VERIFICADO\": re.compile(r\"\\[\\[NO_VERIFICADO:([^\\]\\n]+)\\]\\]\")")],
     "test_gramatica"),
    ("CR-1.2 · sin node, la guardia de escritura falla abierta (código 127, no bloqueante)", "hooks/hooks.json",
     [('guardia_escritura.py cerrado PreToolUse || { echo \\"itostack: la guardia no pudo ejecutarse (¿falta node?): se deniega (falla cerrado)\\" >&2; exit 2; }',
       "guardia_escritura.py cerrado PreToolUse")],
     "test_sin_node_las_guardias_previas_fallan_cerradas"),
]

CONJUNTOS = {"cierre-0.1.2": ("tests/test_auditoria_codex.py", MUTANTES), "cr1": ("tests/test_procedencia.py", MUTANTES_CR1),
             "reserva": ("tests/test_auditoria_codex.py", MUTANTES_RESERVA),
             "cr12": (["tests/test_entrega.py", "tests/test_procedencia.py", "tests/test_plataforma.py"], MUTANTES_CR12)}


def copiar(destino: Path) -> None:
    shutil.copytree(PLUGIN, destino, ignore=shutil.ignore_patterns("node_modules", "__pycache__", ".pytest_cache", ".hypothesis", "results", "compuerta"))


def correr(raiz: Path, filtro: str, pruebas: str | list[str] = PRUEBAS) -> subprocess.CompletedProcess:
    entorno = {k: v for k, v in os.environ.items() if not k.startswith("ITOSTACK_")}
    entorno["PYTHONUTF8"] = "1"
    archivos = [pruebas] if isinstance(pruebas, str) else pruebas
    return subprocess.run([sys.executable, "-m", "pytest", *archivos, "-q", "-p", "no:cacheprovider", "-k", filtro], cwd=raiz,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", env=entorno, timeout=900)


def ultima_linea(salida: str) -> str:
    lineas = [l for l in salida.strip().splitlines() if l.strip()]
    return lineas[-1] if lineas else ""


def principal() -> int:
    pruebas, mutantes = CONJUNTOS[sys.argv[2] if len(sys.argv) > 2 else "cierre-0.1.2"]
    base = Path(tempfile.mkdtemp(prefix="mutantes-"))
    filas, sobrevivientes = [], 0
    try:
        limpio = base / "limpio"
        copiar(limpio)
        for i, (nombre, archivo, reemplazos, filtro) in enumerate(mutantes, 1):
            control = correr(limpio, filtro, pruebas)
            raiz = base / f"m{i}"
            copiar(raiz)
            ruta = raiz / archivo
            texto = ruta.read_text(encoding="utf-8")
            invalidos = [original for original, _ in reemplazos if texto.count(original) != 1]
            if invalidos:
                filas.append((nombre, "MUTANTE INVÁLIDO", f"fragmento no único o ausente: {invalidos[0][:60]!r}"))
                sobrevivientes += 1
                continue
            for original, mutado in reemplazos:
                texto = texto.replace(original, mutado)
            ruta.write_text(texto, encoding="utf-8")
            mutante = correr(raiz, filtro, pruebas)
            if control.returncode != 0:
                estado = "CONTROL FALLA"  # las pruebas fallan sin mutar: el pase no demuestra nada
                sobrevivientes += 1
            elif mutante.returncode != 0:
                estado = "DETECTADO"
            else:
                estado = "NO DETECTADO"
                sobrevivientes += 1
            filas.append((nombre, estado, f"limpio: {ultima_linea(control.stdout)} · mutante: {ultima_linea(mutante.stdout)}"))
            shutil.rmtree(raiz, ignore_errors=True)
    finally:
        shutil.rmtree(base, ignore_errors=True)
    for nombre, estado, detalle in filas:
        print(f"{estado:15} {nombre}\n                {detalle}")
    print(f"\n{len(filas) - sobrevivientes}/{len(filas)} mutantes detectados")
    return 0 if sobrevivientes == 0 else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(principal())
