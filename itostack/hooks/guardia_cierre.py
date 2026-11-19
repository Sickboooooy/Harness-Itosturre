#!/usr/bin/env python3
"""Stop: «Prove It Works». Si el mensaje final afirma éxito sin evidencia en la sesión, el agente sigue.

Afirmar verificación exige una línea `VEREDICTO: PASS` en algún resultado de herramienta de la
sesión; afirmar que las pruebas pasan exige una salida de pytest/jest con aprobados y sin fallos.
Además (CR-1.2), todo entregable jurídico modificado durante la sesión debe superar la comprobación de entrega: un
manifiesto ausente, incompleto o inconsistente, o un tramo que ya no se verifica contra sus fuentes, es BLOCKED.
"""

from __future__ import annotations

import fnmatch
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402
from nucleo import transcripciones  # noqa: E402

AFIRMA_VERIFICACION = re.compile(
    r"✅\s*VERIFICAD|\bveredicto\s*:?\s*\**PASS\b|\bqued[óo]\s+verificad|\best[áa]n?\s+verificad[oa]s?\b|"
    r"\bfunciona\s+correctamente\b|\bdemostr[ée]\s+que\s+funciona\b|\bcitas?\s+verificadas?\b",
    re.IGNORECASE,
)
AFIRMA_PRUEBAS = re.compile(r"\b(?:todas\s+las\s+)?pruebas\s+(?:pasan|pasaron|en\s+verde)\b|\btests?\s+(?:pasan|en\s+verde)\b", re.IGNORECASE)
NIEGA = re.compile(r"\bno\s+(?:est[áa]n?|qued[óo]|fue)\s+verificad|\bsin\s+verificar\b|\bBLOCKED\b|\bFAIL\b", re.IGNORECASE)
EVIDENCIA_PASS = re.compile(r"VEREDICTO:\s*PASS\b|\"veredicto\":\s*\"PASS\"|ENSAMBLADO:\s*PASS\b")
PRUEBAS_OK = re.compile(r"\b\d+\s+passed\b|Tests?:\s+\d+\s+passed")
PRUEBAS_MAL = re.compile(r"\b\d+\s+(?:failed|errors?)\b")


def evaluar(ultimo: str, resultados: list[str]) -> str | None:
    if not ultimo:
        return None
    afirma_verificacion = bool(AFIRMA_VERIFICACION.search(ultimo)) and not NIEGA.search(ultimo)
    if afirma_verificacion and not any(EVIDENCIA_PASS.search(r) for r in resultados):
        return (
            "afirmas que algo está verificado o funciona, pero en esta sesión no hay ningún resultado con «VEREDICTO: PASS». "
            "Ejecuta la verificación (verificar.py / demuestra-que-funciona) y cita su evidencia, o reporta BLOCKED con la causa."
        )
    if AFIRMA_PRUEBAS.search(ultimo):
        salidas = [r for r in resultados if PRUEBAS_OK.search(r) or PRUEBAS_MAL.search(r)]
        if not salidas or PRUEBAS_MAL.search(salidas[-1]):
            return "afirmas que las pruebas pasan, pero la última ejecución de pruebas de la sesión no lo muestra. Córrelas y muestra la salida."
    return None


VENTANA_SIN_TRANSCRIPCION = 12 * 3600
EXCLUIR = {".git", "node_modules", ".itostack", "__pycache__"}


def inicio_de_sesion(transcripcion: Path | None) -> float:
    """Primera marca de tiempo de la transcripción; sin ella, las últimas 12 horas."""
    if transcripcion and transcripcion.is_file():
        with transcripcion.open(encoding="utf-8", errors="replace") as archivo:
            for linea in archivo:
                try:
                    marca = json.loads(linea).get("timestamp")
                    return datetime.fromisoformat(str(marca).replace("Z", "+00:00")).timestamp()
                except (ValueError, AttributeError, TypeError):
                    continue
    return time.time() - VENTANA_SIN_TRANSCRIPCION


def entregables_de_la_sesion(proyecto: Path, config: dict, desde: float) -> list[Path]:
    """Archivos de `salidas_juridicas` (texto o .docx) modificados desde `desde`, sin sus manifiestos."""
    patrones = config.get("salidas_juridicas", [])
    hallados = []
    for ruta in proyecto.rglob("*"):
        relativa = ruta.relative_to(proyecto)
        if any(parte in EXCLUIR for parte in relativa.parts) or not ruta.is_file() or ruta.name.endswith(".procedencia.json"):
            continue
        if ruta.suffix.lower() in {".md", ".txt", ".docx"} and any(fnmatch.fnmatch(relativa.as_posix(), p) for p in patrones) and ruta.stat().st_mtime >= desde:
            hallados.append(ruta)
    return sorted(hallados)


def entregables_bloqueados(entrada: dict, desde: float) -> list[str]:
    if not _comun.tiene_itostack(entrada):
        return []
    import verificar_entrega

    config = _comun.configuracion(entrada)
    proyecto = _comun.proyecto(entrada)
    contexto = verificar_entrega.contexto_del_proyecto(config)
    motivos = []
    for ruta in entregables_de_la_sesion(proyecto, config, desde):
        problemas = verificar_entrega.revisar(ruta, contexto)
        if problemas:
            motivos.append(f"{ruta.relative_to(proyecto).as_posix()}: {problemas[0]}")
    return motivos


def principal() -> int:
    entrada = _comun.leer_entrada()
    if entrada.get("stop_hook_active"):
        return 0
    transcripcion = entrada.get("transcript_path")
    ruta = Path(transcripcion) if transcripcion else None
    razones = []
    if ruta and ruta.is_file():
        razon = evaluar(transcripciones.ultimo_texto_asistente(ruta), transcripciones.textos_resultados(ruta))
        if razon:
            razones.append(razon)
    try:
        bloqueados = entregables_bloqueados(entrada, inicio_de_sesion(ruta))
    except Exception as error:  # este control falla cerrado: sin comprobación no hay entrega
        bloqueados = [f"no se pudo comprobar la entrega de los documentos jurídicos ({error})"]
    if bloqueados:
        razones.append("BLOCKED: estos documentos jurídicos de la sesión no son entregables:\n" + "\n".join(f"- {m}" for m in bloqueados[:10])
                       + "\nCorrige el borrador y vuelve a ensamblar; compruébalo con verificar_entrega.py.")
    if razones:
        _comun.bloquear_cierre("\n\n".join(razones))
    return 0


if __name__ == "__main__":
    sys.exit(_comun.ejecutar(principal, "Stop", "abierto"))
