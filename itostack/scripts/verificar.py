#!/usr/bin/env python3
"""Verificación forense con veredicto PASS / FAIL / BLOCKED y registro inmutable de evidencia.

Uso:
  verificar.py tesis --registro 2025432 --rubro "..." [--clave ...] [--epoca ...] [--instancia ...]
                     [--tipo ...] [--fecha ...] [--modo cotejo|existencia] [--json]
  verificar.py url   --url https://www.dof.gob.mx/... [--contiene "texto"]... [--json]
  verificar.py app   --base http://127.0.0.1:5000 --ruta ruta.json [--json]
  verificar.py lote  --archivo citas.json [--salida resultados.json]

Salida: 0 = PASS · 1 = FAIL · 2 = BLOCKED · 3 = error de uso.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nucleo import HERRAMIENTA, config as cfg, contexto, veredicto  # noqa: E402
from nucleo.evidencia import AlmacenEvidencia, sha256_resultado  # noqa: E402

DIR_SCRIPTS = Path(__file__).resolve().parent
CODIGOS = {"PASS": 0, "FAIL": 1, "BLOCKED": 2}
INSTALACION = (
    f"Instala las dependencias del navegador forense: cd {DIR_SCRIPTS} && npm install && npx playwright install chromium"
)


def _marca() -> tuple[str, str]:
    ahora = datetime.now(timezone.utc)
    return ahora.isoformat(timespec="seconds"), ahora.strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(2)


def _seguro(texto: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", texto)[:80] or "sin_id"


def _comando_node(script: str) -> list[str] | None:
    node = shutil.which("node")
    if not node:
        return None
    return [node, "--experimental-strip-types", "--no-warnings", str(DIR_SCRIPTS / script)]


def _observar(script: str, argumentos: list[str], tipo: str, identificador: str, timeout_s: int) -> dict:
    """Ejecuta el observador TypeScript. Cualquier falla técnica se convierte en 'no consultado' (BLOCKED)."""
    base = {"tipo": tipo, "identificador": identificador, "consultado": False, "visitas": []}
    comando = _comando_node(script)
    if comando is None:
        return {**base, "motivo_no_consulta": f"Node.js no está instalado. {INSTALACION}"}
    if not (DIR_SCRIPTS / "node_modules" / "playwright").is_dir():
        return {**base, "motivo_no_consulta": f"Playwright no está instalado. {INSTALACION}"}
    try:
        proceso = subprocess.run(comando + argumentos, capture_output=True, text=True, timeout=timeout_s, cwd=DIR_SCRIPTS)
    except subprocess.TimeoutExpired:
        return {**base, "motivo_no_consulta": f"el observador excedió {timeout_s} s"}
    if proceso.returncode != 0:
        detalle = (proceso.stderr or proceso.stdout).strip().splitlines()[-3:]
        return {**base, "motivo_no_consulta": "el observador falló: " + " | ".join(detalle)}
    try:
        return json.loads(proceso.stdout)
    except json.JSONDecodeError:
        return {**base, "motivo_no_consulta": "el observador devolvió una salida no interpretable"}


def _argumentos_navegador(config: dict) -> list[str]:
    argumentos = ["--timeout-ms", str(config["navegador"].get("timeout_ms", 45000))]
    ejecutable = cfg.detectar_navegador(config)
    if ejecutable:
        argumentos += ["--ejecutable", ejecutable]
    elif config["navegador"].get("canal"):
        argumentos += ["--canal", config["navegador"]["canal"]]
    return argumentos


def _cerrar(config: dict, resultado: dict, directorio: Path) -> dict:
    directorio.mkdir(parents=True, exist_ok=True)
    resultado["sha256_resultado"] = sha256_resultado(resultado)
    ruta = directorio / "resultado.json"
    contenido = json.dumps(resultado, ensure_ascii=False, indent=2)
    ruta.write_text(contenido, encoding="utf-8")
    ultimo = Path(config["_proyecto"]) / cfg.DIR_ITOSTACK / "ultimo_resultado.json"
    ultimo.parent.mkdir(parents=True, exist_ok=True)
    ultimo.write_text(contenido, encoding="utf-8")
    almacen = AlmacenEvidencia(cfg.ruta_en_proyecto(config, config["evidencia"]["base_datos"]))
    resultado["_id_registro"] = almacen.registrar(resultado, ruta)
    resultado["_ruta_resultado"] = str(ruta)
    return resultado


def _directorio(config: dict, tipo: str, identificador: str, marca_corta: str) -> Path:
    raiz = cfg.ruta_en_proyecto(config, config["evidencia"]["directorio"])
    return raiz / tipo / _seguro(identificador) / marca_corta


def _ensamblar(tipo: str, identificador: str, decision: veredicto.Resultado, captura: dict, citado: dict, marca: str, directorio: Path) -> dict:
    return {
        "esquema": "itostack.resultado/1",
        "tipo": tipo,
        "identificador": identificador,
        **decision.como_dict(),
        "modo_fuente": captura.get("modo_fuente", "real"),
        "datos_citados": citado,
        "datos_oficiales": captura.get("datos_oficiales") or {},
        "origen_datos": captura.get("origen_datos") or {},
        "visitas": captura.get("visitas", []),
        "marca_tiempo": marca,
        "herramienta": f"{HERRAMIENTA} · {captura.get('herramienta', 'sin observador')}",
        "directorio_evidencia": str(directorio),
    }


def verificar_tesis(config: dict, citado: dict, modo: str = "cotejo") -> dict:
    registro = str(citado.get("registro") or "").strip().upper()
    marca, marca_corta = _marca()
    directorio = _directorio(config, "tesis", registro or "sin_registro", marca_corta)
    fixture = config["sjf"].get("fixture") if config["modo"] == "fixture" else None
    if not registro:
        captura = {"tipo": "tesis", "consultado": False, "visitas": [],
                   "motivo_no_consulta": "la cita no trae registro digital: localízalo en el SJF o repórtala como BLOCKED"}
    elif config["modo"] == "fixture" and not fixture:
        captura = {"tipo": "tesis", "consultado": False, "visitas": [],
                   "motivo_no_consulta": "modo fixture sin archivo sjf.fixture configurado"}
    else:
        sjf = config["sjf"]
        argumentos = [
            "tesis", "--registro", registro, "--salida", str(directorio),
            "--base", sjf["base"], "--ruta-detalle", sjf["ruta_detalle"], "--ruta-api", sjf["ruta_api"],
            "--dominios", ",".join(config["dominios_oficiales"]),
            *_argumentos_navegador(config),
        ]
        if fixture:
            argumentos += ["--fixture", str(cfg.ruta_en_proyecto(config, fixture))]
        limite = int(config["navegador"].get("timeout_ms", 45000) / 1000 * 3 + 30)
        captura = _observar("verificador_fuente.ts", argumentos, "tesis", registro, limite)

    decision = veredicto.decidir_tesis(citado, captura, modo, config["comparacion"].get("ignorar_acentos", True))
    oficial = captura.get("datos_oficiales") or {}
    if oficial:
        decision.advertencias.extend(contexto.advertencias_tesis(oficial, config))
        decision.vvca["contextualizado"] = True
    if captura.get("modo_fuente") == "fixture":
        decision.advertencias.insert(0, "EVIDENCIA DE FIXTURE (datos ficticios): no apta para uso procesal.")
    resultado = _ensamblar("tesis", registro, decision, captura, citado, marca, directorio)
    resultado["modo_cotejo"] = modo
    resultado["obligatoriedad"] = contexto.obligatoriedad(oficial) if oficial else "no determinada"
    return _cerrar(config, resultado, directorio)


def verificar_url(config: dict, url: str, contiene: list[str]) -> dict:
    marca, marca_corta = _marca()
    directorio = _directorio(config, "url", url.split("//")[-1], marca_corta)
    argumentos = ["url", "--url", url, "--salida", str(directorio), "--dominios", ",".join(config["dominios_oficiales"]), *_argumentos_navegador(config)]
    fixture = config["sjf"].get("fixture") if config["modo"] == "fixture" else None
    if fixture:
        argumentos += ["--fixture", str(cfg.ruta_en_proyecto(config, fixture))]
    captura = _observar("verificador_fuente.ts", argumentos, "url", url, 180)
    decision = veredicto.decidir_url(contiene, captura)
    decision.vvca["contextualizado"] = None
    resultado = _ensamblar("url", url, decision, captura, {"url": url, "contiene": contiene}, marca, directorio)
    return _cerrar(config, resultado, directorio)


def verificar_app(config: dict, base: str, ruta_spec: Path) -> dict:
    marca, marca_corta = _marca()
    spec = json.loads(ruta_spec.read_text(encoding="utf-8"))
    nombre = spec.get("nombre", ruta_spec.stem)
    directorio = _directorio(config, "app", nombre, marca_corta)
    argumentos = ["--base", base, "--spec", str(ruta_spec.resolve()), "--salida", str(directorio), *_argumentos_navegador(config)]
    argumentos[argumentos.index("--timeout-ms") + 1] = str(config["app"].get("timeout_ms", 8000))
    captura = _observar("evidencia_web.ts", argumentos, "app", nombre, 300)
    captura.setdefault("base", base)
    decision = veredicto.decidir_app(captura, config["app"].get("fallar_con_errores_consola", True))
    decision.vvca["contextualizado"] = None
    resultado = _ensamblar("app", nombre, decision, captura, {"base": base, "spec": spec}, marca, directorio)
    resultado["pasos"] = captura.get("pasos", [])
    resultado["errores_consola"] = captura.get("errores_consola", [])
    resultado["errores_pagina"] = captura.get("errores_pagina", [])
    return _cerrar(config, resultado, directorio)


def resumen(resultado: dict) -> str:
    lineas = [
        f"VEREDICTO: {resultado['veredicto']} · {resultado['etiqueta']}",
        f"{resultado['tipo']} {resultado['identificador']} — {resultado['motivo']}",
    ]
    for cotejo in resultado.get("cotejos", []):
        lineas.append(f"  cotejo {cotejo['campo']}: {cotejo['estado']} {cotejo.get('detalle') or ''}".rstrip())
    if resultado.get("advertencias"):
        lineas.append("Advertencias:")
        lineas.extend(f"  ⚠ {aviso}" for aviso in resultado["advertencias"])
    lineas.append(f"Evidencia: {resultado['_ruta_resultado']} (SHA-256 {resultado['sha256_resultado'][:16]}…)")
    for visita in resultado.get("visitas", []):
        for archivo in visita.get("archivos", []):
            if archivo.get("tipo") == "captura":
                lineas.append(f"  captura: {archivo['ruta']} (SHA-256 {archivo['sha256'][:16]}…)")
    return "\n".join(lineas)


def ejecutar_lote(config: dict, archivo: Path, salida: Path | None) -> int:
    citas = json.loads(archivo.read_text(encoding="utf-8"))
    citas = citas.get("citas", citas) if isinstance(citas, dict) else citas
    resumenes = []
    for cita in citas:
        if cita.get("omitir"):
            continue
        citado = {k: cita.get(k) for k in veredicto.CAMPOS_CITABLES if cita.get(k)}
        citado["registro"] = cita.get("registro")
        resultado = verificar_tesis(config, citado, cita.get("modo", "cotejo"))
        resumenes.append({
            "id": cita.get("id"),
            "registro": cita.get("registro"),
            "clave": cita.get("clave"),
            "rubro_citado": cita.get("rubro"),
            "extracto": cita.get("extracto"),
            "lineas": cita.get("lineas"),
            "veredicto": resultado["veredicto"],
            "etiqueta": resultado["etiqueta"],
            "motivo": resultado["motivo"],
            "advertencias": resultado["advertencias"],
            "vvca": resultado["vvca"],
            "resultado": resultado["_ruta_resultado"],
            "sha256_resultado": resultado["sha256_resultado"],
        })
        print(f"[{cita.get('id')}] VEREDICTO: {resultado['veredicto']} · {resultado['etiqueta']} — {resultado['motivo']}")
    lote = {"esquema": "itostack.lote/1", "fuente": str(archivo), "marca_tiempo": _marca()[0], "resultados": resumenes}
    contenido = json.dumps(lote, ensure_ascii=False, indent=2)
    (Path(config["_proyecto"]) / cfg.DIR_ITOSTACK / "ultimo_lote.json").write_text(contenido, encoding="utf-8")
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(contenido, encoding="utf-8")
    conteo = {v: sum(1 for r in resumenes if r["veredicto"] == v) for v in veredicto.VEREDICTOS}
    print(f"VEREDICTO LOTE: {conteo['PASS']} PASS · {conteo['FAIL']} FAIL · {conteo['BLOCKED']} BLOCKED")
    return 1 if conteo["FAIL"] else 2 if conteo["BLOCKED"] else 0


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("--proyecto", help="raíz del proyecto (por defecto se detecta)")
    sub = analizador.add_subparsers(dest="accion", required=True)

    p_tesis = sub.add_parser("tesis")
    p_tesis.add_argument("--registro", default="")
    for campo in ("rubro", "clave", "epoca", "instancia", "tipo", "fecha"):
        p_tesis.add_argument(f"--{campo}")
    p_tesis.add_argument("--modo", choices=["cotejo", "existencia"], default="cotejo")
    p_tesis.add_argument("--json", action="store_true")

    p_url = sub.add_parser("url")
    p_url.add_argument("--url", required=True)
    p_url.add_argument("--contiene", action="append", default=[])
    p_url.add_argument("--json", action="store_true")

    p_app = sub.add_parser("app")
    p_app.add_argument("--base", required=True)
    p_app.add_argument("--ruta", required=True, type=Path)
    p_app.add_argument("--json", action="store_true")

    p_lote = sub.add_parser("lote")
    p_lote.add_argument("--archivo", required=True, type=Path)
    p_lote.add_argument("--salida", type=Path)

    args = analizador.parse_args()
    config = cfg.cargar(cfg.raiz_proyecto(args.proyecto) if args.proyecto else None)

    if args.accion == "lote":
        return ejecutar_lote(config, args.archivo, args.salida)
    if args.accion == "tesis":
        citado = {"registro": args.registro}
        for campo, destino in (("rubro", "rubro"), ("clave", "clave"), ("epoca", "epoca"), ("instancia", "instancia"), ("tipo", "tipo"), ("fecha", "fecha_publicacion")):
            if getattr(args, campo):
                citado[destino] = getattr(args, campo)
        resultado = verificar_tesis(config, citado, args.modo)
    elif args.accion == "url":
        resultado = verificar_url(config, args.url, args.contiene)
    else:
        if not args.ruta.is_file():
            print(f"no existe la ruta de verificación {args.ruta}", file=sys.stderr)
            return 3
        resultado = verificar_app(config, args.base, args.ruta)

    print(json.dumps(resultado, ensure_ascii=False, indent=2) if args.json else resumen(resultado))
    return CODIGOS[resultado["veredicto"]]


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.exit(principal())
