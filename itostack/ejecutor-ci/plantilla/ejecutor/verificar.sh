#!/usr/bin/env bash
# Verificación previa (contrato CR-3, E4; CR-2, X8 y X9). Si algo falla, no se evalúa y no se consume el intento.
set -euo pipefail
: "${HUELLA:?falta la huella}" "${SKILL:?falta la skill}"
cd "$GITHUB_WORKSPACE"
# Herramientas en las versiones verificadas y copia fijada del orquestador (versiones.json); cualquier diferencia → BLOCKED.
python3 ejecutor/ejecutor/comprobar_versiones.py ejecutor/ejecutor/versiones.json
# La reserva de este repositorio: cada caso aprobado por una persona distinta de su autor y declarado sintético.
python3 ejecutor/ejecutor/validar_reserva.py ejecutor/reserva "$SKILL"
# La huella de la candidata obtenida debe ser la congelada.
calculada=$(python3 ejecutor/orquestador/evals/compuerta_holdout.py huella --skill "$SKILL" --plugin candidata/itostack)
[ "$calculada" = "$HUELLA" ] || { echo "la candidata no tiene la huella congelada"; exit 1; }
# Prueba de humo: una guardia PreToolUse de la candidata, con su comando exacto de hooks.json, deniega una acción
# conocida. Sin guardias funcionando no se evalúa.
python3 ejecutor/orquestador/evals/humo_guardias.py candidata/itostack
echo "verificación previa: PASS"
