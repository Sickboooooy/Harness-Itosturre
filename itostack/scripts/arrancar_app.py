#!/usr/bin/env python3
"""Arranca y detiene la app local para verificarla (aislada por puerto libre).

Uso:
  arrancar_app.py iniciar [--comando "flask --app app run --port {puerto}"] [--salud /] [--espera 30]
  arrancar_app.py estado
  arrancar_app.py detener
Imprime JSON con base_url, puerto y pid. El estado vive en .itostack/app.json.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nucleo import config as cfg  # noqa: E402


def puerto_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def responde(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as respuesta:
            return respuesta.status < 500
    except urllib.error.HTTPError as error:
        return error.code < 500
    except (urllib.error.URLError, OSError):
        return False


def iniciar(proyecto: Path, comando: str, salud: str, espera: int) -> dict:
    estado_ruta = proyecto / cfg.DIR_ITOSTACK / "app.json"
    puerto = puerto_libre()
    linea = comando.format(puerto=puerto)
    bitacora = proyecto / cfg.DIR_ITOSTACK / "app.log"
    bitacora.parent.mkdir(parents=True, exist_ok=True)
    with open(bitacora, "w", encoding="utf-8") as salida:
        proceso = subprocess.Popen(shlex.split(linea), cwd=proyecto, stdout=salida, stderr=subprocess.STDOUT, start_new_session=True)
    base = f"http://127.0.0.1:{puerto}"
    limite = time.monotonic() + espera
    while time.monotonic() < limite:
        if proceso.poll() is not None:
            return {"ok": False, "error": f"la app terminó con código {proceso.returncode}; revisa {bitacora}"}
        if responde(base + salud):
            estado = {"ok": True, "base_url": base, "puerto": puerto, "pid": proceso.pid, "comando": linea, "bitacora": str(bitacora)}
            estado_ruta.write_text(json.dumps(estado, indent=2), encoding="utf-8")
            return estado
        time.sleep(0.3)
    os.killpg(proceso.pid, signal.SIGTERM)
    return {"ok": False, "error": f"la app no respondió en {espera} s en {base}{salud}; revisa {bitacora}"}


def detener(proyecto: Path) -> dict:
    estado_ruta = proyecto / cfg.DIR_ITOSTACK / "app.json"
    if not estado_ruta.is_file():
        return {"ok": True, "detalle": "no había app registrada"}
    estado = json.loads(estado_ruta.read_text(encoding="utf-8"))
    try:
        os.killpg(estado["pid"], signal.SIGTERM)
    except ProcessLookupError:
        pass
    estado_ruta.unlink()
    return {"ok": True, "detalle": f"app detenida (pid {estado['pid']})"}


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = analizador.add_subparsers(dest="accion", required=True)
    p_ini = sub.add_parser("iniciar")
    p_ini.add_argument("--comando", default=f"{shlex.quote(sys.executable)} -m flask --app app run --port {{puerto}}")
    p_ini.add_argument("--salud", default="/")
    p_ini.add_argument("--espera", type=int, default=30)
    sub.add_parser("estado")
    sub.add_parser("detener")
    args = analizador.parse_args()
    proyecto = cfg.raiz_proyecto()
    if args.accion == "iniciar":
        resultado = iniciar(proyecto, args.comando, args.salud, args.espera)
    elif args.accion == "detener":
        resultado = detener(proyecto)
    else:
        ruta = proyecto / cfg.DIR_ITOSTACK / "app.json"
        resultado = json.loads(ruta.read_text(encoding="utf-8")) if ruta.is_file() else {"ok": False, "detalle": "sin app"}
        if resultado.get("base_url"):
            resultado["responde"] = responde(resultado["base_url"] + "/")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if resultado.get("ok") else 1


if __name__ == "__main__":
    sys.exit(principal())
