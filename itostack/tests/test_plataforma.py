"""Regresiones de plataforma (defectos D-01, D-02 y D-03 del informe de la fase 0 en Windows).

Se simulan en cualquier sistema: sin módulo pwd, salida en cp1252, intérprete ausente o que
truena. La CI además corre toda la suite en windows-latest.
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

from conftest import RAIZ, SCRIPTS

LANZADOR = RAIZ / "hooks" / "lanzar.mjs"
requiere_node = pytest.mark.skipif(shutil.which("node") is None, reason="requiere Node")
PUSH_FORZADO = {"tool_name": "Bash", "tool_input": {"command": "git push --force origin main"}}


def lanzar(script, modo, evento, entrada, **entorno_extra):
    entorno = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(RAIZ), **entorno_extra}
    return subprocess.run(
        ["node", str(LANZADOR), str(script), modo, evento],
        input=json.dumps(entrada), capture_output=True, text=True, encoding="utf-8", env=entorno, timeout=60,
    )


def test_d01_nucleo_carga_sin_modulo_pwd():
    codigo = (
        "import sys; sys.modules['pwd'] = None; "
        f"sys.path.insert(0, {str(SCRIPTS)!r}); "
        "from nucleo import config, veredicto, evidencia, citas; print(config.home_real())"
    )
    resultado = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, encoding="utf-8")
    assert resultado.returncode == 0, resultado.stderr


def test_salida_unicode_en_tuberia_cp1252(proyecto):
    entorno = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
    entorno.pop("ITOSTACK_PROYECTO", None)
    resultado = subprocess.run(
        [sys.executable, str(SCRIPTS / "verificar.py"), "tesis", "--rubro", "SIN REGISTRO DE PRUEBA"],
        cwd=proyecto, capture_output=True, env=entorno, timeout=60,
    )
    texto = resultado.stdout.decode("utf-8")
    assert resultado.returncode == 2 and "⚠ NO VERIFICADO" in texto, resultado.stderr.decode("utf-8", "replace")


@requiere_node
def test_lanzador_reenvia_la_decision_del_hook():
    salida = json.loads(lanzar("guardia_bash.py", "cerrado", "PreToolUse", PUSH_FORZADO).stdout)
    assert salida["hookSpecificOutput"]["permissionDecision"] == "deny"


@requiere_node
def test_d02_d03_sin_interprete_la_guardia_deniega():
    resultado = lanzar("guardia_bash.py", "cerrado", "PreToolUse", PUSH_FORZADO, ITOSTACK_PYTHON="/no/existe/python")
    decision = json.loads(resultado.stdout)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny" and "Falla cerrado" in decision["permissionDecisionReason"]


@requiere_node
def test_d02_hook_que_truena_deniega_en_modo_cerrado(tmp_path):
    roto = tmp_path / "roto.py"
    roto.write_text("import modulo_que_no_existe\n", encoding="utf-8")
    resultado = lanzar(roto, "cerrado", "PreToolUse", PUSH_FORZADO, ITOSTACK_PYTHON=sys.executable)
    assert json.loads(resultado.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


@requiere_node
def test_hook_informativo_que_truena_no_bloquea(tmp_path):
    roto = tmp_path / "roto.py"
    roto.write_text("raise RuntimeError('falla de prueba')\n", encoding="utf-8")
    resultado = lanzar(roto, "abierto", "Stop", {}, ITOSTACK_PYTHON=sys.executable)
    assert resultado.returncode == 0 and resultado.stdout == "" and "omitido" in resultado.stderr


@requiere_node
@pytest.mark.skipif(os.name == "nt", reason="el alias simulado es un script de shell")
def test_alias_de_la_store_se_descarta(tmp_path):
    alias = tmp_path / "python3"
    alias.write_text("#!/bin/sh\necho 'Python was not found; run without arguments to install from the Microsoft Store' >&2\nexit 9009\n", encoding="utf-8")
    alias.chmod(0o755)
    resultado = lanzar("guardia_bash.py", "cerrado", "PreToolUse", PUSH_FORZADO, ITOSTACK_PYTHON=str(alias))
    razon = json.loads(resultado.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "no disponible" in razon


def test_ejecutar_convierte_excepciones_en_denegacion(capsys):
    import _comun

    def explota():
        raise ValueError("boom")

    _comun.ejecutar(explota, "PreToolUse", "cerrado")
    assert json.loads(capsys.readouterr().out)["hookSpecificOutput"]["permissionDecision"] == "deny"
    _comun.ejecutar(explota, "Stop", "abierto")
    salida = capsys.readouterr()
    assert salida.out == "" and "omitido" in salida.err


def test_hooks_json_usa_el_lanzador_en_todos_los_eventos():
    configuracion = json.loads((RAIZ / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    comandos = [h["command"] for grupos in configuracion["hooks"].values() for g in grupos for h in g["hooks"]]
    assert comandos and all(c.startswith('node "${CLAUDE_PLUGIN_ROOT}/hooks/lanzar.mjs"') for c in comandos)
    assert all(" cerrado PreToolUse" in c for c in comandos if "guardia_" in c and "cierre" not in c)


def _comandos_previos():
    configuracion = json.loads((RAIZ / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    return [h["command"] for g in configuracion["hooks"]["PreToolUse"] for h in g["hooks"]]


def _bash():
    sys.path.insert(0, str(RAIZ / "evals"))
    import autoprueba

    try:
        return autoprueba.ubicar_bash()
    except SystemExit:
        pytest.skip("requiere bash")


@pytest.mark.parametrize("indice", range(4))
def test_sin_node_las_guardias_previas_fallan_cerradas(tmp_path, indice):
    """Hallado en el laboratorio WSL (0.2.0): si falta `node`, el comando del hook sale con 127, que Claude Code trata
    como error NO bloqueante, y la acción pasa sin guardia. El comando exacto de hooks.json debe salir con 2 (bloquea)."""
    sin_node = tmp_path / "sin-node"
    sin_node.mkdir()
    entorno = {"PATH": str(sin_node), "CLAUDE_PLUGIN_ROOT": RAIZ.as_posix(), "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")}
    salida = subprocess.run([_bash(), "-c", _comandos_previos()[indice]], input='{"tool_name": "Bash", "tool_input": {"command": "ls"}}',
                            capture_output=True, text=True, encoding="utf-8", errors="replace", env=entorno, timeout=60)
    assert salida.returncode == 2 and "falla cerrado" in salida.stderr, (salida.returncode, salida.stderr[-300:])


def test_con_node_el_respaldo_no_altera_la_decision(tmp_path):
    """Control: con `node` presente, una guardia que deniega por JSON sale con 0 y su decisión llega intacta."""
    if not shutil.which("node"):
        pytest.skip("requiere node")
    entorno = {**os.environ, "CLAUDE_PLUGIN_ROOT": RAIZ.as_posix(), "PYTHONUTF8": "1"}
    entrada = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git push --force origin main"}, "cwd": str(tmp_path)})
    salida = subprocess.run([_bash(), "-c", _comandos_previos()[0]], input=entrada, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", env=entorno, timeout=60)
    assert salida.returncode == 0 and json.loads(salida.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
