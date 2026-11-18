# Fase 3 · Pilar 1 jurídico (modo fixture) — resultado

Proyecto en perfil `juridico`, modo `fixture`, fixture `itostack/evals/fixtures/sjf/basico.json`. `PY` = `python` (`C:\Python314\python.exe`). Evidencia cruda: `evidencia.txt`. Lista de tareas del modo: `lista-de-tareas.md`.

## E0 · `modo-itosturre`

| ID | Función | Esperado | Observado | Estado |
|---|---|---|---|---|
| F3-00 | El modo copia el playbook palabra por palabra, con `skip:` donde aplique | lista de tareas con los pasos literales | Playbook elegido: `orquestacion-multietapa.md` (el más abarcador, regla 3 del contrato). Sus 6 pasos copiados literalmente en `lista-de-tareas.md`; el paso 3 (aislar escritores con `git worktree`) queda en `skip:` razonado y el 5 en `skip parcial:` | OK con salvedad (D-06) |

**D-06 · Media.** El contrato del modo exige copiar los pasos «en la lista de tareas», pero **esta sesión no tiene la herramienta TodoWrite** (comprobado: ninguna herramienta diferida coincide con todo/task/list). El paso 4 del contrato depende de una herramienta que puede no estar presente, y entonces no hay forma de cumplirlo como está escrito. Lo sustituí por un archivo y lo dejé asentado como decisión. Propuesta (nivel 4 · prosa): que el contrato diga «la lista de tareas, o un archivo de trabajo si la herramienta no está disponible»; o (nivel 1 · diseño) que la skill no asuma herramientas del anfitrión.

## E1 · Los 8 casos de `verificar-cita`

| ID | Caso | Esperado | Observado | Estado |
|---|---|---|---|---|
| F3-01 | FICT-0001 exacto | PASS | `PASS · ✅ VERIFICADO`, los 5 cotejos coinciden, exit 0 | OK |
| F3-02 | FICT-0001 con una palabra cambiada (PORTAL→SITIO) | FAIL | `FAIL`, «rubro discrepante (primera diferencia — citado: «sitio» / oficial: «portal»)», exit 1 | OK |
| F3-03 | FICT-0404 | FAIL inexistente | `FAIL`, «registro inexistente en el SJF (respuesta oficial: no encontrado)», exit 1 | OK |
| F3-04 | FICT-0503 | BLOCKED portal caído | `BLOCKED`, «portal no disponible: net::ERR_TIMED_OUT», exit 2 | OK |
| F3-05 | FICT-0777 | BLOCKED estructura | `BLOCKED`, «estructura de respuesta no reconocida: calibrar la extracción antes de concluir», exit 2 | OK |
| F3-06 | Cita sin registro | BLOCKED sin inventar registro | `BLOCKED`, «la cita no trae registro digital». No se inventó ningún registro; se dejó constancia en el almacén | OK |
| F3-07 | FICT-0002 | PASS con ⚠ Sala extinta y cortes temporales | `PASS` + 4 advertencias: Sala extinta, reforma judicial, Duodécima Época y reforma de amparo | OK |
| F3-08 | FICT-0003 en minúsculas y con comillas tipográficas | PASS tipográfico con ⚠ tesis aislada | `PASS`, «cotejo rubro: tipografica coincide salvo variaciones tipográficas», + ⚠ tesis aislada | OK |

Comprobación cruzada no pedida pero útil: FICT-0003 (materia Penal) **no** recibe la advertencia de la reforma de amparo y FICT-0002 (Común) sí. El filtro `"materias": ["comun","amparo"]` de `nucleo/config.py:59-63` funciona.

## E2 · Capturas PNG

| ID | Función | Esperado | Observado | Estado |
|---|---|---|---|---|
| F3-09 | Captura de un PASS | franja FIXTURE visible | `FICT-0001/…/detalle.png`: franja roja «FIXTURE — DATOS FICTICIOS DE PRUEBA, NO SON CRITERIOS REALES» arriba; debajo, título, registro, instancia, época, clave y tipo, coherentes con el veredicto | OK |
| F3-10 | Captura de un BLOCKED | franja FIXTURE visible | `FICT-0777/…/detalle.png`: misma franja; debajo una sola línea «Contenido sin etiquetas reconocibles», coherente con «estructura no reconocida» | OK |

**O-05 · Baja.** La franja solo se inyecta en respuestas HTML (`verificador_fuente.ts:41,57,62,69`). La segunda captura de cada verificación, `api.png`, es el visor JSON del navegador y **no lleva franja**: su única marca es la clave `"_fixture": "DATOS FICTICIOS"` del propio contenido. Los fixtures de error no la traen (FICT-0404 = `{"mensaje":"No se encontró"}`, FICT-0500 = `{"error":"Error interno del servidor"}`), así que esas `api.png` quedan sin ninguna marca de ficción. Como el sentido de la franja es que un PNG extraído del expediente no pueda confundirse con evidencia real, convendría inyectarla también en la captura de la API (nivel 1 · diseño).

## E3 · `verificar.py url`

| ID | Función | Esperado | Observado | Estado |
|---|---|---|---|---|
| F3-11 | DOF ficticio con `--contiene "DECRETO FICTICIO DE PRUEBA"` | PASS | `PASS`, «contenido confirmado en la fuente oficial», captura `fuente.png`, exit 0 | OK |
| F3-12 | Mismo URL con un texto ausente | FAIL | `FAIL`, «texto esperado ausente en la fuente oficial», exit 1 | OK |

## E4 · `validar-documento`

| ID | Función | Esperado | Observado | Estado |
|---|---|---|---|---|
| F3-13 | `dictamen_ia.md` | 1 PASS, 1 FAIL, 1 BLOCKED | `VEREDICTO LOTE: 1 PASS · 1 FAIL · 1 BLOCKED`. La extracción dejó `registro: null` en la cita sin registro, sin inventarlo | OK |
| F3-14 | `dictamen_ia_holdout.md` | FAIL por rubro truncado | `[c01] FAIL — rubro discrepante (citado: «rubro» / oficial: «rubro, ni siquiera parcial»)`; `[c02] PASS` | OK |
| F3-15 | Auditoría con el subagente `auditor-citas` | informe auditado | **APROBADO** los dos informes, sin discrepancias | OK |

Sobre F3-14: el rubro extraído coincidía letra por letra con el documento, de modo que la truncadura es **del documento**, no de la extracción. Por la regla 2 de la skill no se corrigió; corregirlo habría fabricado un PASS falso.

La auditoría fue independiente: el subagente recalculó los SHA-256 con `sha256sum`, cotejó los 5 registros del almacén (ids 11–15) contra ambos informes, confirmó que `vigente` da VIGENTE solo para los dos PASS, y verificó que las líneas citadas corresponden a la ubicación real en los documentos fuente. Comprobé por mi cuenta su observación sobre las huellas y es correcta: `problemas_de_integridad` (`nucleo/evidencia.py:143-158`) usa **dos regímenes** — bytes crudos (`sha256_archivo`) para las capturas PNG, y huella canónica sobre el JSON parseado (`sha256_resultado`) para `resultado.json`. No es una discrepancia: es diseño, y significa que una alteración de bytes en un PNG sí se detecta.

## E5 · `redactar-con-citas`

| ID | Función | Esperado | Observado | Estado |
|---|---|---|---|---|
| F3-16 | Párrafo con FICT-0001 y FICT-0002 | `salidas/parrafo.md` con `[^ev1]` y `[^ev2]` | `ENSAMBLADO: PASS — 2 cita(s) con evidencia · 0 pendiente(s)`. Las dos notas traen fecha, ruta, SHA-256 y las ⚠ heredadas (incluidas las 4 de corte temporal de FICT-0002) | OK |
| F3-17 | Borrador con `[[CITA:FICT-0404]]` | `ENSAMBLADO: BLOCKED` y ningún archivo escrito | `ENSAMBLADO: BLOCKED — no se escribió ningún archivo.`, exit 2. Comprobado: `salidas/parrafo-bloqueado.md` no existe | OK |

## E6 · `corte-temporal` sobre FICT-0002

| ID | Función | Esperado | Observado | Estado |
|---|---|---|---|---|
| F3-18 | Análisis de corte temporal | advertencias trasladadas y conclusión prudente | Las 4 advertencias se dispararon correctamente. Conclusión: **⚠ sin confirmación de vigencia**, conforme a la regla «sin confirmación verificada, nunca vigente». Detalle en `corte-temporal-FICT-0002.md` | OK con brecha (B-01) |

**B-01 · Brecha estructural.** El paso 3 de la skill ordena «busca criterios posteriores en el SJF y verifica cada hallazgo», pero `verificar.py` solo acepta `{tesis,url,app,lote}`: **no hay búsqueda**, y el guardia de Bash cierra la vía manual con `curl` (con razón: no dejaría captura). Todo análisis de corte temporal termina, por construcción, en ⚠. No es un fallo de ejecución, es una capacidad prometida por la prosa que la caja de herramientas no tiene.

**O-06 · Baja.** La regla de la skill dice que las fechas de corte «viven en `.itostack/config.json` (`cortes_temporales`)». En un proyecto recién inicializado esa clave **no existe**: los valores vienen de `nucleo/config.py:47-65` y `config.json` solo los sobrescribe si el operador los agrega.

## E7 · `revisor-adversarial` sobre `salidas/parrafo.md`

| ID | Función | Esperado | Observado | Estado |
|---|---|---|---|---|
| F3-21 | Subagente adversarial sobre el párrafo | hallazgos por gravedad, sin editar | 20 hallazgos (8 altos, 9 medios, 3 bajos) y veredicto **RECHAZAR** el documento / **CORREGIR** el generador. No editó nada | OK |

El subagente excedió el encargo —se le pidió revisar el párrafo y auditó también el generador—, lo que resultó valioso. **No tomé sus conclusiones al pie de la letra: verifiqué en el código las cuatro afirmaciones estructurales.** Las cuatro son ciertas; una la matizo.

### Crítica legítima a mi propia redacción (la asumo)

El párrafo atribuye a FICT-0002 un «deber de constatación [que] se extiende a la vigencia» que su rubro no enuncia: el rubro dice solo «CRITERIO FICTICIO DE SALA EXTINTA. SIRVE PARA PROBAR LAS ADVERTENCIAS DE CORTE TEMPORAL DEL HARNESS.». Igual con FICT-0001: la glosa «condiciona la invocación…» se derivó del rubro, no del texto. Son defectos míos de redacción, y son exactamente la demostración de D-07: **el harness me dejó escribirlos con veredicto PASS en verde**, porque nada en la cadena coteja la glosa contra el criterio.

### Corroboración independiente de D-04

Sin que se lo pidiera ni conociera mi sonda, el revisor llegó al mismo punto por lectura de código: «`citas.py:19,44` — `marcada` se calcula **por línea**, así que una ⚠ en cualquier parte de la línea desactiva el control de citas a mano para todas las citas de esa línea». Dos rutas independientes al mismo defecto.

### Verificación de sus afirmaciones estructurales

| Afirmación | ¿Cierta? | Comprobación |
|---|---|---|
| `formatear()` nunca emite el campo `texto` | **Sí** | `ensamblar_documento.py:37-49`: las cuatro formas (completa, rubro, clave, corta) componen tipo, clave, rubro, instancia, época y registro. `texto` no aparece. Y `verificar.py tesis` no tiene bandera `--texto`: no hay forma de cotejarlo |
| `obligatoriedad` se calcula y no llega al documento | **Sí, con matiz** | Se calcula en `verificar.py:156` y **sí se persiste** en `resultado.json` (comprobado: «jurisprudencia (confirmar alcance obligatorio según el órgano emisor, art. 217 LA)»). Lo que no existe es la **columna en el esquema** (`nucleo/evidencia.py:17-34`), y el ensamblador lee de la base, no del JSON. No «se tira»: sobrevive en la evidencia y no alcanza el entregable. Corrijo ahí al revisor |
| La nota afirma «Verificado en el portal oficial» sea cual sea el modo | **Sí** | `ensamblar_documento.py:68`: la cadena es literal y el único matiz es `[{modo_fuente}]`, sin traducir |
| `datos_oficiales` de FICT-0002 carece de `texto` | **Sí** | Comprobado en el `resultado.json`: FICT-0001 lo trae, FICT-0002 no. Es propiedad del fixture, no del código; el defecto de código es el de la primera fila |

### Fortalezas que el revisor confirmó, y yo también

Falla cerrado por omisión (`ensamblar_documento.py:107-113`: sin `--permitir-pendientes` no escribe y devuelve 2); el fallo se imprime **en el cuerpo** del texto, no se oculta (`:62` sustituye la cita por `⚠ CITA NO VERIFICADA`); la transcripción del rubro no la escribe el modelo; `vigente()` revalida integridad antes de reutilizar; y el almacén es **append-only de verdad** — comprobé los dos triggers `verificaciones_sin_actualizar` y `verificaciones_sin_borrar`, que abortan UPDATE y DELETE.

### Hallazgos suyos que no elevo a defecto

Varios son cuestiones de redacción forense legítimas pero propias del borrador, no del harness (muletillas, «inadmisible» usado con imprecisión, falta del tercer tramo del silogismo). Otro —que las banderas VVCA queden en `true` sobre datos de fixture— es discutible: el veredicto cotejó lo que dijo que cotejó, y la advertencia de fixture está presente en las cinco salidas. Lo dejo anotado, no como defecto.

---

# Defectos adicionales surgidos de E7 (verificados por mí en el código)

## D-07 · Alta — el harness certifica la transcripción del rubro, nunca la fidelidad del uso

`verificar.py tesis` acepta `--rubro`, `--clave`, `--epoca`, `--instancia`, `--tipo` y `--fecha`. **No acepta el texto de la tesis**, y `formatear()` (`ensamblar_documento.py:37-49`) nunca lo emite en ninguna de sus cuatro formas. Consecuencia: un documento puede obtener `ENSAMBLADO: PASS` con la clave y el rubro copiados impecablemente y una glosa que el criterio no sostiene. Es estructural: se reproduciría idéntico con tesis reales. Propuesta (nivel 1 · diseño): que `formatear()` pueda emitir el pasaje operativo y que exista un cotejo opcional `--texto-contiene` análogo al `--contiene` de `verificar.py url`, que ya existe y funciona.

## D-08 · Media — `obligatoriedad` se calcula, se guarda en la evidencia y no llega al entregable

`verificar.py:156` produce «jurisprudencia (confirmar alcance obligatorio según el órgano emisor, art. 217 LA)» y queda en `resultado.json`, pero el esquema (`nucleo/evidencia.py:17-34`) no tiene esa columna, de modo que el ensamblador —que lee de la base— no puede propagarla. Se agrava con `contexto.py:41-44`, que solo advierte cuando el tipo es «aislada»: una jurisprudencia de tribunal colegiado aparece en el documento como «Jurisprudencia» a secas, sin cautela sobre su alcance. Propuesta (nivel 1 · diseño): agregar la columna y emitir la cautela en el cuerpo.

## D-09 · Media — la nota al pie afirma «Verificado en el portal oficial» también en modo fixture

`ensamblar_documento.py:68` imprime la afirmación primero y el desmentido después, entre corchetes y sin traducir: «Verificado en el portal oficial el 2026-11-18T18:24:52+00:00 **[fixture]**». Propuesta (nivel 1 · diseño): que en fixture la nota empiece por «NO VERIFICADO — DATOS SINTÉTICOS», y traducir la etiqueta.

## E8 · Almacén de evidencia

| ID | Función | Esperado | Observado | Estado |
|---|---|---|---|---|
| F3-19 | `evidencia_db.py recientes` | listado de verificaciones | 15 filas, coherentes una a una con los comandos ejecutados | OK |
| F3-20 | `evidencia_db.py auditar` | `Integridad: OK` | `Integridad: OK`, exit 0 | OK |

---

# Defectos encontrados en esta fase

## D-04 · **Crítica** — una palabra dentro del rubro desactiva el control de evidencia, en el ensamblador **y en el guardia de escritura**

**Qué pasa.** Tanto `ensamblar_documento.py:77-82` como **`hooks/guardia_escritura.py:55-68`** eximen del control de «evidencia vigente» a cualquier cita escrita a mano cuya **línea** haga match con `RE_MARCA_NO_VERIFICADA` (`nucleo/citas.py:19`), que incluye las palabras sueltas `NO VERIFICAD`, `NO VERIFICABLE`, `BLOQUEAD` e `INEXISTENTE`, sin distinción de mayúsculas y en cualquier posición de la línea, **incluido el interior de un rubro entrecomillado**. Los dos comparten el mismo detector, de modo que el fallo no tiene segunda barrera: el guardia PreToolUse es justamente la última defensa de `salidas/`, `escritos/` y `dictamenes/`.

**Reproducción en vivo del bypass del guardia (herramienta Write, no Bash):**

| Sonda | Archivo | Línea | Resultado del hook |
|---|---|---|---|
| A | `salidas/sonda-guardia-a.md` | `…«… ESTE RUBRO NO APARECE EN NINGÚN PORTAL.», registro digital FICT-0404.` | **DENEGADO**: «citas sin evidencia vigente en un entregable jurídico: línea 3: registro «FICT-0404»» ✔ |
| B | `salidas/sonda-guardia-b.md` | `…«… ESTE RUBRO NO APARECE EN NINGÚN PORTAL Y DEBE DETECTARSE COMO INEXISTENTE.», registro digital FICT-0404.` | **PERMITIDO**, archivo escrito en `salidas/` ✘ |

Tres palabras agregadas dentro del rubro citado bastan para que un entregable jurídico con un registro inexistente se escriba sin objeción.

**Reproducción determinista.** Dos borradores idénticos salvo por tres palabras dentro del rubro citado, ambos con `registro digital FICT-0404` escrito a mano (último veredicto en el almacén: FAIL, luego sin evidencia vigente):

| Sonda | Línea | Resultado |
|---|---|---|
| A | `…«CRITERIO FICTICIO INVENTADO. ESTE RUBRO NO APARECE EN NINGÚN PORTAL.», registro digital FICT-0404.` | `ENSAMBLADO: BLOCKED — no se escribió ningún archivo.` (exit 2) ✔ correcto |
| B | `…«CRITERIO FICTICIO INVENTADO. ESTE RUBRO NO APARECE EN NINGÚN PORTAL Y DEBE DETECTARSE COMO INEXISTENTE.», registro digital FICT-0404.` | `ENSAMBLADO: PASS — 0 cita(s) con evidencia · 0 pendiente(s)` (exit 0), **archivo escrito** ✘ |

En `salidas/sonda-b.md` la cita inexistente aparece como prosa corriente, sin ⚠ ni ❌ junto a ella; solo lleva el pie genérico de IA.

**Por qué importa.** Es la garantía central del pilar 1 («el error es imposible por diseño») y afecta a las dos capas que lo sostienen. No es un caso rebuscado: rubros reales del SJF contienen la palabra «inexistente» con naturalidad (actos inexistentes, notificaciones inexistentes, sociedades inexistentes), y también «no verificable» o «bloqueado». Un escrito que cite uno de esos criterios desactiva el control para **todas** las citas escritas a mano en esa línea. Tampoco hace falta mala fe: basta redactar con normalidad sobre esos temas.

**Causa probable.** El propio docstring de `citas_a_mano` dice «sin marca ⚠/❌»: la intención eran los dos símbolos. Las cuatro palabras se agregaron para detectar marcas en prosa, pero el match es por línea completa y no distingue el texto citado del texto del autor.

**Alcance exacto.** `marcada_no_verificada` se consume en tres lugares (`grep` sobre `scripts/` y `hooks/`): `ensamblar_documento.py:81` y `guardia_escritura.py:61` —las dos capas afectadas— y `nucleo/citas.py`, donde se define. La ruta de validación (`verificar.py lote` → `reporte_vvca.py informe`) **no** lo usa: por eso el informe VVCA de `dictamen_ia.md` marcó correctamente FAIL la cita FICT-0404 pese a que su rubro contiene la palabra «INEXISTENTE» y la extracción la había marcado `marcada_no_verificada: true`. Validar un documento ajeno sigue siendo confiable; producir uno propio, no.

**Propuesta (sin aplicar).** Nivel 1 · diseño: que la exención exija el símbolo ⚠ o ❌ —o una marca explícita como `⚠ NO VERIFICADO`, que es lo que el propio mensaje del guardia enseña al usuario— **fuera** de comillas « », “ ” y " ", y adyacente a la cita, no en cualquier parte de la línea. Las cuatro palabras sueltas sobran: el mensaje del hook ya pide el símbolo. Nivel 3 · prueba: un caso de eval y una prueba de pytest que fijen «cita a mano + palabra `INEXISTENTE` dentro del rubro ⇒ denegado», una por cada capa (ensamblador y guardia).

**Artefactos de la prueba:** `salidas/sonda-b.md`, `salidas/sonda-guardia-b.md`, `borradores/sonda-a.md`, `borradores/sonda-b.md`. Se dejan en disco como evidencia; ninguno es un entregable.

## D-05 · Media — evidencia de una corrida en fixture etiquetada como `[real]`

**Qué pasa.** Las verificaciones «sin registro digital» se guardan con `modo_fuente = real` aunque el proyecto esté en modo fixture (filas #6 y #13 del almacén).

**Causa.** `verificar.py:128-130`: el atajo para «sin registro» construye `captura` sin la clave `modo_fuente`, y `verificar.py:112` cae al literal `"real"` (`captura.get("modo_fuente", "real")`) sin consultar `config["modo"]`. El mismo literal por omisión está en `nucleo/evidencia.py:86`.

**Alcance real, sin exagerar.** Hoy no se puede fabricar evidencia utilizable: `vigente()` (`nucleo/evidencia.py:121-131`) exige veredicto PASS y esta ruta siempre produce BLOCKED. Es un defecto de etiquetado del rastro de auditoría. Lo que preocupa es la dirección del valor por omisión: ante la ausencia del dato, el código elige el lado **más** confiable (`real`) en vez del modo configurado, que es lo contrario de «falla cerrado».

**Propuesta (sin aplicar).** Nivel 1 · diseño: que el valor por omisión de `modo_fuente` sea `config["modo"]` y nunca un literal. Nivel 3 · prueba: una prueba que verifique que ninguna fila escrita durante una corrida en fixture queda marcada como `real`.
