"""Contextualización (la C de VVCA): corte temporal, órgano emisor y obligatoriedad.

Estas reglas no cambian el veredicto; producen advertencias ⚠ que el agente debe trasladar
al escrito o resolver con una verificación adicional.
"""

from __future__ import annotations

import re
from datetime import date

from . import normalizacion as norm


def advertencias_tesis(oficial: dict, config: dict) -> list[str]:
    avisos: list[str] = []
    instancia = norm.sin_acentos(str(oficial.get("instancia") or "")).lower()
    materia = norm.sin_acentos(str(oficial.get("materia") or "")).lower()
    epoca = norm.epoca_a_numero(oficial.get("epoca"))
    fecha = norm.parsear_fecha(oficial.get("fecha_publicacion"))
    tipo = norm.normalizar_tipo(oficial.get("tipo"))

    if re.search(r"\b(primera|segunda)\s+sala\b", instancia):
        avisos.append(
            "Criterio de una Sala extinta (reforma DOF 15-IX-2024; la SCJN funciona solo en Pleno desde 1-IX-2025): "
            "verificar si fue superado, reiterado o interrumpido por el Pleno."
        )
    if epoca is not None and epoca <= 9:
        avisos.append(f"Época {epoca}: criterio histórico; verificar vigencia y posibles contradicciones resueltas.")

    if fecha is None:
        avisos.append("Fecha de publicación no disponible: no se pudo aplicar el corte temporal.")
    else:
        for corte in config.get("cortes_temporales", []):
            limite = date.fromisoformat(corte["fecha"])
            materias = corte.get("materias")
            aplica_materia = not materias or any(m in materia for m in materias)
            if fecha < limite and aplica_materia:
                avisos.append(corte["mensaje"])

    if tipo == "aislada":
        avisos.append("Tesis aislada: criterio orientador, no obligatorio.")
    elif tipo != "jurisprudencia":
        avisos.append("Tipo de tesis no identificado: confirmar si es jurisprudencia o tesis aislada.")
    return avisos


def obligatoriedad(oficial: dict) -> str:
    tipo = norm.normalizar_tipo(oficial.get("tipo"))
    if tipo == "jurisprudencia":
        return "jurisprudencia (confirmar alcance obligatorio según el órgano emisor, art. 217 LA)"
    if tipo == "aislada":
        return "tesis aislada (orientadora)"
    return "no determinada"
