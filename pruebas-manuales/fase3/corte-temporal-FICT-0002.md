# Corte temporal · FICT-0002 (modo fixture)

**Criterio analizado (datos tomados de la evidencia, no de memoria):** jurisprudencia 2a./J. FICT-2/2019 (10a.), registro digital FICT-0002, Segunda Sala, Décima Época, materia Común, publicada 2019-03-15. Rubro: «CRITERIO FICTICIO DE SALA EXTINTA. SIRVE PARA PROBAR LAS ADVERTENCIAS DE CORTE TEMPORAL DEL HARNESS.»

**Paso 1 — verificación.** PASS en `verificar.py tesis` (evidencia `…\.itostack\evidencia\tesis\FICT-0002\20261118T182156Z-2adc\resultado.json`). ⚠ EVIDENCIA DE FIXTURE: no apta para uso procesal.

## Paso 2 — qué hay que confirmar por cada advertencia

| ⚠ Advertencia emitida | Fecha de corte | Qué habría que confirmar | Estado |
|---|---|---|---|
| Criterio de una Sala extinta (reforma DOF 15-IX-2024; la SCJN funciona solo en Pleno desde 1-IX-2025) | — | Si el Pleno reiteró, interrumpió o superó el criterio; si existe contradicción de criterios resuelta con posterioridad | **BLOCKED** |
| Anterior a la reforma judicial (DOF 15-IX-2024) | 2024-09-15 | Si el criterio depende de competencias u órganos que cambiaron. Aquí sí depende: el órgano emisor (Segunda Sala) ya no subsiste | **BLOCKED** |
| Anterior a la Duodécima Época (AG 7/2025 (12a.), 1-IX-2025) | 2025-09-01 | Si el criterio fue reubicado, reiterado o dejado sin efectos al abrirse la nueva Época | **BLOCKED** |
| Anterior a la reforma a la Ley de Amparo (DOF 16-X-2025, vigor 17-X-2025) | 2025-10-17 | Si interpreta artículos reformados; régimen del transitorio 3° para asuntos en trámite. Aplica por ser materia **Común** | **BLOCKED** |

Las cuatro advertencias se dispararon correctamente: 2019-03-15 es anterior a las tres fechas de corte, y la materia «Común» activa la regla de amparo. Comprobación cruzada: FICT-0003 (2023-06-02, materia **Penal**) recibió solo tres advertencias, sin la de amparo, porque esa regla está acotada con `"materias": ["comun", "amparo"]` en `nucleo/config.py:59-63`. El filtro por materia funciona.

## Paso 3 — búsqueda de criterios posteriores: BLOCKED

No se realizó y **no puede realizarse con este harness**:

1. `verificar.py` solo acepta `tesis`, `url`, `app` y `lote`: **no hay subcomando de búsqueda** en el SJF. Solo sabe consultar un registro que ya se conoce.
2. El guardia de Bash bloquea `curl` contra `sjf2.scjn.gob.mx`, y con razón: no dejaría captura forense.
3. En modo fixture, `basico.json` contiene siete registros y ninguno posterior que pudiera reiterar o superar a FICT-0002.

## Paso 4 — conclusión por criterio

**⚠ FICT-0002: sin confirmación de vigencia.** No es «vigente» ni «superado»: es un criterio de un órgano extinto, anterior a las tres reformas de corte, cuya suerte posterior no fue confirmada con evidencia. Conforme a la regla de la skill —«sin confirmación verificada, la conclusión es ⚠, nunca vigente»— no debe usarse como apoyo sin que el operador localice y verifique un criterio posterior del Pleno.

## Hallazgos de la prueba

- **B-01 · Brecha estructural (no es un fallo de ejecución).** El paso 3 de la skill ordena «busca criterios posteriores en el SJF y verifica cada hallazgo», pero el harness no ofrece ninguna herramienta de búsqueda y el guardia de Bash cierra la vía manual. La skill pide algo que su propia caja de herramientas no puede hacer, así que todo análisis de corte temporal termina estructuralmente en ⚠. Propuesta: o un subcomando `verificar.py buscar --clave/--rubro` que consulte el buscador oficial con captura (nivel 1 · diseño), o decir en la prosa de la skill que la búsqueda la aporta el operador (nivel 4). Hoy la prosa promete una capacidad que no existe.
- **O-06 · Baja.** La regla de la skill dice que «las fechas de corte viven en `.itostack/config.json` (`cortes_temporales`)». En un proyecto recién inicializado **esa clave no existe** en `config.json`: las cuatro fechas vienen de los valores por omisión de `nucleo/config.py:47-65`, y `config.json` solo las sobrescribe si el operador las agrega a mano. Quien siga la prosa al pie de la letra abrirá `config.json` y no encontrará nada que ajustar. Propuesta (nivel 4 · prosa, o nivel 1 escribiendo la clave al inicializar).
