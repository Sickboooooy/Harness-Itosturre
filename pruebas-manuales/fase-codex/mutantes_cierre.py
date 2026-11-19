"""Pase de mutantes del cierre de 0.1.2: ¿las pruebas de la matriz detectan el defecto que dicen demostrar?

Para cada mutante: copia el plugin (sin node_modules) a un directorio temporal, reintroduce UN defecto con un reemplazo
exacto y corre solo las pruebas del invariante. «Detectado» = las pruebas fallan con el defecto. Un mutante no
detectado es una prueba que no demuestra su invariante.

Uso: python -I mutantes_cierre.py <raíz del plugin itostack>
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


def copiar(destino: Path) -> None:
    shutil.copytree(PLUGIN, destino, ignore=shutil.ignore_patterns("node_modules", "__pycache__", ".pytest_cache", ".hypothesis", "results", "compuerta"))


def correr(raiz: Path, filtro: str) -> subprocess.CompletedProcess:
    entorno = {k: v for k, v in os.environ.items() if not k.startswith("ITOSTACK_")}
    entorno["PYTHONUTF8"] = "1"
    return subprocess.run([sys.executable, "-m", "pytest", PRUEBAS, "-q", "-p", "no:cacheprovider", "-k", filtro], cwd=raiz,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", env=entorno, timeout=900)


def ultima_linea(salida: str) -> str:
    lineas = [l for l in salida.strip().splitlines() if l.strip()]
    return lineas[-1] if lineas else ""


def principal() -> int:
    base = Path(tempfile.mkdtemp(prefix="mutantes-"))
    filas, sobrevivientes = [], 0
    try:
        limpio = base / "limpio"
        copiar(limpio)
        for i, (nombre, archivo, reemplazos, filtro) in enumerate(MUTANTES, 1):
            control = correr(limpio, filtro)
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
            mutante = correr(raiz, filtro)
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
