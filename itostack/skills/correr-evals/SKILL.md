---
name: correr-evals
description: Ejecuta la suite de evals del harness - autoprueba sin tokens y claude plugin eval con línea base sin plugin - e interpreta los resultados por caso. Úsala para medir una skill, comparar antes y después de un cambio, o preparar la compuerta holdout.
---

# Correr evals

Raíz del plugin: `R=$(cat .itostack/raiz_plugin)`.

1. **Autoprueba** (gratis, determinista): `python3 "$R/evals/autoprueba.py" --caso "<skill>/*"`. Si un caso sale incoherente, arregla la eval antes de culpar a la skill.
2. **Desarrollo con agente real** (consume tokens; corre en tu máquina, como tú):

   ```bash
   claude plugin eval "$R" --tag desarrollo --case "<skill>.*" --scaffold \
     --allow-tools Bash Write Edit --judge-model sonnet --json /tmp/dev-<skill>.json
   ```

   - `--scaffold` ejecuta los `preparar.sh` (escritos por el operador). La primera vez pedirá confiar en el plugin.
   - Por defecto añade un brazo sin plugin: la diferencia mide cuánto aporta la skill.
   - El juez no debe ser el mismo modelo que el agente (`--model` vs `--judge-model`).
3. **Lee las trazas** de los casos con puntaje < 1.0 y de los que se cortaron por tiempo o turnos, aunque el puntaje parezca bueno.
4. **Juez de otra familia (opcional, local)**: `python3 "$R/scripts/revisar_ollama.py" --rol juez --modelo <ollama> --rubrica "$R/evals/rubricas/<rubrica>.md" --archivo <artefacto>`.
5. Reporta por caso: puntaje con plugin, sin plugin, graders fallidos y causa probable. Un 10/10 en desarrollo no certifica producción: es la entrada a la compuerta holdout.
