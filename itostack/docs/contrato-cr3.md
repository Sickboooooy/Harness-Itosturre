# Contrato técnico de CR-3 · holdout orquestado por la compuerta

Estado: **contrato preparado, sin implementar** (rama `dev/itostack-0.2.0`, 2026-11-19). Lo complementan:

- esquemas ejecutables en `evals/esquemas/`;
- pruebas de conformidad en `tests/test_contrato_cr3.py`;
- la exploración de `pruebas-manuales/fase-0.2.0/exploracion-plugin-eval.md`.

Objetivo: que la compuerta **produzca** resultados y veredictos en vez de recibirlos, y que rechace (BLOCKED) todo lo que no reconoce. Cada regla tiene un identificador para que una prueba la cite.

## 1. Hechos observados que fijan el contrato

| Hecho | Evidencia | Consecuencia |
|---|---|---|
| Una corrida con falla de infraestructura sale con `error` no vacío, pero **con puntaje**. «Not logged in» dio `score` 0.2857, porque los calificadores negativos «pasan» sin que el agente hiciera nada. La compuerta de 0.1.2 solo lee `aggregates.score` | `tests/datos/resultado_claude_plugin_eval.json` | R6: `error`, `partial` o un calificador que lanzó → BLOCKED, nunca puntaje |
| El informe HTML **se publica en claude.ai por omisión** cuando la cuenta lo permite | `claude plugin eval --help` (2.1.327) | I-2: `--no-publish` es obligatorio |
| Los resultados se escriben por omisión **dentro del plugin** (`<plugin>/evals/results/`) | Ídem | `--output-dir` fuera del plugin, en el almacén de la cuenta de servicio |
| Los calificadores `llm` usan **Haiku** por omisión (`--judge-model`) | Ídem | La identidad del evaluador incluye ese modelo y se congela |
| La ablación «con y sin plugin» excluye del puntaje los calificadores `withOnly` | Ídem | `--ablation none`, registrada en el manifiesto |
| En Windows nativo, el sandbox **no puede sellar** el directorio temporal («directory modes do not restrict access on Windows») | Salida de la exploración | El holdout no corre en Windows nativo |
| Con `--keep-temp`, el temporal contiene **una unión (junction) a `~/.aws/sso` real**; el borrado recursivo sugerido por la CLI puede seguirla en PowerShell 5.1 | Exploración: `Get-ChildItem -Attributes ReparsePoint` | Limpieza: primero quitar los puntos de reanálisis, después borrar |
| En esta máquina, `~/.aws` (22 GB) impide **cualquier** evaluación con Bash en Windows nativo | `tests/datos/resultado_plugin_eval_windows_bloqueado.json` | Plataforma: Linux/WSL bajo la identidad de servicio (CR-2) |
| `runsPerCase` informa el valor del caso aunque `--runs` lo cambie | Ídem (`runsPerCase: 3`, 1 corrida) | R6: las corridas reales se cuentan en `arms.with` |
| **Laboratorio Linux:** sin backend de sandbox, una corrida termina con `error` («cannot confine» el Bash), `partial: false`, `turns` 0 y **código 1**, el mismo de un fallo de la candidata. Con sandbox y sin sesión, termina con «Not logged in», `partial: true` y **código 2** | `pruebas-manuales/fase-0.2.0/laboratorio-wsl.md` | R4 y R6: ni el código de salida ni `partial` bastan; decide `error` o un «grader threw» |
| En Linux la evaluación necesita **bubblewrap y socat** (backend de sandbox), y los hooks de itostack necesitan **node**. Sin node, los guardias fallaban abiertos (código 127, no bloqueante); corregido en CR-1.2 | Ídem | P3 y E4: verificar las herramientas y una guardia funcionando antes de evaluar |
| En Linux el temporal se **sella** (`sealed/`, modo 000) y no tuvo enlaces ni montajes. El HOME aislado trae señuelos vacíos (`.aws`, `.ssh`, `.config/anthropic`) | Ídem | V4: limpieza por sistema operativo |

## 2. Plataforma

- **P1.** El holdout corre en Linux, en el ejecutor aislado de CR-2 (VM o CI, `docs/cr2-ejecutor-aislado.md`). Nunca como el usuario del agente y nunca en Windows nativo.
- **P3.** La imagen del ejecutor incluye `node` (hooks), `bubblewrap` y `socat` (sandbox), `python3` y `git`, con versiones registradas en el manifiesto.
- **P2.** La versión de `claude` y la de `codex` se fijan al congelar; otra versión al ejecutar → BLOCKED.

## 3. Entorno de la corrida (validación estricta)

- **E1.** La evaluación recibe un entorno construido desde cero, no heredado. Contiene:
  - `PATH` fijo;
  - `HOME` de la cuenta de servicio;
  - `LANG=C.UTF-8`;
  - `TMPDIR` dentro del almacén;
  - las credenciales que `claude` necesita, en la forma que confirme el spike.

  Se registran los **nombres** de las variables, nunca sus valores.
- **E2.** No hay ninguna variable `ITOSTACK_*`, `PYTHON*`, `NODE_OPTIONS`, `CLAUDECODE` ni `CLAUDE_CODE_ENTRYPOINT`. Es una lista de permitidas, no de prohibidas: toda variable no listada en E1 queda fuera. Cierra el límite de CR-4 documentado en 0.1.2.
- **E3.** Antes de evaluar se comprueban:
  - que la reserva esté «aislada» (`evals/reserva.json`, y con CR-2 en el almacén de la cuenta);
  - que la huella de la copia materializada sea igual a la congelada;
  - que la huella de la reserva sea igual a la congelada.

  Cualquiera distinta → BLOCKED sin consumir el intento.
- **E4. Verificación previa de infraestructura**, sin consumir el intento:
  - que estén `node`, `bwrap`, `socat`, `python3`, `git` y `claude`, en sus versiones (P3);
  - una prueba de humo de que una guardia PreToolUse de la copia deniega una acción conocida, con su comando exacto de `hooks.json`.

  Sin guardias funcionando no se evalúa.

## 4. Invocación de `claude plugin eval`

- **V1.** Opciones obligatorias, y ninguna otra salvo `--allow-tools`:

  ```text
  --tag holdout --case "<skill>.*" --runs <congelado> --ablation none --scaffold --trust-plugin
  --model <congelado> --judge-model <congelado> --no-publish --mocks record --concurrency 1
  --output-dir <almacén>/<intento>/ --json <almacén>/<intento>/resultados.json --max-cost-usd <tope>
  ```

- **V2.** `--allow-tools` es exactamente la unión de los `allowed_tools` de los casos de la reserva; nada más.
- **V3.** El `argv` completo queda en el manifiesto (`evaluador.argv`).
- **V4.** Si se usa `--keep-temp` para extraer artefactos, la limpieza no sigue ningún enlace ni cruza ningún montaje. Procedimiento verificado en `pruebas-manuales/fase-0.2.0/lab/limpiar.sh`:
  1. abrir permisos solo en directorios reales (`find -P -xdev -type d`), porque en Linux lo escrito por el agente queda sellado con modo 000;
  2. listar los enlaces y borrarlos sin seguirlos;
  3. borrar el resto con `rm -r --one-file-system`;
  4. verificar que los destinos de los enlaces siguen intactos.

  Nunca se ejecuta `git` ni nada que cargue configuración desde ahí dentro.

## 5. Validación de resultados

Esquema: `evals/esquemas/resultado-plugin-eval.schema.json` (estricto; provisional hasta observar una corrida exitosa).

- **R1.** JSON legible y conforme al esquema; si no → BLOCKED.
- **R2.** `schemaVersion == 1` y `claudeVersion ==` la congelada; si no → BLOCKED.
- **R3.** `suite` coincide con lo pedido (`ablation`, `modelOverride`, `caseFilter`, `threshold`, `concurrency`); `plugins[0].path ==` la copia materializada; `plugins[0].version ==` la de la candidata. Si no → BLOCKED.
- **R4.** `partial == false`; si no → BLOCKED, con `partialReason` en el manifiesto. **`partial == false` no prueba que la corrida haya ocurrido** (laboratorio: sin sandbox, `partial` vale `false` y `turns` 0); por eso R6 se aplica siempre. **El código de salida no decide nada:** 1 y 2 aparecieron en fallas de infraestructura.
- **R5.** El conjunto de nombres de casos es **exactamente** el de la reserva: ni falta ni sobra uno. Si no → BLOCKED.
- **R6.** Cada corrida de cada caso debe cumplir:
  - `error == ""`;
  - `skippedPaidGraders == false`;
  - un resultado por cada calificador del caso (mismos nombres);
  - ninguna `explanation` que empiece con «grader threw»;
  - `len(arms.with) ==` las corridas pedidas.

  Si alguna falla, el caso es BLOCKED. Para decidir qué pasa con el intento:
  - si **todas** las corridas BLOCKED tienen `turns == 0`, el agente no vio los casos: el intento es **REINTENTABLE**;
  - si no, la reserva quedó expuesta: el intento queda **INCONCLUSO**, se consume sin aceptar y la candidata necesita una huella nueva.
- **R7.** El puntaje de cada corrida se recalcula desde sus calificadores (pesos, `scored`, `withOnly`) y debe coincidir con el informado. **Por confirmar en el spike:** la fórmula exacta (las dos salidas observadas son compatibles con «peso aprobado / peso total puntuado»).
- **R8.** Un caso ACEPTA solo si todas sus corridas valen 1.0 sin BLOCKED; si una corrida válida vale menos de 1.0, RECHAZA.

## 6. Identidad del evaluador

- **I1. Evaluador de los casos** (`claude plugin eval`): versión de `claude`, `--model` y `--judge-model`. Se congela al congelar la candidata; cualquier diferencia → BLOCKED.
  - Los calificadores `llm` son de la familia Claude, la misma del trabajador. Cuentan para el puntaje de la evaluación, **no** como el juez de otra familia.
- **I2. Juez de otra familia:** familia, herramienta, modelo, esfuerzo, versión exacta (`codex --version`) y el sha256 de sus opciones (`revisar_codex.comando()`). Se congela igual.
- **I3. Rúbrica:** la de `evals/rubricas/por_skill.json` **de la copia congelada**; nunca un argumento.
- **I4.** El juez se llama como función, no por archivos. Cada respuesta cruda se guarda sellada; se valida con `juez.errores_contrato` y se califica con `juez.calificar`, el mismo contrato de 0.1.2.
- **I5.** Una respuesta BLOCKED se reintenta hasta K = 2 veces, y cada intento queda en `casos[].juicios`. Si sigue BLOCKED → PENDIENTE_DE_JUICIO. `reanudar` vuelve a juzgar los artefactos sellados, que no cambian. Nunca se acepta sin juicio.

## 7. Manifiesto y diario

Esquema: `evals/esquemas/manifiesto-holdout.schema.json`.

- **M1.** El diario es de solo anexar. Cada entrada lleva el sha256 de la anterior. La cabeza va en el manifiesto y en el historial, y se muestra al operador.
- **M2.** `verificar-manifiesto` recalcula todo:
  - los hashes de resultados, trazas, artefactos y respuestas;
  - la calificación desde las respuestas crudas;
  - la cadena del diario;
  - la rúbrica contra `por_skill.json` de la copia.

  Cualquier diferencia → el manifiesto no vale.
- **M3.** Un manifiesto de holdout solo existe con la reserva «aislada»; el esquema lo exige.
- **M4.** La decisión se escribe una vez (marca exclusiva, como en 0.1.2). Con CR-2, en un almacén que el usuario del agente no puede escribir.
- **M5.** Cada caso del manifiesto ata su veredicto a cuatro cosas, todas obligatorias en el esquema:
  - un identificador opaco: el sha256 del nombre, que revelaría qué se prueba;
  - la huella de su definición;
  - la huella de su rúbrica autorizada;
  - la huella de la identidad del evaluador, más la de sus artefactos y cada juicio con su veredicto.

  El ejecutor de CR-2 firma el manifiesto (`ssh-keygen -Y sign`), y el constructor lo verifica con la clave pública versionada.

## 8. Incógnitas que resuelve el spike en WSL

| Incógnita | Cómo se resuelve | Bloquea |
|---|---|---|
| Forma de una corrida **exitosa** (`graders[]` con resultados reales, `tracePath`) | Correr un caso de desarrollo con sesión iniciada; guardar la salida en `tests/datos/` y validarla con `test_contrato_cr3.py` | R6, R7 |
| Fórmula del puntaje | Comparar `score` con los calificadores en al menos dos casos con resultados mixtos | R7 |
| Dónde queda el artefacto que califica el juez (espacio final, último mensaje, `out/trace.jsonl`) | `--keep-temp` y lectura de `out/` | Extracción (paso 5) |
| Credenciales de `claude` para una cuenta de servicio sin interfaz | Documentación de Claude Code y prueba con la cuenta de CR-2 | E1 |
| Códigos de salida (0, 1 por umbral, 2 por tope de costo) | Corridas con resultado PASS, FAIL y tope | Clasificación |

## 9. Criterios de aceptación y de terminación de CR-3

| ID | Propiedad verificable | Prueba |
|---|---|---|
| A3-1 | Juez falso que reprueba → RECHAZADA; que aprueba todo → ACEPTADA; BLOCKED → PENDIENTE_DE_JUICIO, nunca ACEPTADA | Integración con `claude` y juez falsos |
| A3-2 | Para cada skill, el juez recibe exactamente los bytes de su rúbrica | Propiedades |
| A3-3 | `verificar-manifiesto` detecta el cambio de cualquier byte de cualquier archivo sellado | Propiedades |
| A3-4 | No existen `--juez` ni `--resultados` para el holdout | Unitaria |
| A3-5 | Una variable fuera de E1 en el entorno del lanzador no llega a la evaluación | Integración |
| A3-6 | Dos `ejecutar` simultáneos → una evaluación y una decisión | Procesos reales |
| A3-7 | Por propiedades: para toda salida conforme al esquema con `error`, `partial` o un calificador que lanzó, la clasificación es BLOCKED, sea cual sea su puntaje. Así ninguna falla de infraestructura acepta | Hypothesis sobre las salidas reales mutadas |
| A3-8 | Corrida real en WSL bajo la cuenta de servicio, con el manifiesto verificado | En vivo |
| A3-9 | Pase de mutantes sobre el orquestador y el clasificador: 100 % detectados | `mutantes` |

**Terminación:** de A3-1 a A3-9 en PASS. No se agregan reglas después sin una observación nueva que las motive.

## 10. Defectos latentes de la compuerta de 0.1.2 que este contrato cierra

Hoy no tienen efecto práctico: `evals/reserva.json` está «contaminada» y `reservar` y `holdout` se niegan.

- `puntajes()` ignora `error` y `partial`: una falla de infraestructura con calificadores negativos podría aceptar (R6).
- El camino `holdout` sin juez lanza `claude plugin eval` sin `--no-publish` ni `--output-dir`: publicaría los prompts del holdout y escribiría los resultados dentro del plugin (V1).
- El entorno de la evaluación se hereda del lanzador (E1 y E2).
