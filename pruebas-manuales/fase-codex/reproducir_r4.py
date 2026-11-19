"""Reproduce los 10 hallazgos de la ronda 4 contra una versión de itostack (argumento: raíz del plugin).

Imprime, por hallazgo, si el defecto se manifiesta (DEFECTO) o no (OK) con un caso concreto.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(PLUGIN / "scripts"))
sys.path.insert(0, str(PLUGIN / "evals"))
os.environ["PYTHONUTF8"] = "1"

from nucleo import citas, juez  # noqa: E402

resultados = []


def anotar(id_, defecto, detalle):
    resultados.append((id_, "DEFECTO" if defecto else "OK", detalle))


OF = {
    "1999999": {"rubro": "OFICIAL LARGO DE PRUEBA.", "clave": "1a./J. 45/2019 (10a.)"},
    "FICT-0001": {"rubro": 'DERECHO A LA "VERDAD". ALCANCE.'},
    "FICT-0002": {"rubro": "LEGALIDAD. SU ALCANCE."},
}


def buscar(registro, clave):
    return OF.get(registro) or ({"rubro": "OTRO RUBRO.", "clave": clave} if clave else None)


# [1] segundo rubro para una sola cita
p = citas.rubros_discrepantes("registro digital 1999999, rubro: «OFICIAL LARGO DE PRUEBA.»; rubro: «FALSO»", buscar)
anotar("R4-1 segundo rubro sin cotejar", not p, p)

# [2] registro ❌ y clave con rubro falso en otro segmento
p = citas.rubros_discrepantes("registro digital 1999999 ❌; 1a./J. 45/2019 (10a.), rubro: «FALSO»", buscar)
anotar("R4-2 la marca del registro exime a la clave", not p, p)

# [3] marca dentro de una cita entre «» de varias líneas
m = {c.valor: c.marcada_no_verificada for c in citas.extraer("Texto citado: «\nregistro digital 1999999 ❌\n»")}
anotar("R4-3 marca dentro de comillas multilínea exime", m.get("1999999") is True, m)

# [8] rubro válido con comillas interiores
p = citas.rubros_discrepantes('registro digital FICT-0001, rubro: «DERECHO A LA "VERDAD". ALCANCE.»', buscar)
anotar("R4-8 falso rechazo con comillas interiores", bool(p), p)

# [9] rubro declarado con puntos propios entre varias citas
texto = 'registro digital FICT-0002, Rubro: LEGALIDAD. SU ALCANCE. Y registro digital FICT-0001, rubro: «DERECHO A LA "VERDAD". ALCANCE.»'
p = [x for x in citas.rubros_discrepantes(texto, buscar) if "FICT-0002" in x]
anotar("R4-9 falso rechazo de rubro declarado con puntos", bool(p), p)

# [10] respuesta del juez fuera de contrato
r = juez.calificar({"criterios": [{"numero": 1, "criterio": "c", "cumple": "si", "evidencia": "«x y z»"}]}, 1)
anotar("R4-10a sin fallos_criticos aprueba", r.get("aprobado") is True, {"aprobado": r.get("aprobado")})
try:
    r = juez.calificar([], 1)
    anotar("R4-10b respuesta [] no es BLOCKED", not (r.get("puntaje") is None and r.get("aprobado") is False), {"puntaje": r.get("puntaje"), "aprobado": r.get("aprobado")})
except Exception as error:  # noqa: BLE001
    anotar("R4-10b respuesta [] lanza excepción", True, type(error).__name__)

# [4] acciones_externas_permitidas fuera de la huella
import compuerta_holdout as compuerta  # noqa: E402

with tempfile.TemporaryDirectory() as proyecto:
    (Path(proyecto) / ".itostack").mkdir()
    os.environ["ITOSTACK_PROYECTO"] = proyecto
    antes = compuerta.huella("verificar-cita")
    (Path(proyecto) / ".itostack" / "config.json").write_text(json.dumps({"acciones_externas_permitidas": ["mcp__*"]}), encoding="utf-8")
    despues = compuerta.huella("verificar-cita")
    # Diagnóstico (CR-4): no es un defecto. El caso corre en un espacio que preparar.sh inicializa con la configuración
    # del plugin; la del operador no le llega (TestCierre012::test_el_caso_no_ve_la_configuracion_del_operador).
    resultados.append(("R4-4 acciones_externas_permitidas no cambia la huella", "NO ES DEFECTO" if antes == despues else "DEP. FALSA",
                       "la huella no depende de la configuración del operador" if antes == despues else "la huella depende de la configuración del operador"))

    # [5] rúbrica de otra skill aceptada
    otra = (PLUGIN / "evals" / "rubricas" / "informe-vvca.md").read_bytes()
    veredicto = {"criterios": [{"numero": i, "criterio": "c", "cumple": "si", "evidencia": "«x»", "evidencia_verificada": True} for i in range(1, 7)],
                 "fallos_criticos": [], "observaciones": "", "juez": {"familia": "openai", "herramienta": "codex", "modelo": "gpt-6.1-sol", "esfuerzo": "high", "version": "1", "rol": "juez"},
                 "material": {"sha256_artefactos": ["a" * 64], "rubrica": {"sha256": juez.sha256(otra), "criterios": 6}}}
    ruta = Path(proyecto) / "v.json"
    ruta.write_text(json.dumps(veredicto), encoding="utf-8")
    try:
        identidad, errores, desaprobados, *_ = compuerta.veredictos_juez([ruta], proyecto=Path(proyecto), skill="verificar-cita")
    except TypeError:
        identidad, errores, desaprobados, *_ = compuerta.veredictos_juez([ruta], proyecto=Path(proyecto))
    anotar("R4-5 rúbrica de otra skill aceptada para verificar-cita", not errores and not desaprobados, errores or desaprobados)

    # [10c] la compuerta consumidora ante un veredicto guardado sin fallos_criticos (con la rúbrica correcta)
    propia = (PLUGIN / "evals" / "rubricas" / "verificacion.md").read_bytes()
    sin_fallos = {"criterios": [{"numero": i, "criterio": "c", "cumple": "si", "evidencia": "«x»", "evidencia_verificada": True} for i in range(1, 6)],
                  "observaciones": "", "juez": veredicto["juez"],
                  "material": {"sha256_artefactos": ["b" * 64], "rubrica": {"sha256": juez.sha256(propia), "criterios": 5}}}
    ruta.write_text(json.dumps(sin_fallos), encoding="utf-8")
    try:
        try:
            _, errores, desaprobados, *_ = compuerta.veredictos_juez([ruta], proyecto=Path(proyecto), skill="verificar-cita")
        except TypeError:
            _, errores, desaprobados, *_ = compuerta.veredictos_juez([ruta], proyecto=Path(proyecto))
        anotar("R4-10c la compuerta acepta un veredicto sin fallos_criticos", not errores and not desaprobados, errores or "aceptado")
    except Exception as error:  # noqa: BLE001
        anotar("R4-10c la compuerta lanza excepción", True, type(error).__name__)


# [6] [7] guardias de la reserva
def hook(nombre, entrada):
    entorno = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(PLUGIN)}
    entorno.pop("ITOSTACK_PROYECTO", None)
    salida = subprocess.run([sys.executable, str(PLUGIN / "hooks" / nombre)], input=json.dumps(entrada), capture_output=True, text=True, encoding="utf-8", env=entorno, cwd=str(PLUGIN))
    datos = json.loads(salida.stdout) if salida.stdout.strip() else {}
    return (datos.get("hookSpecificOutput") or {}).get("permissionDecision")


with tempfile.TemporaryDirectory() as base:
    reserva = Path(base) / "mi proyecto" / "evals" / "verificar-cita" / "holdout-x"
    reserva.mkdir(parents=True)
    (reserva / "case.yaml").write_text("secreto", encoding="utf-8")
    comando = f'cat "{(Path(base) / "mi proyecto" / "evals" / "verificar-cita").as_posix()}/*/case.yaml"'
    d = hook("guardia_bash.py", {"tool_name": "Bash", "tool_input": {"command": comando}, "cwd": str(PLUGIN)})
    anotar("R4-6 ruta entrecomillada con espacios permite leer la reserva", d != "deny", d)

d = hook("guardia_lectura.py", {"tool_name": "Read", "tool_input": {"file_path": str(PLUGIN / "evals" / "verificar-cita" / "HOLDOUT-fail-clave" / "case.yaml")}})
anotar("R4-7a Read con HOLDOUT- en mayúsculas", d != "deny", d)
d = hook("guardia_bash.py", {"tool_name": "Bash", "tool_input": {"command": "Get-Content EVALS/verificar-cita/*/case.yaml"}, "cwd": str(PLUGIN)})
anotar("R4-7b Get-Content EVALS/… en mayúsculas", d != "deny", d)

sys.stdout.reconfigure(encoding="utf-8")
for id_, estado, detalle in resultados:
    print(f"{estado:13} {id_} {str(detalle)[:110]}")
