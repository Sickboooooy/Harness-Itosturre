"""Riesgo residual de los hooks (decisión 5 del operador): ¿qué hace cada hook de itostack, en una sesión real de Claude
Code en Windows, cuando `node` no está en el PATH?

claude.exe es nativo (no necesita node), así que se lanza con un PATH sin la carpeta de Node.js: la sesión funciona y
los hooks no encuentran `node`. Se le pide ejecutar `echo` con Bash, preaprobado con --allowedTools: si la guardia
PreToolUse no bloquea, el comando corre. Control: la misma sesión con node en el PATH.

Se registran todos los eventos de hooks del flujo stream-json (nombre, código de salida, stderr), que además revelan qué
shell ejecuta los comandos de hooks.json. Sin credenciales nuevas; repositorio temporal; nada sale de la máquina salvo la
llamada normal al modelo.
Uso: python -I hooks_sin_node_vivo.py <raíz del plugin itostack> [modelo]
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PLUGIN = Path(sys.argv[1]).resolve()
MODELO = sys.argv[2] if len(sys.argv) > 2 else "claude-haiku-5-5"
SALIDA = Path(__file__).resolve().parent / "evidencia-vivo"
CLAUDE = Path(os.environ["APPDATA"]) / "npm" / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
MARCA = "hola-itostack-sin-node"


def path_sin_node() -> str:
    carpetas = [c for c in os.environ["PATH"].split(os.pathsep) if c and not (Path(c) / "node.exe").is_file() and "nodejs" not in c.lower()]
    return os.pathsep.join(carpetas)


def sesion(etiqueta: str, path: str, trabajo: Path) -> dict:
    entorno = {k: v for k, v in os.environ.items() if k not in {"CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"} and not k.startswith("ITOSTACK_")}
    entorno["PATH"] = path
    argv = [str(CLAUDE), "-p", "--plugin-dir", str(PLUGIN), "--permission-mode", "default", "--strict-mcp-config", "--output-format", "stream-json",
            "--verbose", "--max-turns", "3", "--model", MODELO, "--allowedTools", "Bash(echo:*)"]
    prompt = f"Usa la herramienta Bash para ejecutar exactamente este comando, una sola vez: echo {MARCA}\nDespués responde solo con la salida o el error."
    proceso = subprocess.run(argv, input=prompt, cwd=trabajo, capture_output=True, text=True, encoding="utf-8", errors="replace", env=entorno, timeout=600)
    eventos, hooks, resultados = [], [], []
    for linea in proceso.stdout.splitlines():
        try:
            evento = json.loads(linea)
        except json.JSONDecodeError:
            continue
        eventos.append(evento)
        if evento.get("subtype") == "hook_response":
            hooks.append({"hook": evento.get("hook_name"), "codigo": evento.get("exit_code"), "resultado": evento.get("outcome"),
                          "stderr": str(evento.get("stderr") or "")[:300]})
        mensaje = evento.get("message")
        for bloque in (mensaje.get("content") if isinstance(mensaje, dict) and isinstance(mensaje.get("content"), list) else []):
            if isinstance(bloque, dict) and bloque.get("type") == "tool_result":
                texto = bloque.get("content")
                texto = " ".join(str(t.get("text", "")) for t in texto if isinstance(t, dict)) if isinstance(texto, list) else str(texto)
                resultados.append({"error": bool(bloque.get("is_error")), "texto": texto[:400]})
    (SALIDA / f"hooks-{etiqueta}.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in eventos) + "\n", encoding="utf-8")
    final = next((e for e in reversed(eventos) if e.get("type") == "result"), {})
    return {"etiqueta": etiqueta, "codigo": proceso.returncode, "node_en_path": shutil.which("node", path=path) is not None,
            "eventos_de_hooks": hooks, "resultados_de_herramientas": resultados, "echo_ejecutado": any(MARCA in r["texto"] and not r["error"] for r in resultados),
            "sesion_termino": bool(final), "turnos": final.get("num_turns"), "stderr_cola": proceso.stderr.strip()[-400:]}


def principal() -> int:
    SALIDA.mkdir(exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix="hooks-sin-node-"))
    try:
        subprocess.run(["git", "init", "-q"], cwd=base, check=True)
        sin_node = sesion("sin-node", path_sin_node(), base)
        con_node = sesion("con-node", os.environ["PATH"], base)
    finally:
        shutil.rmtree(base, ignore_errors=True)
    criterios = {
        "control_con_node_ejecuta_echo": con_node["echo_ejecutado"],
        "sin_node_el_path_no_tiene_node": not sin_node["node_en_path"],
        "sin_node_la_guardia_bash_bloquea": not sin_node["echo_ejecutado"] and any(r["error"] and "falla cerrado" in r["texto"] for r in sin_node["resultados_de_herramientas"]),
        "sin_node_la_sesion_termina_sin_bucle": sin_node["sesion_termino"],
    }
    informe = {"fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"), "modelo": MODELO, "claude": str(CLAUDE.name), "criterios": criterios,
               "veredicto": "PASS" if all(criterios.values()) else "FAIL", "sin_node": sin_node, "con_node": con_node}
    (SALIDA / "hooks-sin-node-vivo.json").write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"veredicto": informe["veredicto"], "criterios": criterios}, ensure_ascii=False, indent=2))
    for etiqueta, datos in (("sin node", sin_node), ("con node", con_node)):
        print(f"--- {etiqueta}: echo ejecutado={datos['echo_ejecutado']} · turnos={datos['turnos']}")
        for h in datos["eventos_de_hooks"]:
            print(f"    hook {h['hook']}: código {h['codigo']} · {h['resultado']} · {h['stderr'][:160]!r}")
        for r in datos["resultados_de_herramientas"]:
            print(f"    resultado {'ERROR' if r['error'] else 'ok'}: {r['texto'][:200]!r}")
    return 0 if informe["veredicto"] == "PASS" else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(principal())
