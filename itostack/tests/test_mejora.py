"""Mejora continua: correcciones, bitácora, relleno, salud de transcripciones y rutinas, autoprueba de evals."""

import json
import subprocess
import sys

from conftest import RAIZ, SCRIPTS, requiere_navegador


def correr(proyecto, script, *argumentos):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *argumentos], cwd=proyecto, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)


def test_correcciones_pendientes_y_propuesta(proyecto):
    tsv = proyecto / ".itostack" / "mejora" / "correcciones.tsv"
    tsv.write_text("fecha\tsesion\tclave\textracto\n" + "".join(f"2026-11-1{i}\ts{i}\tcommits-espanol\tNo, en español\n" for i in range(3)), encoding="utf-8")
    assert "commits-espanol · 3 veces" in correr(proyecto, "registrar_correccion.py", "pendientes").stdout
    correr(proyecto, "registrar_correccion.py", "proponer", "--clave", "commits-espanol", "--nivel", "2", "--artefacto", "hooks/guardia_bash.py", "--descripcion", "x")
    assert "nivel: 2" in (proyecto / ".itostack" / "mejora" / "propuesta.md").read_text(encoding="utf-8")
    correr(proyecto, "registrar_correccion.py", "elevar", "--clave", "commits-espanol", "--nivel", "2", "--artefacto", "hooks/guardia_bash.py", "--descripcion", "x")
    assert "Sin correcciones" in correr(proyecto, "registrar_correccion.py", "pendientes").stdout


def test_bitacora_irreversible(proyecto):
    assert correr(proyecto, "bitacora.py", "registrar", "--decision", "renombrar tabla", "--razon", "consistencia").returncode == 0
    assert correr(proyecto, "bitacora.py", "registrar", "--decision", "borrar respaldo", "--razon", "espacio", "--reversible", "no").returncode == 3
    assert "irreversible" in correr(proyecto, "bitacora.py", "ver").stdout


def test_relleno(tmp_path):
    sucio = tmp_path / "s.md"
    sucio.write_text("Es importante destacar que, sin lugar a dudas, juega un papel crucial. En resumen, es robusto.", encoding="utf-8")
    limpio = tmp_path / "l.md"
    limpio.write_text("Por lo expuesto, procede conceder la suspensión definitiva.", encoding="utf-8")
    assert correr(tmp_path, "detectar_relleno.py", str(sucio)).returncode == 1
    assert correr(tmp_path, "detectar_relleno.py", str(limpio)).returncode == 0


def _transcripcion(directorio, nombre, mensajes):
    directorio.mkdir(parents=True, exist_ok=True)
    with open(directorio / f"{nombre}.jsonl", "w", encoding="utf-8") as archivo:
        for m in mensajes:
            archivo.write(json.dumps(m) + "\n")


def test_salud_transcripciones_y_rutinas(proyecto, tmp_path):
    proyectos = tmp_path / "projects"
    mensajes = []
    for i in range(3):
        mensajes.append({"type": "user", "message": {"role": "user", "content": "No, te dije que no uses waitForTimeout"}})
        mensajes.append({"type": "assistant", "message": {"role": "assistant", "usage": {"input_tokens": 300000, "output_tokens": 200000},
                         "content": [{"type": "tool_use", "name": "Bash", "input": {"command": "npx playwright test --project chromium"}}]}})
        mensajes.append({"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": "itostack: commit en inglés", "is_error": True}]}})
    _transcripcion(proyectos / "-home-proyecto", "sesion1", mensajes)
    salida = correr(proyecto, "salud_transcripciones.py", "--proyectos", str(proyectos))
    assert "Correcciones humanas: 3" in salida.stdout and "Construir la palanca" in salida.stdout
    rutinas = correr(proyecto, "salud_rutinas.py", "--proyectos", str(proyectos), "--umbral", "1000")
    assert "Sesiones atípicas" in rutinas.stdout


def test_salud_silenciosa_sin_friccion(proyecto, tmp_path):
    _transcripcion(tmp_path / "projects" / "p", "s", [{"type": "user", "message": {"role": "user", "content": "Redacta el escrito"}}])
    salida = correr(proyecto, "salud_transcripciones.py", "--proyectos", str(tmp_path / "projects"))
    assert salida.stdout == "" and not list((proyecto / ".itostack" / "mejora" / "reportes").glob("*.md"))


def test_revisor_local_rechaza_familia_claude(tmp_path):
    archivo = tmp_path / "a.md"
    archivo.write_text("x", encoding="utf-8")
    assert correr(tmp_path, "revisar_ollama.py", "--modelo", "claude-sonnet", "--archivo", str(archivo)).returncode == 3


def test_mapa_rutas_flask():
    salida = subprocess.run([sys.executable, str(SCRIPTS / "mapa_rutas_flask.py"), str(RAIZ / "evals" / "fixtures" / "app_flask_simulada"), "--json"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    datos = json.loads(salida.stdout)
    assert {r["ruta"] for r in datos["rutas"]} == {"/", "/validar"}
    assert "campo-registro" in json.dumps(datos["selectores"])


@requiere_navegador
def test_autoprueba_de_evals_juridicos():
    resultado = subprocess.run([sys.executable, str(RAIZ / "evals" / "autoprueba.py"), "--caso", "verificar-cita/*"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    assert resultado.returncode == 0, resultado.stdout


def test_compuerta_holdout_un_solo_intento(tmp_path, monkeypatch):
    sys.path.insert(0, str(RAIZ / "evals"))
    import compuerta_holdout as compuerta

    monkeypatch.setattr(compuerta, "COMPUERTA", tmp_path)
    monkeypatch.setattr(compuerta, "HISTORIAL", tmp_path / "historial.tsv")
    real = json.loads((RAIZ / "tests" / "datos" / "resultado_claude_plugin_eval.json").read_text(encoding="utf-8"))
    assert compuerta.puntajes(real) == {"verificar-cita.fail-inexistente": real["cases"][0]["aggregates"]["score"]}

    desarrollo = {"cases": [{"name": n, "aggregates": {"score": 1.0}} for n in compuerta._casos("verificar-cita", "desarrollo")]}
    (tmp_path / "dev.json").write_text(json.dumps(desarrollo), encoding="utf-8")
    assert compuerta.congelar("verificar-cita", tmp_path / "dev.json") == 1  # sin juez de otra familia no se congela
    assert compuerta.congelar("verificar-cita", tmp_path / "dev.json", sin_juez_externo="prueba sin juez") == 0

    assert compuerta.reservar("verificar-cita") == 0  # el intento se consume antes de correr
    holdout = {"cases": [{"name": n, "aggregates": {"score": 0.5}} for n in compuerta._casos("verificar-cita", "holdout")]}
    (tmp_path / "h.json").write_text(json.dumps(holdout), encoding="utf-8")
    assert compuerta.holdout("verificar-cita", tmp_path / "h.json", []) == 1
    assert compuerta.holdout("verificar-cita", tmp_path / "h.json", []) == 1
    assert compuerta.reservar("verificar-cita") == 1
    assert "RECHAZADA" in (tmp_path / "historial.tsv").read_text(encoding="utf-8")
