"""Flujos completos con navegador real contra fixtures interceptados (sin red)."""

import json
import subprocess
import sys

from conftest import SCRIPTS, requiere_navegador, verificar

R1 = "CRITERIO FICTICIO DE PRUEBA. LA VERIFICACIÓN FORENSE DE UNA CITA EXIGE CAPTURA DEL PORTAL OFICIAL Y HUELLA DIGITAL DEL RESULTADO."


def correr(proyecto, script, *argumentos):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *argumentos], cwd=proyecto, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)


@requiere_navegador
def test_tesis_pass_fail_blocked_y_registro(proyecto):
    assert verificar(proyecto, "tesis", "--registro", "FICT-0001", "--rubro", R1).returncode == 0
    assert verificar(proyecto, "tesis", "--registro", "FICT-0404", "--rubro", "INVENTADO PARA PRUEBA").returncode == 1
    assert verificar(proyecto, "tesis", "--registro", "FICT-0500", "--rubro", "X").returncode == 2
    assert verificar(proyecto, "tesis", "--registro", "1234567890", "--rubro", "X").returncode == 2
    ultimo = json.loads((proyecto / ".itostack" / "ultimo_resultado.json").read_text(encoding="utf-8"))
    assert ultimo["veredicto"] == "BLOCKED" and "formato inválido" in ultimo["motivo"]
    recientes = correr(proyecto, "evidencia_db.py", "recientes")
    assert recientes.stdout.count("\n") >= 4
    assert correr(proyecto, "evidencia_db.py", "auditar").returncode == 0


@requiere_navegador
def test_url_oficial(proyecto):
    url = "https://www.dof.gob.mx/nota_detalle.php?codigo=FICT0001&fecha=16/10/2025"
    assert verificar(proyecto, "url", "--url", url, "--contiene", "DECRETO FICTICIO DE PRUEBA").returncode == 0
    assert verificar(proyecto, "url", "--url", url, "--contiene", "texto que no está").returncode == 1
    assert verificar(proyecto, "url", "--url", "https://ejemplo.com/x").returncode == 2


@requiere_navegador
def test_ensamblado_falla_cerrado_y_luego_pasa(proyecto):
    borrador = proyecto / "borrador.md"
    borrador.write_text("Aplica [[CITA:FICT-0001]] y también [[CITA:FICT-0002|clave]].\n", encoding="utf-8")
    salida = proyecto / "salidas" / "escrito.md"
    bloqueado = correr(proyecto, "ensamblar_documento.py", str(borrador), "--salida", str(salida))
    assert bloqueado.returncode == 2 and not salida.exists()
    verificar(proyecto, "tesis", "--registro", "FICT-0001", "--modo", "existencia")
    verificar(proyecto, "tesis", "--registro", "FICT-0002", "--modo", "existencia")
    listo = correr(proyecto, "ensamblar_documento.py", str(borrador), "--salida", str(salida))
    assert listo.returncode == 0, listo.stdout
    texto = salida.read_text(encoding="utf-8")
    assert "EXIGE CAPTURA DEL PORTAL OFICIAL" in texto and "[^ev1]" in texto and "[^ev2]" in texto and "Sala extinta" in texto


@requiere_navegador
def test_ensamblado_rechaza_cita_a_mano(proyecto):
    borrador = proyecto / "b.md"
    borrador.write_text("Aplica la tesis con registro digital 2099998, cuyo rubro escribí de memoria.\n", encoding="utf-8")
    resultado = correr(proyecto, "ensamblar_documento.py", str(borrador), "--salida", str(proyecto / "salidas" / "x.md"))
    assert resultado.returncode == 2 and "escrito a mano" in resultado.stdout
