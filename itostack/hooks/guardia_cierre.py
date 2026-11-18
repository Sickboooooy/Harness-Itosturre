#!/usr/bin/env python3
"""Stop: «Prove It Works». Si el mensaje final afirma éxito sin evidencia en la sesión, el agente sigue.

Afirmar verificación exige una línea `VEREDICTO: PASS` en algún resultado de herramienta de la
sesión; afirmar que las pruebas pasan exige una salida de pytest/jest con aprobados y sin fallos.
"""

from __future__ import annotations

import re
import sys
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


def principal() -> int:
    entrada = _comun.leer_entrada()
    if entrada.get("stop_hook_active"):
        return 0
    transcripcion = entrada.get("transcript_path")
    if not transcripcion or not Path(transcripcion).is_file():
        return 0
    ruta = Path(transcripcion)
    razon = evaluar(transcripciones.ultimo_texto_asistente(ruta), transcripciones.textos_resultados(ruta))
    if razon:
        _comun.bloquear_cierre(razon)
    return 0


if __name__ == "__main__":
    sys.exit(_comun.ejecutar(principal, "Stop", "abierto"))
