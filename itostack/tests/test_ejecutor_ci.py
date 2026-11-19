"""CR-2 (preparación, sin aprovisionar): la plantilla del ejecutor aislado y sus piezas locales.

- workflow: disparo manual, permisos mínimos, ejecutor efímero, secretos por paso, dependencias fijadas, sin publicación;
- scripts: estrictos, sin traza, claves solo en temporales 600, orquestador fijado (nunca el de la candidata);
- instanciar.py falla cerrado; validar_reserva.py (X8, X9); comprobar_versiones.py (versiones y copia fijada);
- atestación OpenSSH con claves efímeras; prueba de humo de guardias; huella de otra copia del plugin.
Todo sintético y local: ninguna credencial real, ningún recurso externo.
"""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from conftest import RAIZ

from nucleo import atestacion

CI = RAIZ / "ejecutor-ci"
PLANTILLA = CI / "plantilla"
WORKFLOW = PLANTILLA / ".github" / "workflows" / "holdout.yml"
SKILL = "verificar-cita"
SSH_KEYGEN = shutil.which("ssh-keygen")
requiere_ssh_keygen = pytest.mark.skipif(SSH_KEYGEN is None, reason="requiere ssh-keygen")


def cargar(nombre, ruta):
    especificacion = importlib.util.spec_from_file_location(nombre, ruta)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


instanciar = cargar("instanciar_ci", CI / "instanciar.py")
validar_reserva = cargar("validar_reserva_ci", PLANTILLA / "ejecutor" / "validar_reserva.py")
comprobar_versiones = cargar("comprobar_versiones_ci", PLANTILLA / "ejecutor" / "comprobar_versiones.py")
humo = cargar("humo_guardias_ci", RAIZ / "evals" / "humo_guardias.py")
compuerta = cargar("compuerta_holdout_ci", RAIZ / "evals" / "compuerta_holdout.py")


def _bash():
    sys.path.insert(0, str(RAIZ / "evals"))
    import autoprueba

    try:
        return autoprueba.ubicar_bash()
    except SystemExit:
        pytest.skip("requiere bash")


# ---------------------------------------------------------------------------------------------------------- workflow

def flujo():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def pasos(f=None):
    f = f or flujo()
    return [p for trabajo in f["jobs"].values() for p in trabajo["steps"]]


class TestWorkflow:
    def test_solo_se_dispara_a_mano(self):
        f = flujo()
        disparadores = f.get("on", f.get(True))  # PyYAML (YAML 1.1) lee la clave «on» como True
        assert set(disparadores) == {"workflow_dispatch"}

    def test_permisos_minimos(self):
        f = flujo()
        assert f["permissions"] == {}
        assert f["jobs"] and all(t.get("permissions") == {"contents": "read"} for t in f["jobs"].values())

    def test_ejecutor_efimero_aprobado_serializado_y_acotado(self):
        f = flujo()
        assert f["concurrency"] == {"group": "holdout", "cancel-in-progress": False}
        assert "env" not in f
        for trabajo in f["jobs"].values():
            assert trabajo["runs-on"] == "ubuntu-24.04"  # alojado por GitHub (efímero); nunca self-hosted
            assert trabajo["environment"] == "holdout"  # revisores obligatorios: cada corrida la aprueba una persona
            assert isinstance(trabajo["timeout-minutes"], int) and 0 < trabajo["timeout-minutes"] <= 120
            assert "env" not in trabajo and "container" not in trabajo and "services" not in trabajo

    def test_ninguna_expresion_se_interpola_en_un_script(self):
        assert all("${{" not in p.get("run", "") for p in pasos())

    def test_cada_secreto_llega_solo_al_paso_que_lo_usa(self):
        texto = "\n".join(l for l in WORKFLOW.read_text(encoding="utf-8").splitlines() if not l.lstrip().startswith("#"))
        referencias = re.findall(r"\$\{\{\s*(secrets\.[A-Z_]+|github\.token)\s*\}\}", texto)
        por_paso = []
        for paso in pasos():
            assert not re.search(r"secrets\.|github\.token", json.dumps({k: v for k, v in paso.items() if k != "env"}))
            por_paso += sorted({m for v in paso.get("env", {}).values() for m in re.findall(r"secrets\.[A-Z_]+|github\.token", str(v))})
        assert referencias and sorted(referencias) == sorted(por_paso)  # ninguno fuera del env de un paso
        assert len(por_paso) == len(set(por_paso))  # y cada uno en un solo paso

    def test_dependencias_externas_fijadas_o_pendientes(self):
        usos = [p["uses"] for p in pasos() if "uses" in p]
        assert usos and all(re.fullmatch(r"[^@\s]+@([0-9a-f]{40}|PENDIENTE-DE-VERIFICAR)", u) for u in usos)

    def test_solo_sale_el_manifiesto_firmado_al_final(self):
        todos = pasos()
        subida = todos[-1]
        assert "upload-artifact" in subida["uses"] and sum("uses" in p for p in todos) == 1
        assert subida["with"]["path"].split() == ["salida/manifiesto.json", "salida/manifiesto.json.sig"]
        assert subida["with"]["if-no-files-found"] == "error" and subida["with"]["retention-days"] <= 7

    def test_orden_validar_obtener_verificar_correr_firmar(self):
        corridas = [p.get("run", "") for p in pasos()]
        indice = {n: next(i for i, r in enumerate(corridas) if n in r) for n in ("CANDIDATA\" =~", "obtener_candidata.sh", "verificar.sh", "correr.sh", "firmar.sh")}
        assert list(indice.values()) == sorted(indice.values())
        assert all(re.search(rf"\[\[ \"\${c}\" =~ \^\[", corridas[0]) for c in ("CANDIDATA", "HUELLA", "SKILL"))


# ----------------------------------------------------------------------------------------------------------- scripts

SCRIPTS_SH = sorted((PLANTILLA / "ejecutor").glob("*.sh"))


@pytest.mark.parametrize("script", SCRIPTS_SH, ids=lambda p: p.name)
def test_scripts_estrictos_sin_traza_y_validos(script):
    codigo = "\n".join(l for l in script.read_text(encoding="utf-8").splitlines() if not l.lstrip().startswith("#"))
    assert "set -euo pipefail" in codigo
    assert not re.search(r"set\s+-[a-z]*x|bash\s+-x|set\s+-o\s+xtrace", codigo)  # una traza filtraría secretos
    salida = subprocess.run([_bash(), "-n", script.as_posix()], capture_output=True, text=True)
    assert salida.returncode == 0, salida.stderr


@pytest.mark.parametrize("nombre", ["obtener_candidata.sh", "firmar.sh"])
def test_las_claves_solo_viven_en_un_temporal_600_que_se_borra(nombre):
    texto = (PLANTILLA / "ejecutor" / nombre).read_text(encoding="utf-8")
    posiciones = [texto.index(f) for f in ("clave=$(mktemp)", "trap 'rm -f \"$clave\"' EXIT", "chmod 600 \"$clave\"", "> \"$clave\"")]
    assert posiciones == sorted(posiciones)  # los permisos se restringen ANTES de escribir la clave


def test_la_candidata_se_obtiene_exacta_y_sin_sus_reservas():
    texto = (PLANTILLA / "ejecutor" / "obtener_candidata.sh").read_text(encoding="utf-8")
    assert "StrictHostKeyChecking=yes" in texto and "known_hosts" in texto
    assert '[ "$(git -C candidata rev-parse HEAD)" = "$CANDIDATA" ]' in texto
    assert "-name 'holdout-*'" in texto


def test_se_usa_el_orquestador_fijado_nunca_el_de_la_candidata():
    for nombre in ("verificar.sh", "correr.sh"):
        texto = (PLANTILLA / "ejecutor" / nombre).read_text(encoding="utf-8")
        llamadas = re.findall(r"python3 (\S+\.py)", texto)
        assert llamadas and all(l.startswith("ejecutor/") for l in llamadas), llamadas
    verificar = (PLANTILLA / "ejecutor" / "verificar.sh").read_text(encoding="utf-8")
    assert "--plugin candidata/itostack" in verificar and '[ "$calculada" = "$HUELLA" ]' in verificar


@requiere_ssh_keygen
def test_firmar_sh_produce_una_firma_verificable_y_borra_la_clave(tmp_path, claves):
    directorio, firmantes = claves
    trabajo, temporales = tmp_path / "trabajo", tmp_path / "tmp"
    (trabajo / "salida").mkdir(parents=True)
    temporales.mkdir()
    manifiesto = b'{"decision": "ACEPTADA", "sintetico": true}\n'
    (trabajo / "salida" / "manifiesto.json").write_bytes(manifiesto)
    entorno = {**os.environ, "CLAVE_FIRMA": (directorio / "ejecutor").read_text(encoding="utf-8"), "TMPDIR": temporales.as_posix()}
    salida = subprocess.run([_bash(), (PLANTILLA / "ejecutor" / "firmar.sh").as_posix()], cwd=trabajo, env=entorno, capture_output=True, text=True)
    assert salida.returncode == 0, salida.stderr
    firma = (trabajo / "salida" / "manifiesto.json.sig").read_bytes()
    assert atestacion.verificar(manifiesto, firma, firmantes, "ejecutor@itostack") == []
    assert list(temporales.iterdir()) == []  # la clave temporal no sobrevive al paso


def test_firmar_sh_sin_clave_falla_sin_firmar(tmp_path):
    (tmp_path / "salida").mkdir()
    (tmp_path / "salida" / "manifiesto.json").write_text("{}", encoding="utf-8")
    entorno = {k: v for k, v in os.environ.items() if k != "CLAVE_FIRMA"}
    salida = subprocess.run([_bash(), (PLANTILLA / "ejecutor" / "firmar.sh").as_posix()], cwd=tmp_path, env=entorno, capture_output=True, text=True)
    assert salida.returncode != 0 and not (tmp_path / "salida" / "manifiesto.json.sig").exists()


# -------------------------------------------------------------------------------------------------------- instanciar

def repositorio(ruta: Path) -> Path:
    ruta.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(ruta)], check=True)
    return ruta


def plantilla_resuelta(tmp_path: Path) -> Path:
    """La plantilla con todo lo pendiente resuelto (valores SINTÉTICOS, solo para probar la regla)."""
    copia = tmp_path / "plantilla"
    shutil.copytree(PLANTILLA, copia)
    flujo_ = copia / ".github" / "workflows" / "holdout.yml"
    flujo_.write_text(flujo_.read_text(encoding="utf-8").replace("@PENDIENTE-DE-VERIFICAR", "@" + "a" * 40), encoding="utf-8")
    ruta = copia / "ejecutor" / "versiones.json"
    versiones = json.loads(ruta.read_text(encoding="utf-8"))
    versiones["pendientes_de_verificar"] = []
    versiones["fijados"] = {"directorio": "orquestador", "archivos": {"evals/orquestador.py": "0" * 64}}
    ruta.write_text(json.dumps(versiones), encoding="utf-8")
    (copia / "ejecutor" / "known_hosts").write_text("github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAISINTETICA\n", encoding="utf-8")
    return copia


def _alterar_flujo(viejo, nuevo):
    def alterar(copia):
        ruta = copia / ".github" / "workflows" / "holdout.yml"
        texto = ruta.read_text(encoding="utf-8")
        assert viejo in texto
        ruta.write_text(texto.replace(viejo, nuevo), encoding="utf-8")
    return alterar


def _alterar_versiones(cambio):
    def alterar(copia):
        ruta = copia / "ejecutor" / "versiones.json"
        versiones = json.loads(ruta.read_text(encoding="utf-8"))
        cambio(versiones)
        ruta.write_text(json.dumps(versiones), encoding="utf-8")
    return alterar


ALTERACIONES_PLANTILLA = {
    "accion por etiqueta": (_alterar_flujo("@" + "a" * 40, "@v4"), "no está fijada"),
    "accion por SHA corto": (_alterar_flujo("@" + "a" * 40, "@aaaaaaa"), "no está fijada"),
    "accion pendiente": (_alterar_flujo("@" + "a" * 40, "@PENDIENTE-DE-VERIFICAR"), "PENDIENTE-DE-VERIFICAR"),
    "version pendiente": (_alterar_versiones(lambda v: v.update(pendientes_de_verificar=["node"])), "pendiente de verificar"),
    "sin herramientas verificadas": (_alterar_versiones(lambda v: v.update(verificadas={})), "no declara herramientas"),
    "orquestador sin fijar": (_alterar_versiones(lambda v: v.pop("fijados")), "no fija la copia"),
    "fijados sin archivos": (_alterar_versiones(lambda v: v.update(fijados={"directorio": "orquestador", "archivos": {}})), "no fija la copia"),
    "known_hosts solo comentarios": (lambda c: (c / "ejecutor" / "known_hosts").write_text("# nada\n\n", encoding="utf-8"), "known_hosts"),
}


class TestInstanciar:
    def test_la_plantilla_actual_no_se_instancia(self, tmp_path):
        problemas = instanciar.impedimentos(PLANTILLA, repositorio(tmp_path / "ejecutor"))
        texto = "\n".join(problemas)
        assert all(f in texto for f in ("PENDIENTE-DE-VERIFICAR", "pendiente de verificar", "known_hosts", "no fija la copia"))

    def test_resuelta_y_en_repositorio_separado_se_instancia(self, tmp_path):
        copia, destino = plantilla_resuelta(tmp_path), repositorio(tmp_path / "ejecutor")
        assert instanciar.impedimentos(copia, destino) == []
        salida = subprocess.run([sys.executable, str(CI / "instanciar.py"), str(destino), "--plantilla", str(copia)], capture_output=True,
                                text=True, encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"})
        assert salida.returncode == 0, salida.stdout + salida.stderr
        assert (destino / ".github" / "workflows" / "holdout.yml").read_bytes() == (copia / ".github" / "workflows" / "holdout.yml").read_bytes()

    @pytest.mark.parametrize("nombre", sorted(ALTERACIONES_PLANTILLA))
    def test_cualquier_pendiente_impide_instanciar(self, tmp_path, nombre):
        alterar, esperado = ALTERACIONES_PLANTILLA[nombre]
        copia = plantilla_resuelta(tmp_path)
        alterar(copia)
        problemas = instanciar.impedimentos(copia, repositorio(tmp_path / "ejecutor"))
        assert any(esperado in p for p in problemas), problemas

    def test_un_destino_que_no_es_repositorio_se_rechaza(self, tmp_path):
        destino = tmp_path / "suelto"
        destino.mkdir()
        assert any("no es la copia de trabajo" in p for p in instanciar.impedimentos(plantilla_resuelta(tmp_path), destino))

    def test_un_destino_dentro_del_constructor_se_rechaza(self, tmp_path):
        constructor = repositorio(tmp_path / "constructor")
        (constructor / "sub").mkdir()
        problemas = instanciar.impedimentos(plantilla_resuelta(tmp_path), constructor / "sub", constructor=constructor)
        assert any("repositorio separado" in p for p in problemas), problemas

    def test_rechazada_no_copia_nada(self, tmp_path):
        destino = repositorio(tmp_path / "ejecutor")
        salida = subprocess.run([sys.executable, str(CI / "instanciar.py"), str(destino)], capture_output=True, text=True,
                                encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"})
        assert salida.returncode == 1 and sorted(p.name for p in destino.iterdir()) == [".git"]


# ---------------------------------------------------------------------------------------------------- reserva nueva

def reserva(tmp_path, casos=("caso-a", "caso-b")):
    raiz = tmp_path / "reserva"
    aprobaciones = []
    for caso in casos:
        directorio = raiz / SKILL / caso
        directorio.mkdir(parents=True)
        (directorio / "case.yaml").write_text(f"name: {caso}\nprompt: sintetico\n", encoding="utf-8")
        (directorio / "documento.md").write_text("Texto sintético sin datos reales.\n", encoding="utf-8")
        aprobaciones.append({"caso": f"{SKILL}/{caso}", "sha256_caso": validar_reserva.huella_caso(directorio), "autor": "Revisora Independiente",
                             "aprobado_por": "Operador", "fecha": "2026-11-19", "datos_sinteticos": True})
    (raiz / "aprobaciones.json").write_text(json.dumps(aprobaciones), encoding="utf-8")
    return raiz, aprobaciones


def _con(campo, valor):
    return lambda a: [dict(a[0], **{campo: valor}), *a[1:]]


ALTERACIONES_APROBACION = {
    "autor igual a quien aprueba": (_con("autor", "Operador"), "misma persona"),
    "autor igual salvo mayusculas y espacios": (_con("autor", "  operador "), "misma persona"),
    "sin autor": (lambda a: [{k: v for k, v in a[0].items() if k != "autor"}, *a[1:]], "falta el autor"),
    "quien aprueba vacio": (_con("aprobado_por", "  "), "falta el autor"),
    "datos no sinteticos": (_con("datos_sinteticos", False), "sintéticos"),
    "sinteticos como texto": (_con("datos_sinteticos", "true"), "sintéticos"),
    "sin fecha": (_con("fecha", ""), "fecha"),
    "huella ajena": (_con("sha256_caso", "0" * 64), "cambió"),
    "aprobacion faltante": (lambda a: a[1:], "sin aprobación"),
    "aprobacion repetida": (lambda a: [a[0], *a], "repetidas"),
    "aprobacion de caso inexistente": (lambda a: [*a, dict(a[0], caso=f"{SKILL}/fantasma")], "no existe"),
    "no es lista": (lambda a: {"aprobaciones": a}, "lista de objetos"),
    "elemento no objeto": (lambda a: [*a, "caso-c"], "lista de objetos"),
}


class TestReserva:
    def test_reserva_valida(self, tmp_path):
        raiz, _ = reserva(tmp_path)
        assert validar_reserva.validar(raiz, SKILL) == []

    @pytest.mark.parametrize("nombre", sorted(ALTERACIONES_APROBACION))
    def test_cualquier_aprobacion_irregular_invalida(self, tmp_path, nombre):
        alterar, esperado = ALTERACIONES_APROBACION[nombre]
        raiz, aprobaciones = reserva(tmp_path)
        (raiz / "aprobaciones.json").write_text(json.dumps(alterar(aprobaciones)), encoding="utf-8")
        problemas = validar_reserva.validar(raiz, SKILL)
        assert any(esperado in p for p in problemas), problemas

    @pytest.mark.parametrize("cambio", ["editar", "agregar", "renombrar", "borrar"])
    def test_un_caso_cambiado_despues_de_aprobarse_no_corre(self, tmp_path, cambio):
        raiz, _ = reserva(tmp_path)
        caso = raiz / SKILL / "caso-a"
        if cambio == "editar":
            (caso / "documento.md").write_text("Texto sintético sin datos reales!\n", encoding="utf-8")
        elif cambio == "agregar":
            (caso / "extra.txt").write_text("x", encoding="utf-8")
        elif cambio == "renombrar":
            (caso / "documento.md").rename(caso / "documento2.md")
        else:
            (caso / "documento.md").unlink()
        assert any("caso-a" in p and "cambió" in p for p in validar_reserva.validar(raiz, SKILL))

    def test_sin_casos_o_sin_aprobaciones_legibles(self, tmp_path):
        assert validar_reserva.validar(tmp_path, SKILL) == [f"la reserva no tiene casos para «{SKILL}»"]
        raiz, _ = reserva(tmp_path)
        (raiz / "aprobaciones.json").write_text("{no es json", encoding="utf-8")
        assert validar_reserva.validar(raiz, SKILL) == ["no hay aprobaciones.json legible"]

    def test_las_aprobaciones_de_otra_skill_no_cuentan_ni_estorban(self, tmp_path):
        raiz, aprobaciones = reserva(tmp_path)
        (raiz / "aprobaciones.json").write_text(json.dumps([*aprobaciones, dict(aprobaciones[0], caso="otra-skill/caso-a")]), encoding="utf-8")
        assert validar_reserva.validar(raiz, SKILL) == []

    @settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(original=st.binary(max_size=64), alterado=st.binary(max_size=64))
    def test_propiedad_la_huella_cambia_con_cualquier_byte(self, tmp_path_factory, original, alterado):
        base = tmp_path_factory.mktemp("huella")
        uno, otro = base / "uno", base / "otro"
        for directorio, contenido in ((uno, original), (otro, alterado)):
            directorio.mkdir()
            (directorio / "case.yaml").write_bytes(contenido)
        assert (validar_reserva.huella_caso(uno) == validar_reserva.huella_caso(otro)) == (original == alterado)

    def test_cli(self, tmp_path):
        raiz, _ = reserva(tmp_path)
        ruta = PLANTILLA / "ejecutor" / "validar_reserva.py"
        entorno = {**os.environ, "PYTHONUTF8": "1"}
        assert subprocess.run([sys.executable, str(ruta), str(raiz), SKILL], capture_output=True, env=entorno).returncode == 0
        (raiz / SKILL / "caso-b" / "case.yaml").write_text("name: otro\n", encoding="utf-8")
        assert subprocess.run([sys.executable, str(ruta), str(raiz), SKILL], capture_output=True, env=entorno).returncode == 1


# --------------------------------------------------------------------------------------------- versiones y copia fijada

def ejecutor_falso(salidas):
    def ejecutar(comando, **_):
        return subprocess.CompletedProcess(comando, 0, salidas[comando[0]], "")
    return ejecutar


def ubicar_todo(nombre):
    return f"/usr/bin/{nombre}"


class TestVersiones:
    SALIDAS = {"claude": "2.1.327 (Claude Code)\n", "git": "git version 2.43.0\n", "node": "v22.11.0\n", "socat": "socat by Gerhard Rieger - see www.dest-unreach.org\nsocat version 1.8.0.0 on Jan  1 2024\n"}

    def test_versiones_exactas_pasan(self, tmp_path):
        versiones = {"verificadas": {"claude": "2.1.327", "git": "2.43.0", "node": "22.11.0", "socat": "1.8.0.0"}}
        assert comprobar_versiones.problemas(versiones, tmp_path, ejecutor_falso(self.SALIDAS), ubicar_todo) == []

    @pytest.mark.parametrize("herramienta,esperada", [("claude", "2.1.32"), ("claude", "2.1.3270"), ("git", "2.43"), ("node", "22.11.1")])
    def test_otra_version_se_bloquea(self, tmp_path, herramienta, esperada):
        problemas = comprobar_versiones.problemas({"verificadas": {herramienta: esperada}}, tmp_path, ejecutor_falso(self.SALIDAS), ubicar_todo)
        assert len(problemas) == 1 and herramienta in problemas[0]

    def test_ausente_desconocida_o_pendiente_se_bloquea(self, tmp_path):
        assert comprobar_versiones.problemas({"verificadas": {"git": "2.43.0"}}, tmp_path, ejecutor_falso(self.SALIDAS), lambda _: None) == ["git: no está instalada"]
        assert comprobar_versiones.problemas({"verificadas": {"curl": "8"}}, tmp_path, ejecutor_falso(self.SALIDAS), ubicar_todo) == ["curl: no se sabe cómo comprobarla"]
        assert comprobar_versiones.problemas({"pendientes_de_verificar": ["node"]}, tmp_path) == ["pendiente de verificar: node"]

    @staticmethod
    def copia_fijada(tmp_path):
        import hashlib

        directorio = tmp_path / "orquestador"
        (directorio / "evals").mkdir(parents=True)
        (directorio / "evals" / "orquestador.py").write_text("print('fijado')\n", encoding="utf-8")
        (directorio / "evals" / "__pycache__").mkdir()
        (directorio / "evals" / "__pycache__" / "x.pyc").write_bytes(b"\x00")
        archivos = {"evals/orquestador.py": hashlib.sha256((directorio / "evals" / "orquestador.py").read_bytes()).hexdigest()}
        return {"fijados": {"directorio": "orquestador", "archivos": archivos}}

    def test_copia_fijada_exacta_pasa(self, tmp_path):
        assert comprobar_versiones.problemas(self.copia_fijada(tmp_path), tmp_path) == []

    @pytest.mark.parametrize("cambio,esperado", [
        (lambda d: (d / "evals" / "orquestador.py").write_text("print('otro')\n", encoding="utf-8"), "no es el fijado"),
        (lambda d: (d / "evals" / "juez_propio.py").write_text("", encoding="utf-8"), "no está en la lista"),
        (lambda d: (d / "evals" / "orquestador.py").unlink(), "falta"),
    ], ids=["contenido", "archivo de mas", "archivo de menos"])
    def test_cualquier_diferencia_en_la_copia_fijada_se_bloquea(self, tmp_path, cambio, esperado):
        versiones = self.copia_fijada(tmp_path)
        cambio(tmp_path / "orquestador")
        problemas = comprobar_versiones.problemas(versiones, tmp_path)
        assert len(problemas) == 1 and esperado in problemas[0], problemas

    def test_fijados_mal_declarados_o_ausentes_se_bloquean(self, tmp_path):
        assert comprobar_versiones.problemas({"fijados": {"directorio": "orquestador"}}, tmp_path)
        assert comprobar_versiones.problemas({"fijados": {"directorio": "no-existe", "archivos": {"a": "0" * 64}}}, tmp_path)


# -------------------------------------------------------------------------------------------------------- atestación

@pytest.fixture(scope="module")
def claves(tmp_path_factory):
    if SSH_KEYGEN is None:
        pytest.skip("requiere ssh-keygen")
    directorio = tmp_path_factory.mktemp("claves-efimeras")
    for nombre in ("ejecutor", "intruso"):
        subprocess.run([SSH_KEYGEN, "-q", "-t", "ed25519", "-N", "", "-C", f"{nombre}-sintetica", "-f", str(directorio / nombre)], check=True)
    firmantes = directorio / "firmantes"
    publica = (directorio / "ejecutor.pub").read_text(encoding="utf-8").strip()
    firmantes.write_text(f'ejecutor@itostack namespaces="{atestacion.ESPACIO}" {publica}\n', encoding="utf-8")
    return directorio, firmantes


HUELLA_RESERVA = "ab" * 32


def atestacion_reserva(**cambios):
    datos = {"estado": "aislada", "huella_reserva": HUELLA_RESERVA, "aprobaciones": [{"caso": f"{SKILL}/caso-a", "autor": "R", "aprobado_por": "O"}]}
    datos.update(cambios)
    return json.dumps(datos, sort_keys=True).encode()


@requiere_ssh_keygen
class TestAtestacion:
    DATOS = b'{"decision": "ACEPTADA", "candidata": "' + b"c" * 64 + b'"}'

    def test_firma_valida(self, claves):
        directorio, firmantes = claves
        firma = atestacion.firmar(self.DATOS, directorio / "ejecutor")
        assert atestacion.verificar(self.DATOS, firma, firmantes, "ejecutor@itostack") == []

    @settings(max_examples=12, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(posicion=st.integers(min_value=0, max_value=len(DATOS) - 1), xor=st.integers(min_value=1, max_value=255))
    def test_propiedad_cualquier_byte_distinto_invalida(self, claves, posicion, xor):
        directorio, firmantes = claves
        firma = atestacion.firmar(self.DATOS, directorio / "ejecutor")
        alterados = bytearray(self.DATOS)
        alterados[posicion] ^= xor
        assert atestacion.verificar(bytes(alterados), firma, firmantes, "ejecutor@itostack") != []

    def test_otra_clave_otro_espacio_u_otra_identidad_invalidan(self, claves):
        directorio, firmantes = claves
        assert atestacion.verificar(self.DATOS, atestacion.firmar(self.DATOS, directorio / "intruso"), firmantes, "ejecutor@itostack") != []
        assert atestacion.verificar(self.DATOS, atestacion.firmar(self.DATOS, directorio / "ejecutor", espacio="otro-uso"), firmantes, "ejecutor@itostack") != []
        assert atestacion.verificar(self.DATOS, atestacion.firmar(self.DATOS, directorio / "ejecutor"), firmantes, "otra@identidad") != []

    def test_firma_rota_ausente_o_sin_herramienta_falla_cerrado(self, claves, tmp_path, monkeypatch):
        directorio, firmantes = claves
        firma = atestacion.firmar(self.DATOS, directorio / "ejecutor")
        lineas = firma.splitlines()
        truncada = b"\n".join([*lineas[:2], *lineas[-1:]])
        assert atestacion.verificar(self.DATOS, truncada, firmantes, "ejecutor@itostack") != []
        assert atestacion.verificar(self.DATOS, b"no es una firma", firmantes, "ejecutor@itostack") != []
        assert atestacion.verificar(self.DATOS, firma, tmp_path / "sin-firmantes", "ejecutor@itostack") != []
        assert atestacion.verificar(self.DATOS, firma, firmantes, "ejecutor@itostack", ssh_keygen=str(tmp_path / "no-existe")) != []
        monkeypatch.setattr(atestacion.shutil, "which", lambda _: None)
        assert atestacion.verificar(self.DATOS, firma, firmantes, "ejecutor@itostack") != []

    def test_atestacion_de_reserva_valida(self, claves):
        directorio, firmantes = claves
        datos = atestacion_reserva()
        firma = atestacion.firmar(datos, directorio / "ejecutor")
        assert atestacion.verificar_atestacion_reserva(datos, firma, firmantes, "ejecutor@itostack", HUELLA_RESERVA) == []

    @pytest.mark.parametrize("datos,esperado", [
        (atestacion_reserva(estado="contaminada"), "no declara la reserva aislada"),
        (atestacion_reserva(huella_reserva="cd" * 32), "otra reserva"),
        (atestacion_reserva(huella_reserva="AB" * 32), "otra reserva"),
        (atestacion_reserva(aprobaciones=[]), "aprobaciones"),
        (atestacion_reserva(aprobaciones="todas"), "aprobaciones"),
        (b"[1, 2]", "no declara la reserva aislada"),
        (b"\xff\xfe", "no es JSON"),
    ], ids=["contaminada", "otra huella", "huella en mayusculas", "sin aprobaciones", "aprobaciones no lista", "no objeto", "no utf8"])
    def test_atestacion_firmada_pero_irregular_no_vale(self, claves, datos, esperado):
        directorio, firmantes = claves
        firma = atestacion.firmar(datos, directorio / "ejecutor")
        problemas = atestacion.verificar_atestacion_reserva(datos, firma, firmantes, "ejecutor@itostack", HUELLA_RESERVA)
        assert len(problemas) == 1 and esperado in problemas[0], problemas

    def test_atestacion_valida_con_firma_de_otra_atestacion_no_vale(self, claves):
        directorio, firmantes = claves
        firma = atestacion.firmar(atestacion_reserva(estado="contaminada"), directorio / "ejecutor")
        assert atestacion.verificar_atestacion_reserva(atestacion_reserva(), firma, firmantes, "ejecutor@itostack", HUELLA_RESERVA) != []


# ------------------------------------------------------------------------------------------------ humo de guardias

def plugin_falso(tmp_path, comandos_bash):
    raiz = tmp_path / "plugin"
    (raiz / "hooks").mkdir(parents=True)
    grupos = [{"matcher": "Bash", "hooks": [{"type": "command", "command": c} for c in comandos_bash]}] if comandos_bash is not None else []
    (raiz / "hooks" / "hooks.json").write_text(json.dumps({"hooks": {"PreToolUse": grupos}}), encoding="utf-8")
    return raiz


DENIEGA = "echo '{\"hookSpecificOutput\": {\"permissionDecision\": \"deny\"}}'"
DISCRIMINA = f"if grep -q -- '--force'; then {DENIEGA}; fi"


class TestHumoGuardias:
    def test_las_guardias_reales_evaluan_en_este_ejecutor(self):
        if not shutil.which("node"):
            pytest.skip("requiere node")
        assert humo.comprobar(RAIZ, _bash()) == []

    def test_sin_node_la_candidata_no_se_evalua(self, tmp_path):
        """Sin node, la guardia deniega por el respaldo «falla cerrado» (salida 2): seguro, pero no evalúa; la corrida
        mediría guardias que deniegan todo. La prueba de humo lo distingue y no deja evaluar."""
        sin_node = tmp_path / "sin-node"
        sin_node.mkdir()
        entorno = {"PATH": str(sin_node), "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")}
        problemas = humo.comprobar(RAIZ, _bash(), entorno_base=entorno)
        assert any("falla cerrado" in p for p in problemas), problemas

    def test_una_guardia_que_discrimina_pasa(self, tmp_path):
        assert humo.comprobar(plugin_falso(tmp_path, [DISCRIMINA]), _bash()) == []

    @pytest.mark.parametrize("comandos,esperado", [
        (["true"], "no deniega"),
        (["echo '{\"hookSpecificOutput\": {\"permissionDecision\": \"allow\"}}'"], "no deniega"),
        (["exit 1"], "no deniega"),
        (["exit 2"], "falla cerrado"),
        (["echo esto no es json"], "no deniega"),
        ([DENIEGA], "no deja pasar la acción inocua"),
        ([DISCRIMINA, DISCRIMINA], "exactamente una"),
        (None, "exactamente una"),
    ], ids=["no hace nada", "permite", "sale 1", "solo falla cerrado", "ilegible", "deniega todo", "dos guardias", "sin guardia"])
    def test_una_guardia_que_no_evalua_impide_evaluar(self, tmp_path, comandos, esperado):
        problemas = humo.comprobar(plugin_falso(tmp_path, comandos), _bash())
        assert any(esperado in p for p in problemas), problemas

    def test_sin_hooks_json_o_sin_bash(self, tmp_path):
        assert humo.comprobar(tmp_path, _bash()) == ["hooks.json no declara exactamente una guardia PreToolUse para Bash"]
        assert humo.comprobar(RAIZ, None) == ["no hay bash: los hooks no podrían ejecutarse"]


# ------------------------------------------------------------------------------------- huella de otra copia del plugin

@pytest.fixture(scope="module")
def copia_plugin(tmp_path_factory):
    copia = tmp_path_factory.mktemp("candidata") / "itostack"
    ignorar = shutil.ignore_patterns("node_modules", "__pycache__", "results")
    for parte in ("skills", "scripts", "hooks", "guardias", "agents", "evals"):
        if (RAIZ / parte).exists():
            shutil.copytree(RAIZ / parte, copia / parte, ignore=ignorar)
    return copia


class TestHuellaDeOtraCopia:
    def test_la_misma_candidata_tiene_la_misma_huella(self, copia_plugin):
        assert compuerta.huella(SKILL, RAIZ) == compuerta.huella(SKILL) == compuerta.huella(SKILL, copia_plugin)

    def test_un_byte_en_la_candidata_cambia_la_huella_y_las_reservas_no(self, copia_plugin):
        antes = compuerta.huella(SKILL, copia_plugin)
        guardia = copia_plugin / "hooks" / "guardia_bash.py"
        original = guardia.read_bytes()
        try:
            guardia.write_bytes(original + b"\n")
            assert compuerta.huella(SKILL, copia_plugin) != antes
        finally:
            guardia.write_bytes(original)
        reserva_ajena = copia_plugin / "evals" / SKILL / "holdout-ajena"
        reserva_ajena.mkdir(parents=True)
        (reserva_ajena / "case.yaml").write_text("name: x\n", encoding="utf-8")
        try:
            assert compuerta.huella(SKILL, copia_plugin) == antes
        finally:
            shutil.rmtree(reserva_ajena)

    def test_cli(self, copia_plugin, tmp_path):
        ruta = RAIZ / "evals" / "compuerta_holdout.py"
        entorno = {k: v for k, v in os.environ.items() if not k.startswith("ITOSTACK_")}
        salida = subprocess.run([sys.executable, str(ruta), "huella", "--skill", SKILL, "--plugin", str(copia_plugin)], capture_output=True, text=True, env=entorno)
        assert salida.returncode == 0 and salida.stdout.strip() == compuerta.huella(SKILL)
        vacia = subprocess.run([sys.executable, str(ruta), "huella", "--skill", SKILL, "--plugin", str(tmp_path)], capture_output=True, text=True, env=entorno)
        assert vacia.returncode == 1 and not vacia.stdout.strip()
