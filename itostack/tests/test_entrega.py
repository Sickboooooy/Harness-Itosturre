"""CR-1.2 · la comprobación de entrega conectada a la CLI, a los hooks (escritura, cierre, salida) y al informe VVCA.

Pruebas con procesos reales sobre un proyecto inicializado. Cada una es negativa o positiva sobre un control: un
entregable sin manifiesto, con el manifiesto incompleto o con una fuente que cambió es BLOCKED; el flujo legítimo
(borrador con marcadores → ensamblado → entrega) sigue funcionando.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import pytest

from conftest import SCRIPTS, correr_hook, decision

ACTO = "La autoridad funda su acto en la tesis 2a./J. 58/2010 (9a.), que considera aplicable al caso."
BORRADOR = ("Se impugna el acto. La autoridad invoca [[CITA_AJENA:2a./J. 58/2010 (9a.)|expediente/acto.md]] "
            "y omite [[NO_VERIFICADO:la fecha de notificación del acto]].\n")


def correr(proyecto, script, *argumentos):
    entorno = {k: v for k, v in os.environ.items() if not k.startswith("ITOSTACK_")}
    entorno["PYTHONUTF8"] = "1"
    return subprocess.run([sys.executable, str(SCRIPTS / script), *argumentos], cwd=proyecto, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=entorno, timeout=120)


def ensamblar(proyecto, texto, nombre="escrito", *extra):
    (proyecto / "borradores").mkdir(exist_ok=True)
    (proyecto / "borradores" / f"{nombre}.md").write_text(texto, encoding="utf-8")
    return correr(proyecto, "ensamblar_documento.py", f"borradores/{nombre}.md", "--salida", f"salidas/{nombre}.md", *extra)


@pytest.fixture
def entregable(proyecto):
    (proyecto / "expediente").mkdir()
    (proyecto / "expediente" / "acto.md").write_text(ACTO, encoding="utf-8")
    resultado = ensamblar(proyecto, BORRADOR)
    assert resultado.returncode == 0, resultado.stdout
    return proyecto / "salidas" / "escrito.md"


def manifiesto_de(ruta):
    return ruta.with_name(ruta.name + ".procedencia.json")


def revisar(proyecto, ruta):
    sys.path.insert(0, str(SCRIPTS))
    import verificar_entrega
    from nucleo import config as cfg

    return verificar_entrega.revisar(ruta, verificar_entrega.contexto_del_proyecto(cfg.cargar(proyecto)))


# ---------------------------------------------------------------- comprobación de entrega (CLI y reglas)

class TestComprobacionDeEntrega:
    def test_flujo_legitimo_pasa_y_no_muestra_marcadores(self, proyecto, entregable):
        salida = correr(proyecto, "verificar_entrega.py", str(entregable))
        assert salida.returncode == 0 and "PASS" in salida.stdout, salida.stdout
        texto = entregable.read_text(encoding="utf-8")
        assert "[[" not in texto and "CITA_AJENA" not in texto and "⚠ CITA NO VERIFICADA" in texto and "(⚠ NO VERIFICADO)" in texto

    def test_codigos_de_uso(self, proyecto):
        assert correr(proyecto, "verificar_entrega.py").returncode == 3
        assert correr(proyecto, "verificar_entrega.py", "salidas/no-existe.md").returncode == 3

    def test_escrito_a_mano_sin_manifiesto_es_blocked(self, proyecto):
        (proyecto / "salidas").mkdir(exist_ok=True)
        (proyecto / "salidas" / "a-mano.md").write_text("Texto sin citas, escrito a mano.\n", encoding="utf-8")
        salida = correr(proyecto, "verificar_entrega.py", "salidas/a-mano.md")
        assert salida.returncode == 2 and "BLOCKED" in salida.stdout

    def test_alterar_el_entregable_es_blocked(self, proyecto, entregable):
        entregable.write_bytes(entregable.read_bytes().replace("omite".encode(), "admite".encode()))
        assert correr(proyecto, "verificar_entrega.py", str(entregable)).returncode == 2

    def test_manifiesto_incompleto_o_ajeno_es_blocked(self, proyecto, entregable):
        base = json.loads(manifiesto_de(entregable).read_text(encoding="utf-8"))
        assert revisar(proyecto, entregable) == []
        casos = [("quitar", (clave,)) for clave in base] + [("quitar", ("tramos", i, clave)) for i, t in enumerate(base["tramos"]) for clave in t]
        casos += [("agregar", ()), ("agregar", ("tramos", 0)), ("tipo", ("entregable",)), ("tipo", ("tramos", 0, "inicio"))]
        for accion, ruta in casos:
            datos = json.loads(json.dumps(base))
            padre = datos
            for paso in ruta[:-1] if accion != "agregar" else ruta:
                padre = padre[paso]
            if accion == "quitar":
                del padre[ruta[-1]]
            elif accion == "agregar":
                padre["campo_ajeno"] = True
            else:
                padre[ruta[-1]] = str(padre[ruta[-1]])
            manifiesto_de(entregable).write_text(json.dumps(datos), encoding="utf-8")
            assert revisar(proyecto, entregable), (accion, ruta)

    @pytest.mark.parametrize("cambio", ["modificar", "borrar"])
    def test_la_fuente_de_la_cita_ajena_debe_seguir_igual(self, proyecto, entregable, cambio):
        fuente = proyecto / "expediente" / "acto.md"
        if cambio == "modificar":
            fuente.write_text(ACTO + " Se agrega un párrafo.", encoding="utf-8")
        else:
            fuente.unlink()
        assert any("fuente" in p for p in revisar(proyecto, entregable))

    def test_derivado_docx_atado_a_su_origen(self, proyecto, entregable):
        sys.path.insert(0, str(SCRIPTS))
        from nucleo import procedencia

        docx = entregable.with_suffix(".docx")
        docx.write_bytes(b"PK\x03\x04 docx de prueba")
        derivado = {"contrato": procedencia.CONTRATO, "version_plugin": "prueba", "tipo_documento": "derivado", "derivado_de": entregable.name,
                    "sha256_documento": procedencia.sha256(docx.read_bytes()), "sha256_origen": procedencia.sha256(entregable.read_bytes())}
        manifiesto_de(docx).write_text(json.dumps(derivado), encoding="utf-8")
        assert revisar(proyecto, docx) == []
        docx.write_bytes(b"PK\x03\x04 docx alterado")
        assert revisar(proyecto, docx)
        derivado["sha256_documento"] = procedencia.sha256(docx.read_bytes())
        manifiesto_de(docx).write_text(json.dumps(dict(derivado, campo_ajeno=1)), encoding="utf-8")
        assert revisar(proyecto, docx)
        manifiesto_de(docx).write_text(json.dumps(derivado), encoding="utf-8")
        assert revisar(proyecto, docx) == []
        # El origen se vuelve a ensamblar (válido, pero otro): el .docx quedó viejo y ya no corresponde.
        assert ensamblar(proyecto, BORRADOR.replace("Se impugna el acto.", "Se impugna la resolución.")).returncode == 0
        assert revisar(proyecto, entregable) == [] and revisar(proyecto, docx)


# ---------------------------------------------------------------- guardia de escritura

def escribir(proyecto, ruta, contenido, herramienta="Write", **extra):
    entrada = {"tool_name": herramienta, "cwd": str(proyecto), "tool_input": {"file_path": str(proyecto / ruta), **extra}}
    if herramienta == "Write":
        entrada["tool_input"]["content"] = contenido
    return decision(correr_hook("guardia_escritura.py", entrada))


class TestGuardiaDeEscritura:
    @pytest.mark.parametrize("ruta", ["salidas/x.md", "escritos/demanda.md", "dictamenes/d.md", "notas/opinion.juridico.md"])
    def test_ningun_entregable_se_escribe_a_mano(self, proyecto, ruta):
        assert escribir(proyecto, ruta, "Texto sin ninguna cita.") == "deny"

    def test_editar_un_entregable_ensamblado_se_deniega(self, proyecto, entregable):
        assert escribir(proyecto, "salidas/escrito.md", None, "Edit", old_string="omite", new_string="admite") == "deny"
        assert escribir(proyecto, "salidas/escrito.md", None, "MultiEdit", edits=[{"old_string": "omite", "new_string": "admite"}]) == "deny"

    @pytest.mark.parametrize("ruta", ["salidas/escrito.md.procedencia.json", "otra/carpeta/x.md.procedencia.json", "itostack/evals/reserva.json"])
    def test_manifiestos_y_estado_de_la_reserva_protegidos(self, proyecto, ruta):
        assert escribir(proyecto, ruta, "{}") == "deny"

    @pytest.mark.parametrize("texto", ["registro digital 2012345", "la 1a./J. 45/2019 (10a.)", "rubro: «UNO DE MEMORIA.»", "⚠ NO VERIFICADO",
                                       "❌", "✅ VERIFICADA", "[[CITA:FICT-0001|resumen]]", "[[OTRO:x]]"])
    def test_borrador_con_cita_o_marca_a_mano_se_deniega(self, proyecto, texto):
        assert escribir(proyecto, "borradores/b.md", f"Argumento: {texto}.") == "deny"

    def test_borrador_con_marcadores_pasa(self, proyecto):
        assert escribir(proyecto, "borradores/b.md", BORRADOR + "Véase [[CITA:FICT-0001|clave]].") is None

    def test_una_edicion_que_completa_una_cita_con_lo_que_ya_estaba_se_deniega(self, proyecto):
        (proyecto / "borradores").mkdir()
        (proyecto / "borradores" / "b.md").write_text("Véase el registro digital PENDIENTE del criterio.\n", encoding="utf-8")
        # El texto nuevo, solo, no trae ninguna cita: lo que se revisa es cómo queda el archivo.
        assert escribir(proyecto, "borradores/b.md", None, "Edit", old_string="PENDIENTE", new_string="2012345") == "deny"
        assert escribir(proyecto, "borradores/b.md", None, "Edit", old_string="el registro digital PENDIENTE", new_string="[[CITA:2012345]]") is None

    def test_modo_estricto_revisa_todo_markdown(self, proyecto):
        ruta = proyecto / ".itostack" / "config.json"
        ruta.write_text(json.dumps({**json.loads(ruta.read_text(encoding="utf-8")), "modo_estricto_md": True}), encoding="utf-8")
        assert escribir(proyecto, "notas/n.md", "Ver registro digital 2012345.") == "deny"
        assert escribir(proyecto, "notas/n.md", "Notas sin citas.") is None


# ---------------------------------------------------------------- cierre de sesión

def transcripcion(proyecto, hace=timedelta(minutes=1)):
    ruta = proyecto / "transcripcion.jsonl"
    marca = (datetime.now(timezone.utc) - hace).isoformat()
    ruta.write_text(json.dumps({"type": "user", "timestamp": marca, "message": {"role": "user", "content": "hola"}}) + "\n", encoding="utf-8")
    return ruta


def cerrar(proyecto, **extra):
    return correr_hook("guardia_cierre.py", {"cwd": str(proyecto), "transcript_path": str(transcripcion(proyecto)), **extra})


class TestCierreDeSesion:
    def test_entregable_valido_no_bloquea(self, proyecto, entregable):
        assert cerrar(proyecto).get("decision") != "block"

    def test_entregable_escrito_a_mano_bloquea(self, proyecto, entregable):
        (proyecto / "salidas" / "a-mano.md").write_text("Escrito sin ensamblar.\n", encoding="utf-8")
        salida = cerrar(proyecto)
        assert salida.get("decision") == "block" and "BLOCKED" in salida["reason"] and "a-mano.md" in salida["reason"]

    def test_entregable_alterado_bloquea(self, proyecto, entregable):
        entregable.write_bytes(entregable.read_bytes() + b"\nAgregado a mano.\n")
        assert cerrar(proyecto).get("decision") == "block"

    def test_documentos_anteriores_a_la_sesion_no_se_revisan(self, proyecto):
        """Incompatibilidad documentada: un documento de 0.1.x sin manifiesto no bloquea la sesión si no se tocó en ella."""
        (proyecto / "salidas").mkdir()
        viejo = proyecto / "salidas" / "viejo.md"
        viejo.write_text("Documento de una versión anterior.\n", encoding="utf-8")
        hace_dos_dias = time.time() - 2 * 86400
        os.utime(viejo, (hace_dos_dias, hace_dos_dias))
        assert cerrar(proyecto).get("decision") != "block"

    def test_no_entra_en_bucle(self, proyecto, entregable):
        (proyecto / "salidas" / "a-mano.md").write_text("Escrito sin ensamblar.\n", encoding="utf-8")
        assert cerrar(proyecto, stop_hook_active=True).get("decision") != "block"


# ---------------------------------------------------------------- salida externa (MCP)

class TestSalidaExterna:
    def _enviar(self, proyecto, adjunto):
        return correr_hook("guardia_externo.py", {"tool_name": "mcp__Gmail__send_message", "cwd": str(proyecto), "permission_mode": "default",
                                                  "tool_input": {"to": "cliente@example.invalid", "body": "Adjunto el escrito.", "attachments": [adjunto]}})

    def test_enviar_un_entregable_no_valido_se_deniega(self, proyecto, entregable):
        (proyecto / "salidas" / "a-mano.md").write_text("Escrito sin ensamblar.\n", encoding="utf-8")
        salida = self._enviar(proyecto, "salidas/a-mano.md")
        assert decision(salida) == "deny" and "no es entregable" in salida["hookSpecificOutput"]["permissionDecisionReason"]

    def test_enviar_un_entregable_valido_queda_en_la_compuerta_humana(self, proyecto, entregable):
        assert decision(self._enviar(proyecto, "salidas/escrito.md")) == "ask"


# ---------------------------------------------------------------- informe VVCA: procedencia literal

DICTAMEN = ("Dictamen de otra IA.\n\nEl acto viola la tesis con registro digital FICT-0404, de rubro: «RUBRO COMO LO ESCRIBIÓ EL DICTAMEN.», "
            "que el autor considera obligatoria.\n")


def lote(proyecto, rubro="RUBRO COMO LO ESCRIBIÓ EL DICTAMEN."):
    parrafo = DICTAMEN.split("\n\n")[1].strip()
    datos = {"resultados": [{"id": "c01", "registro": "FICT-0404", "clave": None, "rubro_citado": rubro, "extracto": parrafo[:300], "lineas": [3],
                             "veredicto": "FAIL", "etiqueta": "❌ NO VERIFICABLE", "motivo": "el registro no existe en el portal", "advertencias": [],
                             "vvca": {"verificado": False}, "resultado": "no-existe.json", "sha256_resultado": "ab" * 32}]}
    ruta = proyecto / ".itostack" / "lote.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return ruta


class TestInformeVVCA:
    def _informe(self, proyecto, documento="dictamen.md"):
        return correr(proyecto, "reporte_vvca.py", "informe", "--documento", documento, "--lote", ".itostack/lote.json", "--salida", "salidas/informe-vvca.md")

    def test_informe_con_procedencia_literal_es_entregable(self, proyecto):
        (proyecto / "dictamen.md").write_text(DICTAMEN, encoding="utf-8")
        lote(proyecto)
        assert self._informe(proyecto).returncode == 0
        informe = proyecto / "salidas" / "informe-vvca.md"
        assert manifiesto_de(informe).is_file() and correr(proyecto, "verificar_entrega.py", str(informe)).returncode == 0

    def test_un_rubro_corregido_hacia_el_oficial_se_bloquea(self, proyecto):
        """Si citas.json se «corrige» con un rubro que el documento no dice, el informe atribuiría al documento una cita que
        no hizo (y podría dar PASS a una cita mal hecha): BLOCKED y no se escribe nada."""
        (proyecto / "dictamen.md").write_text(DICTAMEN, encoding="utf-8")
        lote(proyecto, rubro="EL RUBRO OFICIAL CORRECTO.")
        salida = self._informe(proyecto)
        # El control previo del renderizador (no solo la autoverificación final) lo detecta y dice cómo corregirlo.
        assert salida.returncode == 2 and "no aparece literal" in salida.stdout and "Corrige .itostack/citas.json" in salida.stdout
        assert not (proyecto / "salidas" / "informe-vvca.md").exists()

    def test_las_citas_del_manifiesto_deben_ser_literales_en_el_documento(self, proyecto):
        """Segunda capa: la comprobación de entrega vuelve a cotejar contra el documento auditado lo que el manifiesto
        afirma que dice, aunque las huellas del informe y del documento no hayan cambiado."""
        (proyecto / "dictamen.md").write_text(DICTAMEN, encoding="utf-8")
        lote(proyecto)
        assert self._informe(proyecto).returncode == 0
        manifiesto = manifiesto_de(proyecto / "salidas" / "informe-vvca.md")
        datos = json.loads(manifiesto.read_text(encoding="utf-8"))
        datos["citas"][0]["rubro_citado"] = "EL RUBRO OFICIAL CORRECTO."
        manifiesto.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        assert any("no aparece literal" in p for p in revisar(proyecto, proyecto / "salidas" / "informe-vvca.md"))

    def test_cambiar_el_documento_auditado_invalida_el_informe(self, proyecto):
        (proyecto / "dictamen.md").write_text(DICTAMEN, encoding="utf-8")
        lote(proyecto)
        assert self._informe(proyecto).returncode == 0
        (proyecto / "dictamen.md").write_text(DICTAMEN.replace("FICT-0404", "FICT-0405"), encoding="utf-8")
        assert correr(proyecto, "verificar_entrega.py", "salidas/informe-vvca.md").returncode == 2

    def test_documento_fuera_del_proyecto_se_bloquea(self, proyecto, tmp_path_factory):
        afuera = tmp_path_factory.mktemp("afuera") / "dictamen.md"
        afuera.write_text(DICTAMEN, encoding="utf-8")
        lote(proyecto)
        assert self._informe(proyecto, str(afuera)).returncode == 2
