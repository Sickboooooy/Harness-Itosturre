# Diagnóstico de la ronda 4 y protocolo de cierre de itostack 0.1.2

Fecha: 2026-11-19. El operador suspendió el ciclo auditoría → corrección → auditoría. No hay quinta revisión general.

## 0. Estado de partida

- Cuando llegó la instrucción ya estaban aplicados unos parches tácticos para los 10 hallazgos de la ronda 4: la «ronda 5». Están en el árbol de trabajo, sin commit, y no se revirtieron, porque revertir también es modificar código.
- Con ellos: `pytest` 257 passed, 1 skipped · autoprueba 18/18 · lint 0 · `tsc` 0. Esos parches no han pasado por revisión de Codex.
- Se modifica el plugin solo cuando el operador decida (sección 5).

## 1. Método

Se reconstruyó la versión exacta que revisó Codex en la ronda 4 (`git archive bfd1ee1` —el commit base de 0.1.2— + `git apply version-revisada-r4.patch`). Contra ella se ejecutó un caso concreto por hallazgo (`reproducir_r4.py`, salida en `reproduccion-r4.txt`), y después contra la versión actual.

- **Reproducido**: un caso ejecutado muestra el defecto en la versión revisada.
- **Hipótesis**: el defecto existe en el código, pero el flujo real no lo alcanza.
- El riesgo se evalúa con el modelo de amenaza declarado: un agente cooperativo que se equivoca o se apura, no un atacante que falsifica archivos.

## 2. Los diez hallazgos

| Hallazgo | Reproducido en la versión revisada | Hoy | Riesgo real | Prioridad | Causa raíz |
|---|---|---|---|---|---|
| R4-1 · Un segundo rubro para una sola cita no se coteja | Sí | Corregido (parche) | **Medio · citas.** Un entregable puede atribuir un rubro falso a un registro verificado | Alta | CR-1 |
| R4-2 · La ❌ del registro exime a una clave de otro segmento | Sí | Corregido (parche) | Medio-bajo · citas. Requiere que la clave tenga evidencia vigente de otra tesis | Alta | CR-1 |
| R4-3 · Una marca dentro de una cita «…» de varias líneas exime | Sí | Corregido (parche) | Medio-bajo · citas. Es la misma clase que D-04: el texto citado controla la exención | Alta | CR-1 |
| R4-8 · Falso rechazo de un rubro con comillas interiores | Sí | Corregido (parche) | Sin riesgo de seguridad (falla cerrado). Usabilidad. **Lo introdujo un parche propio de la ronda 2** | Media | CR-1 |
| R4-9 · Falso rechazo de un rubro declarado con puntos propios | Sí | Corregido (parche) | Sin riesgo de seguridad. Usabilidad. **Lo introdujo un parche propio de las rondas 3 y 4** | Media | CR-1 |
| R4-5 · Se acepta un veredicto con la rúbrica de otra skill | Sí | Corregido (parche: `por_skill.json`) | **Medio · holdout.** Un `--rubrica` equivocado aprobaría el holdout con criterios ajenos | Alta | CR-3 |
| R4-10 · Respuesta del juez fuera de contrato (sin `fallos_criticos`, o `[]`) | Sí | **Sigue en la compuerta.** El parche valida en los scripts que generan el veredicto, no donde se consume | Bajo hoy (Ollama no instalado; Codex con esquema forzado). Medio en producción con Ollama | Media | CR-3 |
| R4-6 · Una ruta entrecomillada con espacios permite leer la reserva | Sí | Corregido (parche: `shlex`) | **Medio · holdout.** Las rutas del operador tienen espacios («CFDI-GEN demo») | Alta | CR-2 |
| R4-7 · `HOLDOUT-` / `EVALS/` en mayúsculas en Windows | Sí | Corregido (parche) | Medio-bajo · holdout | Media | CR-2 |
| R4-4 · `acciones_externas_permitidas` fuera de la huella | Sí (la huella no cambia) | «Corregido» | **Hipótesis sin riesgo en el flujo real.** Los casos corren en espacios aislados que `preparar.sh` inicializa con los valores por omisión del plugin; la configuración del operador no les llega. Incluirla en la huella (aquí y en R3-2) es una dependencia falsa: invalida candidatas cuando el operador edita su `config.json`, sin proteger nada | Revertir | CR-4 |

## 3. Causas raíz compartidas

### CR-1 · Interpretar citas escritas en texto libre como frontera de seguridad

- **Hallazgos:** R4-1, R4-2, R4-3, R4-8 y R4-9, más unos 14 de rondas anteriores (D-04, N-01, R1-8, R1-9, R2-5, R2-6, R2-13, R2-14, R3-3, R3-4, R3-5, R3-10).
- **Causa:** el guardia deduce de la prosa qué rubro, qué clave y qué marca corresponden a cada registro. Cada heurística tiene esquinas. Cada parche abre otras: R4-8 y R4-9 son falsos rechazos creados por parches anteriores.
- **Cambio arquitectónico único (nivel 1 de la pirámide):** en las salidas jurídicas, una cita solo puede existir como marcador estructurado.
  - `[[CITA:registro|forma]]`: lo resuelve `ensamblar_documento.py` desde la evidencia.
  - `[[CITA_AJENA:registro]]`: se renderiza como «⚠ NO VERIFICADO».
  - Cualquier registro o clave fuera de un marcador se deniega. El detector de texto libre queda como alarma, que solo necesita detectar; ya no decide a qué cita pertenece cada rubro. Sus errores solo producen denegaciones de más, nunca exenciones.
  - El rubro y la clave nunca los escribe el agente: los pone el renderizador desde la evidencia.
  - `validar-documento` (auditar documentos ajenos) conserva la extracción heurística, porque ahí cada cita extraída termina en `verificar.py` y en el informe, no en una exención.
- **Decisión del operador:** cambia cómo se redactan los entregables.

### CR-2 · Reserva holdout dentro del árbol de trabajo, protegida por patrones de texto

- **Hallazgos:** R4-6 y R4-7, más R2-5, R2-7, R3-6 y N-08.
- **Causa:** el comando y la ruta se inspeccionan como texto, y el citado del intérprete, las mayúsculas, las variables, los globs y `python -c` siempre ofrecen otra vía.
- **Cambio arquitectónico único:** sellar la reserva.
  - Los casos `holdout-*` salen de `evals/` y pasan a un archivo opaco (comprimido y cifrado) que solo `compuerta_holdout.py` abre, dentro de una copia temporal del plugin, después de `reservar`.
  - Con el modelo cooperativo, el riesgo real es la exposición accidental (un grep, una lectura), y un archivo opaco la elimina sin depender de patrones.
  - Los guardias de lectura quedan como defensa adicional.

### CR-3 · La compuerta confía en archivos que le entregan

- **Hallazgos:** R4-5 y R4-10, más N-06, R2-1, R2-2, R2-3, R3-7 y R3-8.
- **Causa:** resultados y veredictos llegan como archivos con `--resultados` y `--juez`. La compuerta valida sus campos, pero no los produjo.
- **Cambio arquitectónico único:** el holdout es una transacción orquestada por la compuerta, que hace todo en una sola corrida y registra un manifiesto caso → artefacto → huella → rúbrica → veredicto → juez:
  1. reserva el intento;
  2. materializa la reserva sellada;
  3. corre `claude plugin eval`;
  4. extrae el artefacto de cada caso;
  5. llama al juez con la rúbrica de `por_skill.json`;
  6. valida cada respuesta contra el esquema;
  7. decide.

  El operador ya no entrega veredictos ni elige la rúbrica.
- **Requisito:** correr `claude plugin eval`, que en esta máquina necesita WSL, y conocer el formato de su directorio de resultados. Se verifica allá.

### CR-4 · Configuración del ambiente tratada como entrada de la evaluación

- **Hallazgo:** R4-4, más R3-2.
- **Diagnóstico:** el riesgo no existe en el flujo nativo, y la «corrección» agrega una dependencia falsa.
- **Acción:** revertir `_configuracion_evaluada` de la huella. La invariante real ya se cumple por construcción: el comportamiento evaluado depende solo de archivos del plugin y del andamiaje del caso, y ambos están en la huella.

**Resultado:** 3 cambios arquitectónicos (CR-1, CR-2 y CR-3) cubren 9 de los 10 hallazgos; el décimo se resuelve revirtiendo. Señal de no convergencia del ciclo táctico: 11 → 16 → 14 → 10 hallazgos por ronda, y en la ronda 4, 2 de los 10 fueron regresiones de parches propios.

## 4. Invariantes críticos y criterios de aceptación

Cada invariante se da por demostrado solo con una prueba nombrada que lo ejercita y pasa. Sin prueba, queda **no demostrado** y va a «Límites conocidos».

### Controles de seguridad

| ID | Invariante | Criterio verificable | Estado |
|---|---|---|---|
| I-1 | Ninguna acción hacia afuera sin compuerta humana efectiva | `TestCompuertaHumana`: en default/acceptEdits/plan → ask; en auto/dontAsk/bypass/sin dato → deny; la lista curada no salta el control de citas. **Más una medición en vivo** en una sesión en modo auto: `git push --dry-run origin main` debe ser denegado (B-02 se confirmó en vivo; su cierre también) | Pruebas: sí. En vivo: pendiente |
| I-2 | En producción, los datos no salen | Sin `"entorno": "desarrollo"` → `revisar_codex.py` sale con 3 sin invocar a Codex. Ollama: solo hosts locales exactos, sin proxy, sin redirecciones | Demostrado (pruebas) |
| I-3 | El juez externo solo ve el mensaje | Prueba en vivo con archivo secreto y `--json` de Codex: **0 llamadas a herramientas** en el registro de eventos. La prueba actual no distingue «sin herramienta» de «se negó» | Parcial |

### Integridad del holdout

| ID | Invariante | Criterio verificable | Estado |
|---|---|---|---|
| I-4 | Un solo intento por candidata | El segundo `reservar` falla; **dos procesos simultáneos → exactamente uno reserva** (prueba con procesos reales; hoy solo se simula con una marca previa) | Parcial |
| I-5 | La reserva no es legible para quien mejora la skill | Con CR-2: un texto centinela dentro de un caso holdout no aparece en ningún archivo del árbol de trabajo (búsqueda = 0); el sellado es opaco. Hoy: solo guardias, con límites declarados | No demostrado |
| I-6 | Lo congelado es inmutable | Cambiar skill, reserva o juez después de congelar → rechazo sin consumir; no se re-congela una huella | Demostrado (pruebas) |
| I-7 | Aceptar exige dev 1.0, holdout 1.0 en todos los casos y el visto bueno del juez de otra familia por caso, con la rúbrica de la skill y cobertura completa | Con CR-3: lo decide un manifiesto producido por la propia compuerta. Hoy: pruebas sobre archivos entregados (R4-10 sigue en la compuerta) | Parcial |

### Exactitud de las citas jurídicas

| ID | Invariante | Criterio verificable | Estado |
|---|---|---|---|
| I-8 | Ninguna cita en un entregable sin evidencia PASS vigente o marca estructural de no verificada | Con CR-1: prueba por propiedades (Hypothesis) que genera documentos con registros y claves fuera de marcadores → siempre deny | No demostrado por construcción (hoy heurístico) |
| I-9 | El rubro y la clave mostrados son los de la evidencia | Con CR-1: propiedad «rubros y claves del documento ensamblado == evidencia» para documentos generados con marcadores; un rubro escrito a mano junto a un registro → deny | Parcial (heurístico) |
| I-10 | El texto citado nunca cambia el estado de verificación (clase D-04) | Con CR-1: trivial, porque las marcas son fichas estructurales | Parcial (heurístico) |
| I-11 | La compuerta del lint nunca da verde sin cobertura | `TestLintDiff`: sin cambios, base inválida o archivo ilegible → 2; nuevos sin rastrear examinados | Demostrado (pruebas) |

## 5. Protocolo de cierre de 0.1.2

**Alcance recomendado.** 0.1.2 = integración de Codex más correcciones tácticas, con los invariantes demostrables probados y los demás declarados como límites. CR-1, CR-2 y CR-3 pasan a 0.2.0, cada uno con su criterio de la sección 4.

Pasos, cada uno con resultado PASS/FAIL:

1. **Decisión del operador sobre los parches de la ronda 5:** conservarlos como provisionales (recomendado: cierran R4-1/2/3/5/6/7/8/9 y tienen regresión) o revertirlos al estado revisado.
2. **Revertir la configuración en la huella** (CR-4). Criterio: la huella no cambia al editar `.itostack/config.json` del operador; sí cambia al editar cualquier archivo del plugin o de los casos.
3. **Validar el contrato del veredicto en la compuerta** (R4-10). Criterio: un veredicto sin `fallos_criticos`, `[]` o `null` → error de configuración sin excepción y sin consumir el intento.
4. **Congelar el código y correr la batería:** `pytest` completo, autoprueba 18/18, lint 0, `tsc` 0, `lint --diff` 0 con cobertura informada.
5. **Matriz de invariantes:** cada I-n → prueba(s) nombrada(s) → resultado. Lo que no tenga prueba que pase va a «Límites conocidos» del CHANGELOG (hoy I-3 parcial, I-4 concurrencia, I-5, I-7 orquestado, I-8, I-9, I-10).
6. **Mediciones en vivo:** B-02 en una sesión en modo auto (I-1) y el aislamiento del juez con registro de eventos (I-3). Se adjunta la evidencia.
7. **Sin revisión general.** Opcional: una revisión de Codex acotada a la matriz, que responda una sola pregunta: ¿cada prueba ejercita de verdad su invariante?
8. **Publicación:** CHANGELOG con «Límites conocidos» y `ESTADO.md` actualizados; commit en una rama (no `main`) y PR en borrador, solo con autorización del operador.

**Criterio de salida:** los pasos 2 a 6 en PASS, los límites documentados, y ningún riesgo alto sin una prueba que demuestre su invariante o sin un aplazamiento explícito a 0.2.0 aprobado por el operador.

## 6. Resolución (decisiones del operador, 2026-11-19)

El operador aprobó el diagnóstico y ordenó:

- Conservar los parches de la ronda 5 si pasan sus pruebas sin regresiones.
- Revertir solo las dependencias falsas, después de comprobar que no afectan el comportamiento evaluado.
- Resolver R4-10 en la compuerta consumidora, sin valores por omisión que permitan aprobar.
- Cerrar 0.1.2 como versión experimental.
- Diseñar CR-1, CR-2 (aislamiento por permisos, no solo cifrado) y CR-3 para 0.2.0, sin implementarlos.

Sin commit, push ni publicación.

| Paso | Resultado | Evidencia |
|---|---|---|
| 1 · Parches de la ronda 5 | **Conservados.** Línea base antes de tocar nada: 257 passed, 1 skipped | Esta sesión |
| 2 · CR-4 | **Revertido**, con comprobación previa: con el `preparar.sh` real, el caso arranca con la configuración del plugin, y la lista curada del operador abre la salida en su proyecto pero no en el caso. Límite que se caracteriza: `ITOSTACK_PROYECTO` en el entorno sí redirige el caso (pasa a CR-3) | `TestCierre012::test_el_caso_no_ve_la_configuracion_del_operador` |
| 3 · R4-10 en la compuerta | **Resuelto.** Contrato único derivado del esquema de Codex. Se eliminan cuatro valores por omisión que permitían aprobar. Un veredicto fuera de contrato o incompleto es BLOCKED: no decide ni consume el intento. También se cerró una excepción de `puntajes` con resultados mal formados | `TestCierre012` (grupo I-7), mutantes |
| 4 · Batería | Ver `bateria-cierre.txt` | `bateria_cierre.sh` |
| 5 · Matriz | Generada por script, no a mano | `matriz-invariantes.md` |
| 6 · En vivo | I-1 PASS: auto, dontAsk y bypassPermissions deniegan por la compuerta humana; en manual, el anfitrión sin interfaz no ejecuta. I-3 PASS: el juez no intenta ninguna herramienta, con un control válido | `evidencia-vivo/` |
| 7 · Revisión general | No se hizo, por orden del operador. En su lugar, un pase de mutantes responde la pregunta acotada: ¿cada prueba ejercita de verdad su invariante? | `mutantes-cierre.txt` |
| 8 · Publicación | CHANGELOG con «Límites conocidos» y `ESTADO.md` actualizados. **Sin commit ni push** | — |

Dos hallazgos del propio cierre, que no vinieron de Codex:

- **El primer pase de mutantes dejó vivos 2 de 10.** Una propiedad casi nunca generaba el caso que decía cubrir, y otra nunca llegaba a la rama `cases`. Al reforzarlas con una exploración exhaustiva y una estrategia dirigida apareció un defecto real de mi propio arreglo de `puntajes`. Es la razón para exigir mutantes: una prueba que pasa no basta.
- **El primer control de I-3 no controlaba nada.** Con la terminal habilitada, Codex tampoco la usó bajo el prompt del juez. El rediseño, con el mismo prompt directo y la terminal como única variable, mostró además que el registro `--json` no lista los intentos que el sandbox rechaza; solo quedan en stderr.
