# Fase Codex · auditoría cruzada e itostack 0.1.2 (2026-11-18)

**Qué se hizo.** Codex (OpenAI, `gpt-6.1-sol`, codex-cli 0.167.0-alpha.3.2), otra familia de modelos, auditó el harness contra el plan (metodología de Lauren Tan / pstack) en modo de solo lectura. Después se integró como juez y revisor de otra familia, y se corrigieron los hallazgos acotados. El operador autorizó el cambio y modificó antes la regla de privacidad-local: no aplica mientras se trabaje en local.

**Archivos.**
- `auditoria-prompt.md`: instrucciones y plan que recibió Codex. **No se versiona**: incluye el texto del plan de referencia, que es de terceros; se conserva solo en la copia local.
- `auditoria-codex.json`: 15 hallazgos, todos con `confirmado_leyendo_codigo: true`.
- `juez-codex-informe-vvca.json`: Codex como juez sobre el artefacto de F7-06.
- `interrogar-0.1.2.json`: revisión adversarial de Codex sobre el diff de 0.1.2.

## Prueba del juez de otra familia (reproduce F7-06)

Mismo artefacto (`salidas/informe-vvca.md`) y misma rúbrica (`evals/rubricas/informe-vvca.md`) que F7-06.

| Juez | Veredicto | Criterio 4 (advertencias de contexto) | Correcto según la verificación manual de F7-06 |
|---|---|---|---|
| `juez-evals` (Haiku, misma familia), 0.1.1 | 10/10, 6 de 6 cumplidos | «cumple», con evidencia que corresponde a otro criterio | No |
| `revisar_codex.py --rol juez` (Codex), 0.1.2 | 5 de 5 aplicables, 1 no aplicable → puntaje 10 calculado, aprobado | `no_aplicable`: «ninguna cita presenta un corte temporal, una Sala extinta o una tesis aislada», y distingue la advertencia de fixture | Sí |

## Hallazgos de la auditoría y estado

| ID | Gravedad | Hallazgo | Estado en 0.1.2 | Prueba |
|---|---|---|---|---|
| D-04 | Crítica | Una palabra del rubro desactiva dos controles de evidencia | **Corregido** (marca explícita, fuera de comillas) | `TestMarcaNoVerificada` |
| N-01 | Alta | Evidencia de un registro respalda un rubro falso | **Corregido** (cotejo del rubro explícito contra la evidencia, en guardia y ensamblador) | `TestRubroContraEvidencia` (incluida una con evidencia real del fixture) |
| N-09 | Alta | El juez de otra familia no era requisito de aceptación | **Corregido** | `TestCompuertaConJuez` |
| N-07 | Alta | El intento holdout se consume demasiado tarde | **Corregido** (marca de creación exclusiva antes de evaluar) | `test_intento_se_consume_…`, `test_marca_de_consumo_atomica` |
| N-08 | Alta | Reserva holdout legible y fuera de la huella | **Parcial**: huella ampliada, huella de la reserva y guardias de lectura (Read, Grep, Glob, Bash). Una búsqueda amplia sobre todo el repositorio todavía puede tocarla; falta separarla físicamente | `TestReservaHoldout`, `test_la_huella_cubre_rubricas_y_agentes` |
| B-02 | Alta | La compuerta humana depende de un `ask` que el anfitrión aprueba solo | **Corregido en lo medido**: en auto, dontAsk o bypassPermissions la compuerta deniega. La propuesta completa de Codex (un ejecutor con autorización humana vinculada al comando exacto) queda pendiente | `TestCompuertaHumana` |
| D-10 | Media | `lint --diff` aprueba sin examinar | **Corregido** | `TestLintDiff` |
| D-16 | — | Grader con «sala» sin delimitar | **Corregido**: rota 0.80 → 0.60 | autoprueba 18/18 |
| D-17 | — | El juez forzaba un 10 binario | **Corregido** (el puntaje lo calcula el programa) | `TestContratoJuez` |
| N-02 | Alta | El adaptador rellena el registro observado con el solicitado | Pendiente: cambia el contrato del verificador (registro solicitado vs. observado) | — |
| N-03 | Alta | El informe VVCA puede atribuir un lote a otro documento | Pendiente: manifiesto de validación con huella del documento | — |
| D-07 | Alta | PASS no acredita el texto de la tesis | Pendiente (estructural, ya registrado) | — |
| N-04 | Alta | Una ruta vacía o con acciones desconocidas puede dar PASS | Pendiente: esquema validado de rutas con expectativa final obligatoria | — |
| N-05 | Alta | El cierre acepta cualquier PASS anterior de la sesión | Pendiente: comprobantes estructurados vinculados al cambio | — |
| N-06 | Alta | La compuerta acepta puntajes sin procedencia verificable | Pendiente: manifiesto de ejecución firmado por el ejecutor de evals | — |
| D-13 | Alta | Las correcciones corteses no se registran | Pendiente: registrar eventos y clasificar después | — |
| N-10 | Alta | Una elevación se da por resuelta sin barrera implementada | Pendiente: estados propuesta → implementada → verificada | — |

## Revisión adversarial de Codex sobre el diff (/interrogar)

**Ronda 1** (`interrogar-0.1.2.json`): veredicto **rechazar**, 11 hallazgos, todos validados contra el código y corregidos:

| # | Hallazgo de Codex | Corrección |
|---|---|---|
| 1 | Con juez externo, la evaluación y el juicio ocurrían antes de consumir el intento | `reservar` consume el intento antes de correr; resultados y veredictos deben ser posteriores |
| 2 | Veredictos no atados a artefacto ni rúbrica; un veredicto de desarrollo servía como holdout | Huellas de artefactos y rúbrica en el veredicto; rúbrica congelada obligatoria; reciclar artefactos de desarrollo se rechaza; bitácora del juez: un reprobado previo prevalece |
| 3 | `{"criterios":[{"cumple":"si"}]}` sacaba 10 | Cobertura exacta de los criterios numerados de la rúbrica; «si» sin evidencia = «no» |
| 4 | Se podía re-congelar la misma candidata con otro juez o sin juez | Una candidata congelada no se re-congela; sin juez, la aceptación dice «SIN JUEZ EXTERNO» |
| 5 | Grep sobre `evals/` y python leían la reserva | Grep sobre `evals/` y `evals/<skill>/` denegado; python y búsquedas sobre todo el repo quedan como límite declarado |
| 6 | Sandbox de solo lectura no impide leer rutas absolutas | Juez sin herramientas (`--disable shell_tool`, navegador, apps, plugins); prueba en vivo con archivo secreto: no se filtró |
| 7 | Recorte silencioso del material | Material excedido = BLOCKED |
| 8 | `Rubro: LA …` sin comillas saltaba el cotejo de N-01 | El texto tras «rubro» debe empezar con el rubro oficial |
| 9 | Una marca ❌ eximía a toda la línea y el párrafo | Marca acotada a su segmento («;» o fin de oración) y a su referencia |
| 10 | `http://localhost.atacante.example` pasaba como local | Parser de URL: host exacto, sin credenciales, solo http, sin redirecciones |
| 11 | Archivo `app_node_modules_extra.py` excluido del lint | Exclusión por componente de ruta |

**Ronda 2** (`interrogar-0.1.2-r2.json`): veredicto **rechazar**, 16 hallazgos más finos. Las correcciones de la ronda 1 se sostienen. Corregidos en una tercera ronda:

| # | Hallazgo de Codex | Corrección |
|---|---|---|
| 1 | Cinco repeticiones del mismo criterio cubrían una rúbrica de cinco | Criterios por número; deben cubrir 1..N sin repetir |
| 2 | Evidencia inventada por el juez daba PASS | El fragmento entre «» debe existir en el artefacto; si no, el «si» cuenta como «no» (comprobado sin falsos negativos sobre el veredicto real de F7-06) |
| 3 | Veredictos no atados a casos | `--caso`; el holdout exige un veredicto por caso. Atar artefactos a los resultados de `claude plugin eval` queda para el manifiesto del ejecutor (N-06) |
| 4 | El archivo se releía para la huella después del juicio | Instantánea única |
| 5 | «RUBRO:» y `rubro: "FALSO"` escapaban al cotejo | Palabra sin distinguir mayúsculas; rubros entrecomillados de cualquier longitud |
| 6 | «FICT-0404 ❌, pero se aplica FICT-0009» eximía a ambos | La marca exime solo al grupo de citas pegado a ella |
| 7 | `rg -n . evals/verificar-cita` recorría la reserva | El guardia de Bash deniega lectores y buscadores sobre `evals/` y `evals/<skill>/` |
| 8 | Dos registros simultáneos podían escribir decisiones distintas | Marca exclusiva de decisión |
| 9 | `http_proxy` sacaba el texto de Ollama | `ProxyHandler({})` |
| 10 | Huella de rúbrica distinta con CRLF | Bytes en revisor y compuerta |
| 11 | El orden de los artefactos ocultaba un rechazo previo | Conjuntos canónicos |
| 12 | Un rechazo de otro juez vetaba al juez designado | El antecedente debe ser del mismo modelo y versión |
| 13 | Con varias citas en una línea, todas recibían el primer rubro | Cada rubro va a la referencia que lo contiene o a la más cercana de su segmento |
| 14 | El punto de un rubro separaba la cita de su marca | Cortes calculados sin el texto entrecomillado |
| 15 | Re-congelar tras restaurar una versión anterior | Se comprueba contra el historial |
| 16 | Nombres no ASCII se saltaban en el lint | `git ls-files -z` |

**Ronda 3** (`interrogar-0.1.2-r3.json`): veredicto **rechazar**, 14 hallazgos (6 altos), más finos: congelar no atómico, configuración fuera de la huella, rubros en otra línea del párrafo, emparejamiento de claves por posición, registro de una tesis con clave de otra, búsquedas desde un directorio con reserva o con `$R`, identidad parcial del juez en la bitácora, tolerancia de 1 s en la reserva, tramos de evidencia fuera de orden, rubros de más de 800 caracteres, `get-content` en minúsculas, `numero` booleano o decimal, aprobado por puntaje redondeado y archivos no UTF-8 en el lint. Todos corregidos en una cuarta ronda, con su regresión.

**Ronda 4** (`interrogar-0.1.2-r4.json`): ver `ESTADO.md`.

## Verificación de 0.1.2

- `pytest tests -q`: 242 passed, 1 skipped (omitida por diseño en Windows). `tests/test_auditoria_codex.py` añade 144 pruebas.
- `autoprueba.py`: 18/18 coherentes.
- `lint_itosturre.py scripts hooks guardias evals`: 0 hallazgos. `lint --diff`: 0 hallazgos, 18 archivos examinados.
- `tsc --noEmit`: 0 errores.
