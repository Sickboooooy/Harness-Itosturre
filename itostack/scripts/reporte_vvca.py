#!/usr/bin/env python3
"""Validación forense de un documento ajeno (p. ej. un dictamen generado por otra IA).

Paso 1 — extraer candidatos (el agente revisa y corrige citas.json antes de verificar):
  reporte_vvca.py extraer DOCUMENTO [--salida .itostack/citas.json]
Paso 2 — verificar:  verificar.py lote --archivo .itostack/citas.json
Paso 3 — informe:
  reporte_vvca.py informe --documento DOCUMENTO [--lote .itostack/ultimo_lote.json] [--salida salidas/informe-vvca.md]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nucleo import HERRAMIENTA, config as cfg, citas, procedencia  # noqa: E402

ADVERTENCIA_FIJA = (
    "⚠ Respuesta generada por IA. Verificar citas en fuentes oficiales antes de uso procesal: "
    "sjf.scjn.gob.mx · dof.gob.mx · diputados.gob.mx/LeyesBiblio"
)


leer_documento = procedencia.leer_texto  # el mismo texto para extraer, comparar y volver a verificar


def citas_no_literales(resultados: list[dict], texto_documento: str) -> list[str]:
    """Procedencia literal: todo lo que el informe afirma que dice el documento (registro, clave, rubro citado,
    extracto) debe aparecer en él. Así una «corrección» de citas.json no puede convertir una cita mal hecha en PASS."""
    return [f"cita {r.get('id')}: su {campo} «{valor[:60]}» no aparece literal en el documento auditado"
            for r in resultados for campo, valor in procedencia.afirmaciones_de(r) if not procedencia.literal_en(valor, texto_documento)]


def extraer(documento: Path, salida: Path) -> int:
    referencias = [r.como_dict() for r in citas.agrupar_referencias(leer_documento(documento))]
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps({"documento": str(documento), "citas": referencias}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(referencias)} cita(s) candidata(s) en {salida}")
    for ref in referencias:
        print(f"  [{ref['id']}] registro={ref['registro'] or '—'} clave={ref['clave'] or '—'} rubro={'sí' if ref['rubro'] else 'no'}")
    print("Revisa y corrige el archivo (rubro exacto como lo cita el documento) antes de: verificar.py lote --archivo", salida)
    return 0


def _vvca(marca: bool | None) -> str:
    return "—" if marca is None else ("✔" if marca else "✘")


def _escapar(texto: str | None) -> str:
    return (texto or "—").replace("|", "\\|").replace("\n", " ")


def informe(documento: Path, lote: Path, salida: Path, proyecto: Path | None = None) -> int:
    proyecto = (proyecto or cfg.raiz_proyecto()).resolve()
    bytes_lote = lote.read_bytes()
    datos = json.loads(bytes_lote.decode("utf-8"))
    resultados = datos.get("resultados", [])
    try:
        fuente = documento.resolve().relative_to(proyecto).as_posix()
    except ValueError:
        print(f"✘ el documento auditado debe estar dentro del proyecto ({proyecto}) para conservar su procedencia.")
        print("INFORME: BLOCKED — no se escribió ningún archivo.")
        return 2
    texto_documento = leer_documento(documento)
    no_literales = citas_no_literales(resultados, texto_documento)
    if no_literales:
        for problema in no_literales:
            print(f"✘ {problema}")
        print("Corrige .itostack/citas.json para que refleje el documento tal como está (no como debería estar) y repite "
              "verificar.py lote. INFORME: BLOCKED — no se escribió ningún archivo.")
        return 2
    conteo = {v: sum(1 for r in resultados if r["veredicto"] == v) for v in ("PASS", "FAIL", "BLOCKED")}
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lineas = [
        "# Informe de validación forense VVCA",
        "",
        f"- Documento revisado: `{documento}`",
        f"- Fecha: {ahora}",
        f"- Herramienta: {HERRAMIENTA}",
        "- Método: cada cita se consultó en el portal oficial con captura de pantalla y huella SHA-256 (Verificado, Validado, Contextualizado, Auditable).",
        "",
        "## Resumen",
        "",
        "| Veredicto | Citas |",
        "|---|---|",
        f"| ✅ VERIFICADO (PASS) | {conteo['PASS']} |",
        f"| ❌ NO VERIFICABLE (FAIL) | {conteo['FAIL']} |",
        f"| ⚠ NO VERIFICADO (BLOCKED) | {conteo['BLOCKED']} |",
        "",
        "## Matriz VVCA",
        "",
        "| # | Registro | Clave citada | Veredicto | V | V | C | A | Motivo |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in resultados:
        v = r.get("vvca", {})
        lineas.append(
            f"| {r['id']} | {_escapar(r.get('registro'))} | {_escapar(r.get('clave'))} | {r['etiqueta']} | "
            f"{_vvca(v.get('verificado'))} | {_vvca(v.get('validado'))} | {_vvca(v.get('contextualizado'))} | {_vvca(v.get('auditable'))} | "
            f"{_escapar(r['motivo'])} |"
        )
    lineas += ["", "## Detalle por cita", ""]
    for r in resultados:
        resultado = json.loads(Path(r["resultado"]).read_text(encoding="utf-8")) if Path(r["resultado"]).is_file() else {}
        oficial = resultado.get("datos_oficiales", {})
        lineas.append(f"### {r['id']} — {r['etiqueta']}")
        lineas.append("")
        lineas.append(f"- Como aparece en el documento (líneas {r.get('lineas') or '—'}): {r['etiqueta'][:1]} {_escapar(r.get('extracto'))}")
        if r.get("rubro_citado"):
            lineas.append(f"- Rubro citado: {r['etiqueta'][:1]} «{r['rubro_citado']}»")
        if r["veredicto"] == "PASS" and oficial:
            lineas.append(f"- Datos oficiales: {oficial.get('clave', '—')} · {oficial.get('instancia', '—')} · {oficial.get('epoca', '—')} · {oficial.get('tipo', '—')} · publicada {oficial.get('fecha_publicacion', '—')}")
        for cotejo in resultado.get("cotejos", []):
            lineas.append(f"- Cotejo {cotejo['campo']}: {cotejo['estado']} {cotejo.get('detalle') or ''}".rstrip())
        lineas.append(f"- Motivo: {r['motivo']}")
        for aviso in r.get("advertencias", []):
            lineas.append(f"- ⚠ {aviso}")
        lineas.append(f"- Evidencia: `{r['resultado']}` · SHA-256 `{r['sha256_resultado']}`")
        for visita in resultado.get("visitas", []):
            for archivo in visita.get("archivos", []):
                if archivo.get("tipo") == "captura":
                    lineas.append(f"  - captura `{archivo['ruta']}` · SHA-256 `{archivo['sha256'][:16]}…`")
        lineas.append("")
    lineas += [
        "## Conclusión",
        "",
        f"- Citas que NO deben usarse tal como están (FAIL): {conteo['FAIL']}.",
        f"- Citas que requieren verificación manual antes de usarse (BLOCKED): {conteo['BLOCKED']}.",
        f"- Citas verificadas (PASS): {conteo['PASS']}. Revisa sus advertencias de contexto.",
        "- Una cita inventada no se corrige sustituyéndola por otra sin verificar.",
        "",
        ADVERTENCIA_FIJA,
        "",
    ]
    texto = "\n".join(lineas)
    version = json.loads((cfg.RAIZ_PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")).get("version", "?")
    citas_manifiesto = [{k: (str(r[k]) if k == "id" else r[k]) for k in ("id", "veredicto", "registro", "clave", "rubro_citado", "extracto", "sha256_resultado")
                         if r.get(k) is not None} for r in resultados]
    manifiesto = procedencia.manifiesto_informe(texto, version, fuente, procedencia.sha256(documento.read_bytes()), procedencia.sha256(bytes_lote), citas_manifiesto)
    contexto = procedencia.Contexto(lambda _registro: None, procedencia.lector_de_fuentes(proyecto))
    problemas = procedencia.verificar_entrega(texto.encode("utf-8"), manifiesto, contexto)
    if problemas:
        for problema in problemas:
            print(f"✘ {problema}")
        print("INFORME: BLOCKED — la salida no supera la comprobación de entrega; no se escribió ningún archivo.")
        return 2
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_bytes(texto.encode("utf-8"))
    salida.with_name(salida.name + ".procedencia.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Informe: {salida} · procedencia en {salida.name}.procedencia.json")
    print(f"VEREDICTO LOTE: {conteo['PASS']} PASS · {conteo['FAIL']} FAIL · {conteo['BLOCKED']} BLOCKED")
    return 0


def principal() -> int:
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = analizador.add_subparsers(dest="accion", required=True)
    p_ext = sub.add_parser("extraer")
    p_ext.add_argument("documento", type=Path)
    p_ext.add_argument("--salida", type=Path)
    p_inf = sub.add_parser("informe")
    p_inf.add_argument("--documento", type=Path, required=True)
    p_inf.add_argument("--lote", type=Path)
    p_inf.add_argument("--salida", type=Path, default=Path("salidas/informe-vvca.md"))
    args = analizador.parse_args()
    proyecto = cfg.raiz_proyecto()
    if args.accion == "extraer":
        return extraer(args.documento, args.salida or proyecto / cfg.DIR_ITOSTACK / "citas.json")
    return informe(args.documento, args.lote or proyecto / cfg.DIR_ITOSTACK / "ultimo_lote.json", args.salida, proyecto)


if __name__ == "__main__":
    sys.exit(principal())
