import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "scripts"
FIXTURE_SJF = RAIZ / "evals" / "fixtures" / "sjf" / "basico.json"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(RAIZ / "guardias"))
sys.path.insert(0, str(RAIZ / "hooks"))


def hay_navegador() -> bool:
    from nucleo import config as cfg

    return (SCRIPTS / "node_modules" / "playwright").is_dir() and cfg.detectar_navegador(cfg.CONFIG_DEFECTO) is not None


requiere_navegador = pytest.mark.skipif(not hay_navegador(), reason="requiere Node + Playwright + Chromium")


@pytest.fixture
def proyecto(tmp_path, monkeypatch):
    """Proyecto temporal con .itostack en modo fixture."""
    monkeypatch.delenv("ITOSTACK_PROYECTO", raising=False)
    monkeypatch.delenv("ITOSTACK_MODO", raising=False)
    subprocess.run(
        [sys.executable, str(SCRIPTS / "inicializar.py"), "--proyecto", str(tmp_path), "--modo", "fixture",
         "--sjf-fixture", str(FIXTURE_SJF), "--silencioso"],
        check=True,
    )
    return tmp_path


def correr_hook(nombre: str, entrada: dict, cwd: Path | None = None) -> dict:
    entorno = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(RAIZ)}
    entorno.pop("ITOSTACK_PROYECTO", None)
    proceso = subprocess.run(
        [sys.executable, str(RAIZ / "hooks" / nombre)],
        input=json.dumps(entrada), capture_output=True, text=True, env=entorno, cwd=cwd or RAIZ, timeout=30,
    )
    assert proceso.returncode == 0, proceso.stderr
    return json.loads(proceso.stdout) if proceso.stdout.strip() else {}


def decision(salida: dict) -> str | None:
    return (salida.get("hookSpecificOutput") or {}).get("permissionDecision")


def verificar(proyecto: Path, *argumentos: str) -> subprocess.CompletedProcess:
    entorno = {k: v for k, v in os.environ.items() if k not in {"ITOSTACK_PROYECTO", "ITOSTACK_MODO"}}
    return subprocess.run([sys.executable, str(SCRIPTS / "verificar.py"), *argumentos], cwd=proyecto, capture_output=True, text=True, env=entorno, timeout=240)
