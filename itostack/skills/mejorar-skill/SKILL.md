---
name: mejorar-skill
description: Corrige una skill que falló, se ignoró, se ejecutó a medias o eligió mal, tratándola como defecto de software - reproducción con un caso de eval, corrección en el nivel más fuerte, iteración hasta 10/10 en desarrollo y una sola corrida del holdout. Úsala cuando una skill del harness no se comporte como debe o el operador diga que una skill "no sirve".
---

# Mejorar skill

Raíz del plugin: `R=$(cat .itostack/raiz_plugin)`. Detalle del protocolo: `$R/docs/evals.md`.

1. **Describe el defecto** con evidencia: qué pidió el usuario, qué hizo el agente, qué debió hacer (traza o transcripción).
2. **Caso que falla**: crea un caso de desarrollo con /crear-eval que reproduzca el defecto. Corre la autoprueba para confirmar que la solución de referencia pasa y la rota falla.
3. **Corrige en el nivel más fuerte**: un script que haga la mecánica (/construir-palanca) o una guardia antes que más texto en la skill. Si editas la skill, mantén la descripción con los disparadores reales.
4. **Itera** con /correr-evals sobre los casos de desarrollo de esa skill hasta 1.0 en todos (usa `/loop` si está disponible). No mires ni edites los casos `holdout-*`: el hook lo impide.
5. **Congela y corre el holdout una vez**:

   ```bash
   python3 "$R/evals/compuerta_holdout.py" congelar --skill <skill> --resultados <dev.json>
   python3 "$R/evals/compuerta_holdout.py" holdout --skill <skill>
   ```

6. Si el holdout falla: la candidata queda RECHAZADA. Rediseña instrucción y eval; vuelve al paso 2. Conserva las trazas para auditoría humana.
7. Commit descriptivo en español con la evidencia (resultados de desarrollo y holdout).
