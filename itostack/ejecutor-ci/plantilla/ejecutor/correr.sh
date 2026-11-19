#!/usr/bin/env bash
# Corre el holdout con el orquestador FIJADO de este repositorio (ejecutor/orquestador), nunca con el de la candidata:
# una candidata no puede traer su propio juez. Requiere CR-3.2b (CLI del orquestador con evaluación y juez reales).
set -euo pipefail
: "${HUELLA:?falta la huella}" "${SKILL:?falta la skill}"
cd "$GITHUB_WORKSPACE"
mkdir -p salida
# Credenciales: solo en este paso y solo como archivos con permisos 600 dentro del HOME efímero del ejecutor.
umask 077
if [ -n "${CODEX_AUTH_JSON:-}" ]; then mkdir -p "$HOME/.codex" && printf '%s' "$CODEX_AUTH_JSON" > "$HOME/.codex/auth.json"; fi
python3 ejecutor/orquestador/evals/orquestador.py ejecutar \
  --skill "$SKILL" --candidata candidata/itostack --huella "$HUELLA" \
  --reserva ejecutor/reserva --almacen salida/almacen --salida salida/manifiesto.json
# El orquestador invoca `claude plugin eval` con --no-publish (V1) y escribe todo dentro de salida/almacen; ninguna
# traza ni caso sale de este ejecutor: el artefacto publicado es solo salida/manifiesto.json y su firma.
