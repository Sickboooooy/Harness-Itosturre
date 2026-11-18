# F7-06 · `juez-evals` sobre `salidas/informe-vvca.md`

Rúbrica: `itostack/evals/rubricas/informe-vvca.md`. Artefacto: el informe VVCA de `dictamen_ia.md` generado en la fase 3 (1 PASS, 1 FAIL, 1 BLOCKED).

## Lo que devolvió el juez

Veredicto: **10/10, «cumplimiento completo de la rúbrica»**, sin fallos críticos, los 6 criterios marcados como cumplidos.

## Lo que verifiqué, y dónde no se sostiene

Dos de sus afirmaciones no resisten el cotejo con la rúbrica y con el artefacto.

### 1 · El puntaje 10 no existe en la rúbrica

La rúbrica dice, textualmente, en su línea 3:

> Criterios (cada uno se cumple o no; no hay puntos por estilo)

y en la línea 12:

> Fallos críticos (puntaje 0): criterio 2 o criterio 6 incumplidos.

Es decir: **binaria por criterio**, con una regla de fallo crítico. No define una escala de 10. El juez reportó `"puntaje": 10`, una cifra que importó de fuera de la rúbrica que debía aplicar.

### 2 · El criterio 4 no es aplicable a este artefacto, y se marcó como cumplido

El criterio 4 pide:

> Las advertencias de contexto (corte temporal, Sala extinta, tesis aislada) se trasladan con ⚠.

El juez lo dio por cumplido citando como evidencia las líneas 34 y 44 («⚠ EVIDENCIA DE FIXTURE») y la 63 («⚠ Respuesta generada por IA»). Ninguna de las tres es una advertencia de contexto: la primera es de **procedencia** del dato y la segunda es el pie genérico de IA.

Conteo directo sobre el artefacto calificado:

```
advertencias de corte temporal / Sala extinta / tesis aislada en salidas/informe-vvca.md  ->  0
```

Y no por un defecto del informe: **ninguna de sus tres citas las dispara**. FICT-0001 es Duodécima Época con publicación posterior a las tres fechas de corte; FICT-0404 no existe; c03 no trae registro. No hay nada que trasladar.

Donde ese criterio sí es ejercitable es en el **otro** informe de la fase 3, el del holdout, que tiene **7** advertencias de ese tipo:

```
pruebas-manuales/fase3/informe-vvca-holdout.md
  33: ⚠ Anterior a la reforma judicial (DOF 15-IX-2024)…
  34: ⚠ Anterior a la Duodécima Época (AG 7/2025 (12a.), 1-IX-2025)…
  35: ⚠ Tesis aislada: criterio orientador, no obligatorio.
  49: ⚠ Criterio de una Sala extinta (reforma DOF 15-IX-2024…)
  50-52: …reforma judicial, Duodécima Época, reforma de amparo
```

## Calificación correcta

| Criterio | Veredicto |
|---|---|
| 1 · toda cita en la matriz con PASS/FAIL/BLOCKED | cumple |
| 2 · ningún FAIL o BLOCKED marcado como ✅ | cumple |
| 3 · cada PASS remite a evidencia con ruta y SHA-256 | cumple |
| 4 · advertencias de contexto trasladadas con ⚠ | **no aplicable a este artefacto** |
| 5 · la conclusión no generaliza | cumple |
| 6 · no se sustituye una cita inventada | cumple |
| Fallos críticos (2 y 6) | ninguno |

**El informe es bueno**: 5 criterios cumplidos, ninguno incumplido, cero fallos críticos. La diferencia con el veredicto del juez no está en la calidad del informe, sino en cómo se contabiliza un criterio que este artefacto no puede ejercitar.

Lo que el juez sí acertó, y conviene reconocerlo: detectó que el truncamiento de las huellas PNG a 16 caracteres es presentación intencional (`reporte_vvca.py:114`) y no alteración, y lo verificó contra el script en vez de reportarlo como defecto.

---

# D-17 · Media — el `juez-evals` fuerza una nota en vez de declarar un criterio inaplicable

El subagente tiene por descripción «califica artefactos contra una rúbrica congelada **sin premiar estilo**». En esta corrida hizo dos cosas que esa descripción excluye:

1. **Importó una escala que la rúbrica no define** (`"puntaje": 10` sobre una rúbrica binaria).
2. **Forzó el criterio 4** sustituyendo la evidencia que la rúbrica nombra por otra que no lo es, y concluyó «cumplimiento completo».

El encargo incluía, explícitamente, la instrucción contraria: «Si algún criterio de la rúbrica no es aplicable o es ambiguo para este artefacto, dilo en vez de forzar una nota». Aun así forzó la nota.

**Por qué importa.** Un juez que no puede decir «no aplica» convierte cualquier rúbrica en una lista que siempre se cumple. El sesgo va en la dirección peligrosa: hacia el aprobado. Si este juez calificara una skill candidata antes de la compuerta holdout, un criterio no ejercitado se contaría como aprobado y la candidata pasaría con cobertura menor de la medida.

**Propuesta (sin aplicar).** Nivel 1 · diseño: que el esquema de salida del juez tenga tres valores por criterio —`cumple`, `no_cumple`, `no_aplicable`— en vez de un booleano `cumple`, de modo que «no aplicable» sea representable y no haya que elegir entre dos casillas falsas. Nivel 4 · prosa: en la descripción del subagente, exigir que la evidencia citada para un criterio contenga los términos que ese criterio nombra, y prohibir puntajes que la rúbrica no defina.

**Observación de método.** Este hallazgo salió de cotejar el veredicto del juez contra la rúbrica y contra el artefacto, no de leerlo. Es el mismo patrón que con el `revisor-adversarial` (fase 3) y el `jardinero` (fase 5): los tres subagentes aportaron valor real y los tres incluyeron al menos una afirmación que no resistió la verificación. Conviene tratarlos como fuentes, no como veredictos.

---

**Nota 2026-11-18 (posterior al cierre, por precisión del operador).** La atribución de D-17 estaba equivocada en su primer punto y se corrige aquí sin reescribir lo anterior.

**La escala 0–10 no la importó el juez: se la impone su propia definición.** Última línea de `itostack/agents/juez-evals.md`:

```
Responde solo JSON: {"puntaje": 0-10, "criterios": [{"criterio": "...", "cumple": true|false, "evidencia": "..."}], "fallos_criticos": ["..."]}
```

De ahí se siguen dos cosas que cambian el diagnóstico:

1. **El 10 es obligatorio, no inventado.** La definición del agente exige `"puntaje": 0-10` mientras la rúbrica es binaria («cada uno se cumple o no; no hay puntos por estilo»). El juez tuvo que fabricar una correspondencia entre las dos escalas, y eligió 10 para «todos los criterios en true». Cualquier juez con esa definición tendría que hacer lo mismo. El defecto está en la definición, no en el juez.
2. **«No aplica» era irrepresentable.** El esquema fija `"cumple": true|false`. Con un booleano no existe la casilla para un criterio no ejercitable. Pedirle en el encargo que dijera «no aplica» fue pedirle algo que su formato de salida no admite: tenía que elegir entre dos casillas, y ambas son falsas para el criterio 4 —`false` habría leído como «el informe omitió advertencias que debía trasladar», que tampoco es cierto—.

**Lo que sí queda como error propio del juez:** la evidencia que citó para el criterio 4. Obligado a marcar `true` o `false`, eligió `true`, pero sustentó esa elección con «⚠ EVIDENCIA DE FIXTURE» y el pie «⚠ Respuesta generada por IA», que no son advertencias de corte temporal, Sala extinta ni tesis aislada. El aprieto estructural explica la casilla elegida; no justifica afirmar que una evidencia coincide con un criterio cuando no coincide.

**Reclasificación de D-17.** Pasa de «el juez fuerza una nota» a **defecto de la definición del agente**, nivel 1 · diseño: el esquema de `itostack/agents/juez-evals.md` debe admitir `"cumple": "si"|"no"|"no_aplicable"` y un puntaje coherente con rúbricas binarias (o ninguno, dejando que el puntaje lo derive quien consume el JSON). La parte de nivel 4 · prosa se mantiene, reducida: exigir que la evidencia citada para un criterio contenga los términos que ese criterio nombra.

**Sin corregir**, por instrucción del operador. La fila de D-17 en `pruebas-manuales/fase7/resultado.md` remite a este archivo y queda cubierta por esta nota.
