# Cambios

## 0.2.0 · en desarrollo (rama `dev/itostack-0.2.0`, sin publicar)

Objetivo: reducir clases de fallos con garantías estructurales. Plan e incrementos en `docs/diseno-0.2.0.md`.

- **CR-1.1 · contrato estructurado de citas (`itostack/citas@1`).** Nuevo `scripts/nucleo/procedencia.py`: gramática formal de marcadores, en la que cada «[[» es un marcador válido o un error:
  - `[[CITA:registro|forma]]`;
  - `[[CITA_AJENA:referencia|fuente]]`: la referencia debe aparecer literal en la fuente;
  - `[[NO_VERIFICADO:texto]]`.

  El ensamblado sale de la evidencia, y ahora un patrón de cita, «rubro:» o una marca ⚠/❌/✅ escritos a mano fuera de un marcador impiden ensamblar. `ensamblar_documento.py` escribe un **manifiesto de procedencia** (`<salida>.procedencia.json`) y se somete a la comprobación de entrega antes de escribir. Nuevo `scripts/verificar_entrega.py`.
- **Reserva contaminada.** `evals/reserva.json` declara la reserva holdout «contaminada» (decisión del operador). `reservar` y `holdout` se niegan salvo con el estado «aislada», que corresponde a CR-2.
- **Contrato técnico de CR-3** (`docs/contrato-cr3.md`), con esquemas ejecutables en `evals/esquemas/` y conformidad contra dos salidas reales de `claude plugin eval` (`tests/test_contrato_cr3.py`). Cierra, cuando se implemente, tres defectos latentes de la compuerta de 0.1.2, hoy neutralizados por la reserva contaminada:
  - una falla de infraestructura con puntaje se tomaba como resultado;
  - el informe se publicaba en claude.ai por omisión;
  - los resultados quedaban dentro del plugin.
- **Modelo de amenazas de CR-2** (`docs/cr2-modelo-amenazas.md`), para aprobación; sin implementar.
- Pruebas nuevas: `test_procedencia.py` (17, por propiedades), `TestReservaContaminada` y `test_contrato_cr3.py` (18). Mutantes: CR-1.1 11/11 y reserva 3/3.

## 0.1.2 — 2026-11-19 · experimental

Versión experimental de integración y evaluación cruzada con Codex. **No es apta para producción jurídica**: las citas de los entregables todavía se controlan con heurísticas (ver «Límites conocidos»). La matriz de invariantes, con pruebas nombradas, mutantes y mediciones en vivo, está en `pruebas-manuales/fase-codex/matriz-invariantes.md`; el diseño que cierra los invariantes pendientes, en `docs/diseno-0.2.0.md`.

Juez de otra familia con Codex y correcciones de la auditoría cruzada (Codex leyó el harness contra el plan: 15 hallazgos, en `pruebas-manuales/fase-codex/`).

- **Juez y revisor de otra familia (pilar 2).** Nuevo `scripts/revisar_codex.py` (Codex CLI, OpenAI) con el mismo contrato que `revisar_ollama.py`, ambos sobre `scripts/nucleo/juez.py`. Codex corre con sandbox de solo lectura, sin sesión persistida, desde un directorio vacío de nombre neutro y con modelo y esfuerzo fijos desde `modelos.json` (ignora `~/.codex/config.toml`). Solo con `"entorno": "desarrollo"`: sin declararlo, el entorno es `produccion` y el script se niega (principio privacidad-local).
- **D-17.** El juez califica cada criterio con `si` / `no` / `no_aplicable`; el puntaje lo calcula el programa (10 × cumplidos / aplicables, 0 con fallo crítico). Todo no aplicable es BLOCKED, no PASS. Codex reprodujo la calificación correcta de F7-06 (5 cumplidos, 1 no aplicable) donde `juez-evals` había dado 10/10.
- **N-09.** `compuerta_holdout.py congelar` exige el visto bueno del juez de otra familia (`--juez`), o un motivo explícito (`--sin-juez-externo`) que queda en el historial. La identidad del juez se congela; cambiarla antes del holdout se rechaza sin consumir el intento. El `aprobado` se recalcula desde los criterios.
- **N-07.** El intento holdout se consume antes de evaluar, con una marca de creación exclusiva: una interrupción, un JSON ilegible o una segunda invocación simultánea ya no permiten repetirlo.
- **N-08.** La huella cubre agentes, rúbricas, fixtures, `_comun` y los instrumentos; la reserva tiene su propia huella, verificada antes del holdout. Nuevo `hooks/guardia_lectura.py` (Read, Grep, Glob) y regla de Bash que deniegan leer casos `holdout-*`.
- **D-04 (crítico).** La marca de cita no verificada solo cuenta fuera de las comillas y debe ser explícita («⚠ NO VERIFICADO», «⚠ CITA NO VERIFICADA», «❌»): una palabra del rubro o una advertencia de contexto ya no eximen de la evidencia.
- **N-01.** La evidencia de un registro ya no respalda un rubro distinto: el guardia de escritura y el ensamblador cotejan el rubro explícito (`rubro: «…»`) contra el oficial de la evidencia.
- **B-02.** Nueva compuerta humana (`_comun.compuerta_humana`): pregunta solo en los modos que de verdad preguntan (default, acceptEdits, plan); en auto, dontAsk o bypassPermissions deniega. Lista curada por el operador en `acciones_externas_permitidas`; no salta el control de citas.
- **D-10.** `lint_itosturre.py --diff` examina también los archivos nuevos sin rastrear, falla ante un error de Git y sale con 2 si no examinó nada; reporta archivos y líneas examinados.
- **D-16.** El grader `explica-contexto` de `pass-advertencia-sala` exige «sala extinta»: la solución rota baja de 0.80 a 0.60.
- **Segunda ronda (revisión adversarial de Codex sobre el diff: «rechazar», 11 hallazgos).** El juez de Codex corre sin herramientas (`--disable shell_tool`, navegador, apps, plugins); prueba en vivo: un artefacto que le ordenaba leer un archivo secreto no obtuvo su contenido. El veredicto exige cobertura exacta de los criterios de la rúbrica (omitir uno es BLOCKED), un «si» sin evidencia cuenta como «no», el material que no cabe es BLOCKED en vez de recortarse, y cada veredicto lleva las huellas de sus artefactos y de su rúbrica y queda en `.itostack/bitacora/juez.tsv`. La compuerta: `reservar` consume el intento antes de correr el holdout; resultados y veredictos deben ser posteriores a la reserva, de una rúbrica congelada, sin reciclar artefactos de desarrollo ni presentar un aprobado después de un reprobado del mismo juez; una candidata congelada no se re-congela; sin juez, la aceptación lo dice. La marca ⚠/❌ exime solo a la cita de su segmento («;» o fin de oración) y de su referencia, no a toda la línea o el párrafo. Un rubro declarado sin comillas debe empezar con el rubro oficial. `revisar_ollama.py` valida el endpoint con un parser de URL (rechaza `localhost.atacante.example`, credenciales, https) y no sigue redirecciones. El guardia de lectura deniega búsquedas de contenido sobre `evals/` y `evals/<skill>/`. El lint ya no se salta archivos cuyo nombre contiene «node_modules».
- **Tercera ronda (segunda revisión de Codex: «rechazar», 16 hallazgos).** Los criterios del veredicto se identifican por número y deben cubrir 1..N sin repetir; la evidencia de cada «si» debe ser un fragmento literal entre «» que exista en el artefacto (si no, cuenta como «no»); el artefacto se lee una sola vez para el mensaje y su huella; la huella de la rúbrica es de bytes en el revisor y en la compuerta (CRLF); `--caso` ata el veredicto a su caso y el holdout exige uno por caso; el antecedente de la bitácora solo veta si es del mismo juez y no depende del orden de los artefactos; la decisión del holdout se escribe una sola vez (marca exclusiva); re-congelar se comprueba contra el historial; «RUBRO:» en mayúsculas y rubros entrecomillados cortos se cotejan; con varias citas en una línea, cada rubro va a la referencia que lo contiene o a la más cercana de su segmento; la marca ⚠/❌ exime solo al grupo de citas pegado a ella y los cortes ignoran la puntuación entre comillas; Ollama sin proxies del entorno; el guardia de Bash deniega lectores y buscadores sobre `evals/` y `evals/<skill>/`; el lint lista archivos nuevos con `-z` (nombres no ASCII).
- **Cuarta ronda (tercera revisión de Codex: «rechazar», 14 hallazgos).** Congelar es una transición única por huella (marca exclusiva); la huella incluía la configuración evaluada (revertido en el cierre: era una dependencia falsa, ver CR-4); con varias citas en un párrafo, cada clave se une al registro más cercano de su segmento y los rubros se asignan con posiciones de todo el párrafo; un rubro sin dueño claro se rechaza; la clave escrita debe ser la de la evidencia del registro; rubros entrecomillados de cualquier longitud; Grep y Bash desde un directorio con reserva, y rutas con variables sin expandir, se deniegan; PowerShell sin distinguir mayúsculas; la bitácora del juez guarda su identidad completa y el antecedente exige coincidencia total; la reserva guarda el instante exacto y no admite archivos anteriores; la evidencia exige todos sus tramos en orden; `numero` debe ser entero JSON; `aprobado` se decide por conteos, no por el puntaje redondeado; el lint respeta la codificación declarada de un .py y devuelve «incompleto» ante un archivo que no puede leer.
- **Quinta ronda (cuarta revisión de Codex: «rechazar», 10 hallazgos).** Un segundo rubro para la misma cita se coteja (R4-1); la marca de un registro ya no exime a una clave de otro segmento (R4-2) ni cuenta dentro de una cita «…» de varias líneas (R4-3); rubros con comillas interiores o con puntos propios ya no se rechazan por error (R4-8, R4-9); el juez debe usar la rúbrica asignada a la skill en `evals/rubricas/por_skill.json` (R4-5); rutas entrecomilladas con espacios y `HOLDOUT-`/`EVALS/` en mayúsculas se tratan como reserva (R4-6, R4-7). Aquí el operador suspendió el ciclo de revisiones: el diagnóstico de causas raíz (`pruebas-manuales/fase-codex/diagnostico-ronda4.md`) mostró que tres cambios de arquitectura cubren 9 de los 10 hallazgos y que el ciclo táctico no convergía (11 → 16 → 14 → 10 hallazgos; 2 de los 10 eran regresiones de parches propios). Esos cambios pasan a 0.2.0.
- **Cierre por invariantes (protocolo del operador).**
  - **R4-10, resuelto en la compuerta consumidora.** Un solo contrato, `juez.errores_contrato`, derivado del mismo esquema que recibe Codex: los revisores lo aplican a la respuesta del modelo y la compuerta al veredicto guardado. Un veredicto ilegible, fuera de contrato o incompleto es BLOCKED: no decide, no consume el intento y no lanza excepción. Se eliminan los valores por omisión que permitían aprobar: `fallos_criticos` ausente leído como vacío; booleanos, «sí» o «true» leídos como «si»; un «si» sin `evidencia_verificada` contado en la compuerta; y la cobertura sin rúbrica (`esperados` es obligatorio). Unos resultados de `claude plugin eval` con forma inesperada ya no lanzan una excepción después de escribir la marca de decisión.
  - **CR-4, revertido.** La `.itostack/config.json` del operador sale de la huella. Antes se comprobó, con el andamiaje real (`preparar.sh`), que el caso arranca con la configuración del plugin y no ve la del operador.
  - **Demostración.** Pruebas por propiedades con oráculo semántico y con `jsonschema` como oráculo independiente (nueva dependencia de desarrollo), exploración exhaustiva de los campos obligatorios, concurrencia con procesos reales para la reserva y la decisión, y un pase de mutantes que reintroduce cada defecto y comprueba que las pruebas fallan. El primer pase encontró dos pruebas que no demostraban lo que decían. Al reforzarlas apareció un defecto real del propio arreglo: `puntajes` aún lanzaba una excepción con casos que no eran objetos. Las tres cosas se corrigieron antes de cerrar.
  - **Mediciones en vivo.** I-1: sesiones `claude -p` reales con el plugin, en modo auto, dontAsk y bypassPermissions, deniegan el push a main por la compuerta humana. I-3: el juez Codex no intenta ninguna herramienta, con un control que sí registra intentos cuando la terminal existe. Codex 0.167 no lista como elemento de `--json` una llamada que su sandbox rechaza: la medición cuenta también el enrutador de herramientas en stderr.
- `tests/test_auditoria_codex.py`: 253 pruebas, una por defecto y variante, más las de cierre (`TestCierre012`).

### Límites conocidos de 0.1.2

Detalle y pruebas en `pruebas-manuales/fase-codex/matriz-invariantes.md`. Cada uno se cierra en 0.2.0 (`docs/diseno-0.2.0.md`).

- **Exactitud de las citas (I-8 no demostrado; I-9 e I-10 parciales).** El guardia deduce de la prosa qué rubro, clave y marca corresponden a cada cita. Las heurísticas cubren los casos probados, no todos. **Toda cita de un entregable de 0.1.2 requiere revisión humana.** → CR-1.
- **Reserva holdout (I-5 no demostrado).** La protegen guardias que inspeccionan comandos como texto, y siempre hay otra vía. Además, los casos `holdout-*` actuales los escribió el mismo agente y están en la historia de Git: ya no son una reserva. Un «ACEPTADA» de 0.1.2 no demuestra generalización. → CR-2.
- **Procedencia del holdout (I-7 parcial).** La compuerta valida lo que recibe, pero no lo produce: no puede demostrar que los resultados y veredictos entregados sean los de la corrida reservada. → CR-3.
- **Marcas de la compuerta (I-4).** Un intento y una decisión se demuestran frente a invocaciones repetidas o simultáneas, no frente al borrado deliberado de `evals/compuerta/`, que el agente puede escribir. → CR-2.
- **Entorno de la corrida (I-6).** `ITOSTACK_PROYECTO` o `ITOSTACK_MODO` en el entorno de `claude plugin eval` redirigen los casos a otro proyecto. `autoprueba.py` los quita; a mano es responsabilidad del operador. → CR-3.
- **Bitácora del juez.** Una corrida BLOCKED queda como «no aprobado» y veta esos artefactos para ese juez. Falla cerrado, pero no distingue BLOCKED de reprobado. → CR-3.
- **Compuerta humana (I-1).** Cubre las acciones que reconocen los guardias: push a main/master, push forzado y envíos MCP. La lista de patrones no es exhaustiva.
- **Aislamiento del juez (I-3).** Se midió con codex-cli 0.167; repetir la medición al actualizar Codex.

## 0.1.1 — 2026-11-18

Corrige los defectos de la fase 0 de pruebas de integración en Windows 11 nativo.

- D-01 (crítico en Windows): `nucleo/config.py` ya no importa `pwd` incondicionalmente; `home_real()` usa `USERPROFILE` cuando no hay `pwd`.
- D-02 (crítico): las guardias fallan cerrado. Nuevo `hooks/lanzar.mjs` (capa 1): si el hook truena, excede el tiempo o no hay intérprete, una guardia PreToolUse deniega; los hooks informativos dejan pasar. Además `_comun.ejecutar()` convierte excepciones en denegación.
- D-03 (alto en Windows): `hooks.json` ya no llama a `python3`; el lanzador busca `py -3`/`python`/`python3` y descarta el alias de la Microsoft Store. El hook de inicio anuncia el intérprete que sí funciona.
- UTF-8 forzado en entrada y salida del núcleo y en toda decodificación de subprocesos (en Windows, cp1252 rompía ✅ ⚠ ❌).
- `arrancar_app.py` multiplataforma (grupo de procesos y `taskkill` en Windows).
- Scripts de evals con `_comun/python.sh`; `compuerta_holdout.py` resuelve `claude.exe`/`claude.cmd`; rutas de Chromium de Playwright en Windows y macOS.
- `.gitattributes` fija LF en `.sh`, `.mjs`, `.py` y demás texto; CI en `ubuntu-24.04` y `windows-latest`.
- `tests/test_plataforma.py`: regresiones que simulan Windows (sin `pwd`, cp1252, intérprete ausente, hook que truena, alias de la Store).

## 0.1.0 — 2026-11-17

- Primera versión del harness itostack con perfiles jurídico y desarrollo.
- Pilar 1: verificador forense de tesis y URL oficiales (Playwright, captura + SHA-256), verificación de app local por rutas del mapa, almacén de evidencia SQLite inmutable.
- Pilar 2: 17 casos nativos de `claude plugin eval` con soluciones de referencia y rotas, autoprueba, compuerta holdout de un solo intento, rúbricas congeladas, juez local con Ollama, pruebas por propiedades.
- Pilar 3: registro automático de correcciones, propuesta y registro de elevaciones, chequeos de salud de transcripciones y tokens, bitácora de decisiones, detector de relleno.
- Pilar 4: ensamblado de citas por marcadores, lint IT001–IT008, hooks de Bash, escritura, MCP, cierre, correcciones e inicio de sesión.
- 21 skills, 11 playbooks, 13 principios y 6 subagentes.
