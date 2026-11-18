# F7-05 · `/itostack:mejorar-skill` en seco

Ejercicio solicitado: explicar qué haría con `verificar-cita/fail-epoca-discrepante` **si fallara**. No se ejecutó ninguna corrección. El caso hoy **no falla**: autoprueba 1.00 / 0.50.

## El supuesto

Supongamos que `claude plugin eval` sobre el conjunto de desarrollo de `verificar-cita` devuelve, en 3 corridas, un promedio de **0.63** para este caso, con el grader `senala-la-epoca` reprobado en 2 de 3 y `veredicto-fail` aprobado siempre.

Esa firma —el veredicto correcto pero el reporte impreciso— dice algo concreto: el agente **sí corre el verificador y sí lee FAIL**, pero al redactar se queda en «la cita presenta discrepancias» sin nombrar cuál. No es un fallo de la herramienta, es que la skill no obliga a trasladar el cotejo que falló.

## Paso 1 · Describir el defecto con evidencia

Qué pidió el usuario: verificar una cita con rubro y clave correctos y época incorrecta.
Qué hizo el agente: veredicto FAIL correcto, reporte genérico.
Qué debió hacer: nombrar el cotejo discrepante, que es el dato accionable — con el rubro y la clave buenas, el abogado solo necesita corregir la época.
Evidencia: la traza del caso y el `last_message` de las corridas que reprobaron.

## Paso 2 · El caso que falla ya existe

`fail-epoca-discrepante` **es** ese caso. El grader `senala-la-epoca` (peso 2) es exactamente el que detecta el defecto, y la solución rota confirma que discrimina: 0.50 contra 1.00.

Si el defecto hubiera aparecido sin tener el caso, aquí tocaría crearlo con `/crear-eval` antes de tocar nada. Es el orden que importa: **primero la prueba que falla**, igual que en `/tdd`.

## Paso 3 · Corregir en el nivel más fuerte

El impulso natural es agregar una línea a `SKILL.md` («traslada siempre el cotejo discrepante»). La skill dice explícitamente que eso es lo último. Orden que seguiría:

| Nivel | Opción | ¿Aplicable aquí? |
|---|---|---|
| 1 · diseño | Que la salida del verificador haga imposible omitirlo | **Sí, y es el que elegiría.** `verificar.py` ya imprime la línea `tesis FICT-0001 — epoca discrepante (época 11 citada vs 12 oficial)`. El problema no es que falte el dato, es que el agente lo resume. Reforzaría el **formato de reporte** de la skill (sección 4 de `verificar-cita/SKILL.md`) agregando un campo obligatorio `Cotejo que falló: <campo> — citado «X» / oficial «Y»`, tomado literal del verificador. Un campo con nombre es más difícil de omitir que una instrucción en prosa. |
| 2 · guardia | Un hook que bloquee un reporte de cita sin el cotejo | Desproporcionado: afectaría a todos los reportes, incluidos los PASS donde no hay cotejo fallido. Lo descartaría. |
| 3 · verificación | El grader `senala-la-epoca` | **Ya está.** Es lo que detecta el defecto; no es la corrección. |
| 4 · prosa | Una línea más en la skill | Solo si el formato del paso 1 resultara insuficiente tras medirlo. |

Nótese el matiz: la corrección de nivel 1 aquí **no** es código, es la estructura del reporte que la skill impone. Sigue siendo nivel 1 porque cambia la forma del artefacto, no la exhortación sobre él.

## Paso 4 · Iterar hasta 1.0 en desarrollo

`/correr-evals` sobre los **6 casos de desarrollo** de `verificar-cita` (`pass-exacto`, `pass-advertencia-sala`, `fail-inexistente`, `fail-rubro-alterado`, `blocked-portal-caido`, `blocked-sin-registro`) más el nuevo, hasta que todos den 1.0.

Dos cuidados:

- **No mirar ni editar los `holdout-*`.** El hook lo impide y se comprobó en vivo en F5-15: el intento de editar `holdout-fail-clave/case.yaml` fue denegado.
- **Vigilar la regresión en los PASS.** Un campo obligatorio «cotejo que falló» puede inducir al agente a inventarse uno cuando no hay ninguno. `pass-exacto` y `pass-advertencia-sala` son los que lo detectarían.

## Paso 5 · Congelar y correr el holdout una vez

```
python evals/compuerta_holdout.py congelar --skill verificar-cita --resultados <dev.json>
python evals/compuerta_holdout.py holdout --skill verificar-cita
```

Estado comprobado hoy: `compuerta_holdout.py estado` no lista ninguna candidata congelada, y la huella actual de `verificar-cita` es `50e62b1c947a4939…`.

**Qué entra en esa huella** (`compuerta_holdout.py:36-48`): el contenido de `skills/verificar-cita/`, `scripts/`, `hooks/`, `guardias/` y `evals/verificar-cita/`, excluyendo todo lo que contenga `holdout-` en su ruta. Dos consecuencias que condicionan el plan:

1. **La huella ya cambió.** Al crear `fail-epoca-discrepante` dentro de `evals/verificar-cita/`, la huella de hoy no es la de ayer. Es el comportamiento correcto —el conjunto de desarrollo forma parte de la candidata—, pero significa que agregar un caso invalida cualquier congelado previo.
2. **Un solo intento por huella.** Si el holdout falla, la candidata queda RECHAZADA (`:144`, `"ACEPTADA" if minimo == 1.0 and not faltantes else "RECHAZADA"`) y esa huella no puede reintentarse. Por eso el paso 4 exige 1.0 **antes** de congelar: el holdout no es una iteración más, es el examen.

## Paso 6 · Si el holdout falla

La candidata queda rechazada y habría que rediseñar la instrucción y quizá la eval, volviendo al paso 2 — no «reintentar a ver si sale». Las trazas se conservan para auditoría humana.

## Paso 7 · Commit

Descriptivo en español, con los resultados de desarrollo y de holdout como evidencia. **En esta campaña no aplica**: la regla 5 del plan prohíbe commits.

## Por qué este ejercicio en seco vale algo

Deja fijado, antes de que haya presión por arreglar, que la corrección iría al **formato del reporte** y no a una línea de prosa, y que el holdout se gasta una sola vez. Las dos son decisiones fáciles de tomar mal cuando una eval está en rojo.
