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
4. **Juez de otra familia (requisito para congelar)**: `python3 "$R/scripts/revisar_codex.py" --rol juez --rubrica "$R/evals/rubricas/<rubrica>.md" --archivo <artefacto> > juez.json`. Exit 0 aprobado, 1 no aprobado, 2 BLOCKED (sin respuesta, nada aplicable o respuesta fuera del contrato: un campo que falta como `fallos_criticos`, un tipo distinto o un valor fuera del esquema como «sí» o `true` en vez de «si»; nada se completa por omisión), 3 configuración rechazada (p. ej. entorno de producción: ahí usa `revisar_ollama.py --modelo <ollama>`, mismo contrato). Guarda el JSON: `compuerta_holdout.py congelar --juez juez.json` lo exige. El veredicto exige un criterio por cada número de la rúbrica (omitir o repetir uno es BLOCKED), evidencia literal entre «» que exista en el artefacto (si no, el «si» cuenta como «no») y registra las huellas del artefacto y de la rúbrica; con `--caso <skill>.<caso>` queda atado al caso (la compuerta exige uno por caso holdout). Cada corrida queda en `.itostack/bitacora/juez.tsv`.
5. Reporta por caso: puntaje con plugin, sin plugin, graders fallidos, veredicto del juez de otra familia y causa probable. Un 10/10 en desarrollo no certifica producción: es la entrada a la compuerta holdout.
