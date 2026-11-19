# Estado de la campaña de pruebas de itostack (traspaso entre sesiones)

Actualizado: 2026-11-18. Sesión anterior: dc16f12d-3d29-4178-99ee-1d1f337ba2a7.

## Entorno (Windows 11 nativo, sin WSL)
- Repo: `c:\Users\licjo\.harness\Harness-Itosturre`, en 56c2920 (itostack 0.1.1), árbol limpio, `core.fileMode=false`.
- Python: usar `python` (3.14.0). `python3` es el alias de Microsoft Store (sale con 49). Usar el intérprete que anuncie el hook de inicio.
- Node v24.10.0. En Git Bash usar `npm.cmd` / `npx.cmd`.
- Donde el plan dice `/tmp`, usar `$TEMP`.
- Instalado con autorización: `npm ci` y Chromium de Playwright en `itostack/scripts`; `hypothesis` 6.170.15.
- Sin bwrap/socat: los evals nativos con Bash quedan para WSL.

## Hecho
- Fase 0 en 0.1.0: ver `fase0/resultado.md` y `fase0/evidencia.txt`. Defectos D-01 (import pwd), D-02 (guardias fallan abiertas), D-03 (`python3` fijo en hooks.json).
- **Fase 0 repetida en 0.1.1 (commit 06cc4fe): cerrada.** Ver `fase0/resultado-011.md` y `fase0/evidencia-011.txt`.
  - F0-01 OK (el hook anuncia la raíz; no el intérprete, porque falta `.itostack/` → O-01).
  - **F0-10 OK en vivo: el commit en inglés fue DENEGADO por el guardia Bash.** No hay hallazgo crítico.
  - **D-01, D-02 y D-03: corregidos en 0.1.1, confirmado con prueba propia.** El lanzador `hooks/lanzar.mjs` deniega en modo `cerrado` cuando no hay intérprete o falta el hook, y deja pasar en modo `abierto`.
  - Entorno completo: node v24.10.0 · python 3.14.0 (`python` y `py -3`) · pytest 9.0.1, hypothesis 6.170.15, yaml 6.0.3, flask 3.1.2 · Playwright con Chromium · `claude plugin validate` ✔ · `tsc --noEmit` 0 errores (usar `./node_modules/.bin/tsc.cmd`, no `npx`).
  - O-02: el guardia Bash evalúa el **texto** del comando, así que no se puede documentar un comando prohibido con heredoc; para esos archivos usar Write.

- **Fase 1 (deterministas): cerrada, 3/3 OK.** Ver `fase1/resultado.md` y `fase1/evidencia.txt`.
  - `pytest tests -q`: 98 passed, 1 skipped (`test_plataforma.py:80`, omitida por diseño en Windows).
  - `autoprueba.py`: 17/17 coherentes; referencias 1.00, rotas 0.00–0.80; los 5 holdout no tienen variante rota.
  - `lint_itosturre.py`: 0 hallazgos.
  - O-03: en Windows exportar `PYTHONUTF8=1` al correr scripts a mano (si no, la raya «—» sale como `?`).
  - Margen más estrecho de la suite: `verificar-cita/pass-advertencia-sala` (1.00 vs 0.80).

- **Fase 2 (configuración en la raíz): cerrada, 11/11 OK.** Ver `fase2/resultado.md` y `fase2/evidencia.txt`.
  - `.itostack/` creado con perfil `juridico` y modo `fixture`; fixture = `itostack/evals/fixtures/sjf/basico.json`.
  - `evidencia_forense.db` con la tabla `verificaciones` (CHECK de tipo/veredicto/modo_fuente) y 0 filas; `raiz_plugin`, `mejora/` (2 TSV con cabecera), `bitacora/`, `evidencia/`, `modelos.json`.
  - Hook de inicio a mano: dice «Harness activo» y «MODO FIXTURE».
  - **O-01 cerrada: `PY` = `python` = `C:\Python314\python.exe`**, el mismo que anuncia el hook.
  - CLAUDE.md: skip. No existe en la raíz, así que no había nada que editar.
  - `.itostack/` lo ignora `.gitignore:8` del repo: el árbol sigue limpio.
  - O-04: `config.json` guarda la ruta del fixture en absoluto y con separadores de Windows (ata el archivo a esta máquina; hoy inocuo porque está ignorado).

- **Fase 3 (pilar 1 jurídico, fixture): cerrada, 21/21 ejecutados.** Ver `fase3/resultado.md`, `fase3/evidencia.txt`, `fase3/lista-de-tareas.md`, `fase3/corte-temporal-FICT-0002.md` y los dos informes VVCA.
  - Los 8 casos de `verificar-cita` dieron los veredictos esperados (3 PASS, 2 FAIL, 3 BLOCKED).
  - Capturas con franja FIXTURE; `verificar.py url` PASS/FAIL; `validar-documento` 1/1/1 y FAIL por rubro truncado en el holdout; `auditor-citas` **APROBADO** en ambos; ensamblado con `[^ev1]`/`[^ev2]`; `[[CITA:FICT-0404]]` → BLOCKED sin escribir; `evidencia_db.py auditar` → `Integridad: OK`.
  - **D-04 · CRÍTICO (sin corregir, pendiente de aprobación).** `nucleo/citas.py:19` aplica `RE_MARCA_NO_VERIFICADA` (incluye las palabras sueltas INEXISTENTE / BLOQUEAD / NO VERIFICAD / NO VERIFICABLE) a la **línea completa**, rubro entrecomillado incluido. Desactiva el control de evidencia en **dos** capas: `ensamblar_documento.py:81` y `hooks/guardia_escritura.py:61`. Reproducido en vivo: la misma cita a `salidas/` se deniega sin la palabra y **se permite** con ella. La ruta de validación (lote/informe) NO se ve afectada.
  - D-05 (media): `verificar.py:128-130` etiqueta `[real]` las filas «sin registro» en corrida fixture (por omisión literal `"real"`, no `config["modo"]`). No fabrica PASS porque `vigente()` exige PASS.
  - D-06 (media): el contrato de `modo-itosturre` exige copiar el playbook «en la lista de tareas», pero esta sesión no tiene TodoWrite. Sustituido por archivo.
  - D-07 (alta): `verificar.py tesis` no coteja el **texto** de la tesis y `formatear()` nunca lo emite → PASS certifica la transcripción del rubro, no la fidelidad de la glosa. Estructural.
  - D-08 (media): `obligatoriedad` se calcula y se guarda en `resultado.json`, pero no hay columna en el esquema → no llega al entregable.
  - D-09 (media): la nota al pie dice «Verificado en el portal oficial» también en fixture.
  - B-01 (brecha): `corte-temporal` manda buscar criterios posteriores en el SJF; no existe subcomando de búsqueda. Todo análisis termina en ⚠.
  - O-05: la franja FIXTURE solo se inyecta en HTML; `api.png` no la lleva.
  - Fortalezas confirmadas: falla cerrado, fallo visible en el cuerpo, almacén append-only con triggers que abortan UPDATE y DELETE, corte temporal con filtro por materia correcto.

- **Fase 4 (pilar 1 desarrollo): cerrada, 11/11 OK.** Ver `fase4/resultado.md`, `fase4/evidencia.txt`, `fase4/evidencia-2.txt`.
  - App en `pruebas-manuales/app` (perfil desarrollo, modo real). Corregida ahí y solo ahí: `app.py:14` → `registro.upper()`, más la prueba `test_registro_en_minusculas_se_valida_igual`. 2 passed.
  - `demuestra-que-funciona`: PASS (mayúsculas), BLOCKED (selector `boton-historial` inexistente, sin implementarlo), FAIL (minúsculas). `app.json` desaparece al detener; la evidencia sobrevive.
  - `reproductor`: 4 veredictos en 2 corridas, capturas de fallo byte-idénticas. `agente-itosturre`: PASS con el mismo motivo textual.
  - Skill del proyecto creada en `pruebas-manuales/app/.claude/skills/verificar-app-simulada/SKILL.md`; autoprueba 6/6 (tras dos rondas de corrección).
  - **D-11 · media-alta.** `arrancar_app.py iniciar` muere con traceback si falla el sondeo de salud, **dejando un servidor huérfano** que `detener` no puede matar (no alcanzó a escribir `app.json`). Comprobado con netstat y Get-CimInstance; eliminado con Stop-Process. Propuesta: try/except, matar al hijo y emitir BLOCKED.
  - **D-10 · media.** `lint_itosturre.py --diff` aprobó **en vacío**: `git diff` no ve archivos ignorados **ni archivos nuevos sin rastrear**, así que la compuerta del paso 6 de `reproducir-y-corregir` puede pasar sin examinar nada. Propuesta: reportar archivos/líneas examinados e incluir los no rastreados.
  - O-07 (baja): `final.png` es byte-idéntico a la captura anterior en cada corrida.
  - E-01 (entorno): en Git Bash, MSYS convierte un `/` suelto en `C:/Program Files/Git/`. Afecta a `--salud /` y a banderas tipo `tasklist /FI`. Remedio: omitirlo, `MSYS_NO_PATHCONV=1`, o PowerShell.
  - **Corrección al plan:** SÍ hay remoto (`origin https://github.com/Sickboooooy/harness-itosturre`). El PR sigue en skip, pero porque `pruebas-manuales/` está excluido del repo y la regla 5 prohíbe commits y push.

- **Fase 5 (pilar 4 guardrails): cerrada.** Ver `fase5/resultado.md` y `fase5/evidencia.txt`.
  - Bash: 8/8 denegaciones esperadas. Write/Edit: 4 deny y 3 permitidos, todos correctos. MCP: deny en vivo con cita sin evidencia.
  - **B-02 · alta.** `git push --dry-run origin main` **se ejecutó sin preguntar**. El guardia sí emite `ask` (`guardia_bash.py:27`, verificado a mano); el anfitrión lo resolvió a permitir. No hay settings del proyecto y ninguna de las 21 reglas allow globales cubre git; `defaultMode` = None. De las 13 reglas del guardia, 11 son `denegar` (exigibles) y **2 son `preguntar`** — ambas sobre push a la rama compartida. Afecta también a `guardia_externo.py`, cuya compuerta humana es un `preguntar` único.
  - **F5-18 no se disparó** (skip razonado, en bitácora): con `ask` auto-aprobándose, la llamada MCP habría enviado un correo real al operador sin confirmación. Veredicto acreditado por simulación del guardia.
  - Brechas: (1) Bash elude el guardia de escritura, pero el lint detecta los 8 códigos IT (13 hallazgos); (2) alterar un byte de una captura → `huella alterada`, restaurada → `Integridad: OK`; (3) `lint --diff` → 0 hallazgos con 13 violaciones reales en disco (demostración directa de D-10); (4) censo del `jardinero` sobre `itostack/scripts`: lint 0 hallazgos y categorías limpias confirmadas, más 8 patrones no cubiertos.
  - **D-12 · media.** La `ADVERTENCIA_FIJA` impresa al pie de todo entregable jurídico (copiada en `ensamblar_documento.py:27` y `reporte_vvca.py:25`) remite a `sjf.scjn.gob.mx`, mientras `dominios_oficiales` y `verificador_fuente.ts` tienen por canónico `sjf2.scjn.gob.mx`. Ya materializado en `salidas/parrafo.md` e `informe-vvca.md`.
  - Archivos de prueba dejados en disco a propósito: `pruebas-manuales/reglas.py`, `reglas.ts` (13 violaciones IT), `salidas/prueba-guardia*.md`, `salidas/sonda-*.md`, `borradores/sonda-*.md`.

- **Fase 6 (pilar 3 mejora continua): cerrada salvo F6-07.** Ver `fase6/resultado.md`, `fase6/correcciones-del-operador.md`, `fase6/palanca-candidata.md`.
  - Hicieron falta **tres** correcciones del operador para lograr dos filas con la misma clave. La segunda (redactada con calma) no se registró.
  - **D-13 · alta.** `captura_correcciones.py:21-26` solo detecta el registro confrontativo («no» al inicio, «te dije», «otra vez», «nunca escribas»…). Una corrección cortés es invisible al bucle de mejora. Medido ejecutando el módulo real.
  - **D-14 · media.** `clave()` agrupa por las 5 primeras palabras de contenido: 4 paráfrasis de la misma corrección → 4 claves distintas. El umbral n≥2 solo se alcanza repitiendo casi literal.
  - **D-15 · media.** `salud_rutinas.py` suma `cache_read_input_tokens` (contexto releído por turno → 126 M en una sesión) y atribuye por skill de forma pegajosa (todo lo posterior se carga a la última skill invocada). El ranking de «consumo por skill» no es utilizable para decidir dónde invertir.
  - `/corregir`: propuesta **nivel 2** (IT009 en lint + guardia de escritura) en `.itostack/mejora/propuesta.md`. **Sin aplicar, espera aprobación.**
  - `muestra-tu-trabajo`: reversible exit 0, irreversible exit 3 con detención, acatada. `sin-relleno`: 9 hallazgos → LIMPIO en una poda, conservando las fórmulas forenses.
  - `construir-palanca`: candidato = el preámbulo `cd … && R=$(cat raiz_plugin) && PYTHONUTF8=1 python "$R/scripts/…"`, 38 repeticiones medidas. Sin escribir código.
  - Ollama ausente → `revisar_ollama.py` en skip, con su fallo cerrado verificado (exit 2 sin servidor; exit 3 y rechazo ante endpoint remoto).
  - **Pendiente de decisión del operador (F6-07):** repetir o no `revisor-adversarial` sobre `salidas/parrafo.md`, ya revisado en la fase 3 (E7). Costo estimado 45–55 k tokens, sin información nueva esperable.

- **Fase 7 (pilar 2 evals): cerrada salvo los evals nativos.** Ver `fase7/resultado.md`, `fase7/mejorar-skill-en-seco.md`, `fase7/juez-evals-informe-vvca.md`, `fase7/falso-positivo-pass-advertencia-sala.md`.
  - F7-01…04: caso `verificar-cita/fail-epoca-discrepante` creado (4 archivos), autoprueba **1.00 / 0.50**, suite **18/18**, sin commit. Antes de escribirlo verifiqué que una época discrepante sí da FAIL.
  - F7-05: `mejorar-skill` en seco. La corrección iría al **formato del reporte** (campo obligatorio «Cotejo que falló»), nivel 1, no a prosa. Crear el caso nuevo ya invalidó cualquier congelado: la huella incluye `evals/verificar-cita/` entero. Huella actual `50e62b1c947a4939…`; `estado` sin candidatas.
  - F7-06: `juez-evals` devolvió 10/10 y «cumplimiento completo». Calificación correcta: 5 cumplidos, **1 no aplicable**, 0 fallos críticos. El criterio 4 (advertencias de corte temporal) no es ejercitable en ese informe: tiene 0 de esas advertencias porque ninguna de sus citas las dispara; sí lo es en `fase3/informe-vvca-holdout.md`, que tiene 7.
  - **D-17 · nivel 1 · defecto de la DEFINICIÓN del agente, no del juez** (atribución corregida por el operador; ver la nota fechada al pie de `fase7/juez-evals-informe-vvca.md`). La última línea de `itostack/agents/juez-evals.md` impone `{"puntaje": 0-10, "criterios": [{..., "cumple": true|false, ...}]}`: el 10 es obligatorio sobre una rúbrica binaria, y con un booleano «no aplica» es irrepresentable aunque se le pida. Error propio del juez, más acotado: la evidencia que citó para el criterio 4 (marca de fixture y pie de IA) no corresponde a ese criterio. Propuesta: `"cumple": "si"|"no"|"no_aplicable"` y puntaje coherente con rúbricas binarias.
  - **D-16 (reportado por el operador, registrado SIN corregir):** el grader `explica-contexto` de `pass-advertencia-sala` busca `sala` sin delimitadores y lo encuentra dentro de «ú**sala**» en el mensaje de `referencia_rota.sh` (`✅ VERIFICADO, úsala sin reservas.`). Explica el 0.80 anómalo que se venía señalando desde la fase 1. Nivel 3 (falla el instrumento, no el producto). El operador lo corrige en 0.1.2.
  - F7-07: evals nativos con `claude plugin eval` **pendientes de WSL** (sin bubblewrap ni socat).
  - F6-07 (`/interrogar`): **saltado por decisión del operador**.

## F-PUSH · commit y push autorizados por el operador (2026-11-18)

Excepción expresa a la regla 5 del plan. Commit `bfd1ee1`, push a `main` aceptado: `06cc4fe..bfd1ee1`.

- **El push NO pidió confirmación. B-02 queda CONFIRMADO en vivo, y esta vez sobre un push real, no un `--dry-run`.** La regla `guardia_bash.py:27` (`\bgit\s+push\b[^|;&]*\b(?:main|master)\b`) debía emitir `ask`; el comando se ejecutó sin que apareciera ninguna compuerta. Es la segunda medición del mismo defecto (la primera, F5-04, fue con `--dry-run`): el nivel `preguntar` del guardia no protege nada en esta sesión, ni siquiera ante una escritura real a la rama compartida de un repositorio remoto.
- El commit en español y descriptivo **sí** pasó el guardia de Bash sin objeción, como corresponde.
- Contenido: 48 archivos, 2584 inserciones, **0 modificaciones y 0 borrados** de archivos preexistentes. Bajo `itostack/` solo los 4 archivos del caso nuevo.
- **Excluido deliberadamente** (97 archivos de estado de máquina): `pruebas-manuales/app/.itostack/` completo —con `evidencia_forense.db` y 39 capturas PNG—, `__pycache__/`, `.pytest_cache/`, `app.log` y `raiz_plugin`. El propio `.itostack/.gitignore` declara esa intención. Sin credenciales ni tokens (barrido de `ghp_`, `sk-ant`, claves privadas y asignaciones de `token`/`password`/`secret`: sin coincidencias).
- **Premisa del operador corregida:** `06cc4fe` ya estaba en local y era el HEAD; el remoto estaba exactamente ahí. `git pull --rebase` respondió «Current branch main is up to date»: no hubo divergencia ni conflicto que resolver.
- `pruebas-manuales/` y `salidas/` siguen listados en `.git/info/exclude:7,9`. Ya no afecta a los 48 archivos ahora rastreados, pero **cualquier archivo NUEVO en esas carpetas seguirá invisible para `git status`** — relevante para la fase 8 y para `INFORME-PRUEBAS.md`.
- **Aviso del remoto:** «This repository moved. Please use the new location: https://github.com/Sickboooooy/Harness-Itosturre.git». La URL de `origin` conserva la grafía antigua en minúsculas y GitHub está redirigiendo. Conviene actualizarla; no se tocó.

## F-CODEX · auditoría cruzada con Codex e itostack 0.1.2 (2026-11-18)

Autorizado por el operador («haz el resto de cambios y usa Codex para mejorar el Harness de acuerdo al plan»), que antes modificó `privacidad-local.md`: la regla de que los datos no salen de la máquina aplica solo en producción. Detalle completo en `fase-codex/resultado.md`.

- **Codex como juez y revisor de otra familia** (`gpt-6.1-sol`, codex-cli 0.167.0-alpha.3.2, sesión ChatGPT ya iniciada; Ollama sigue sin instalar). `scripts/revisar_codex.py` corre solo con `"entorno": "desarrollo"`: se declaró en `.itostack/config.json` de la raíz (ignorado por git), y `modelos.json` de la raíz apunta al juez Codex.
- **F7-06 repetida con Codex**: 5 cumplidos + criterio 4 `no_aplicable`, con la razón correcta. Es la calificación verificada a mano; `juez-evals` (Haiku) había dado 10/10.
- **Auditoría de Codex contra el plan** (solo lectura): 15 hallazgos confirmados en el código, 5 conocidos (D-04, D-07, D-10, D-13, B-02) y 10 nuevos (N-01 a N-10).
- **Corregidos en 0.1.2**: D-04, N-01, N-07, N-09, B-02 (en lo medido), D-10, D-16, D-17; N-08 parcial.
- **Revisión adversarial de Codex sobre el diff, ronda 1**: «rechazar», 11 hallazgos. Corregidos en una segunda ronda: juez sin herramientas, cobertura exacta de la rúbrica, material excedido = BLOCKED, reserva antes del holdout, veredictos atados a rúbrica y artefactos con bitácora del juez, no re-congelar, marcas por segmento y referencia, rubro declarado sin comillas, endpoint de Ollama, Grep sobre `evals/`, `node_modules`.
- **Prueba en vivo del aislamiento del juez**: un artefacto le ordenó leer un archivo secreto fuera del directorio neutro. El contenido no aparece en la salida (0 coincidencias) y Codex marcó la instrucción como inyección. Esa salida no distingue «sin herramienta» de «se negó».
- **Revisión adversarial de Codex, ronda 2**: «rechazar», 16 hallazgos; confirma las correcciones de la ronda 1. Corregidos en una tercera ronda (detalle en `fase-codex/resultado.md`).
- **Revisión adversarial de Codex, ronda 3**: «rechazar», 14 hallazgos (6 altos, más finos). Corregidos en una cuarta ronda.
- **Verificación**: `pytest tests -q` 242 passed, 1 skipped (`test_auditoria_codex.py`: 144). `autoprueba.py` 18/18. Lint 0 hallazgos. `lint --diff` 0 hallazgos en 18 archivos. `tsc` 0 errores.
- **Pendientes de diseño** (propuestas de Codex en `fase-codex/auditoria-codex.json`): N-02, N-03, N-04, N-05, N-06, D-07, D-13, N-10; la separación física de la reserva holdout (N-08), y un ejecutor con autorización humana vinculada al comando exacto (B-02).
- **Cambio de comportamiento a tener presente**: en una sesión en modo auto, dontAsk o bypassPermissions, un push a `main`/`master` y los envíos MCP ahora se DENIEGAN (antes «preguntaban» y el anfitrión los aprobaba solo). Para responder por Telegram u otra salida curada, agregarla a `acciones_externas_permitidas`.
- Sin commit ni push.

### Cierre de 0.1.2 por invariantes (2026-11-19)

El operador suspendió el ciclo de revisiones después de la ronda 4 de Codex (10 hallazgos) y ordenó cerrar 0.1.2 demostrando invariantes. Detalle en `fase-codex/diagnostico-ronda4.md` (secciones 1 a 6).

- **Diagnóstico:** los 10 hallazgos se reprodujeron. Tres causas raíz (CR-1 citas en prosa, CR-2 reserva en el árbol de trabajo, CR-3 compuerta que confía en archivos entregados) cubren 9; el décimo (CR-4) era una dependencia falsa.
- **Cambios de código del cierre:**
  - R4-10, resuelto en la compuerta consumidora (contrato único, sin valores por omisión que aprueben; BLOCKED no decide ni consume el intento).
  - CR-4, revertido después de comprobarlo con el andamiaje real.
  - `puntajes` ya no lanza con resultados mal formados.
  - Prueba nueva de que Ollama no sigue redirecciones; `jsonschema` como dependencia de desarrollo.
- **Evidencia:**
  - `fase-codex/matriz-invariantes.md`, generada por script;
  - `fase-codex/mutantes-cierre.txt`;
  - `fase-codex/bateria-cierre.txt`;
  - `fase-codex/evidencia-vivo/` (I-1 y I-3 en vivo; solo los informes JSON se versionan, no las capturas crudas de las sesiones).
- **Estado:**
  - Demostrados: I-1, I-2, I-3, I-4, I-6, I-11.
  - Parciales: I-7 (falta la procedencia), I-9, I-10.
  - No demostrados: I-5, I-8.
  - Todo está en «Límites conocidos» del CHANGELOG.
- **Los casos `holdout-*` actuales están quemados.** Los escribió el agente y están en dos commits de la historia de Git. Un ACEPTADA de 0.1.2 no demuestra generalización.
- **Diseño de 0.2.0:** `itostack/docs/diseno-0.2.0.md`, con CR-1, CR-2 y CR-3, sus criterios de aceptación A1 a A3 y la secuencia recomendada. Sin implementar.
- **Pendiente del operador:** autorizar un commit en una rama, y decidir si arranca CR-1 y el spike de WSL. Sin commit ni push.

## F-0.2.0 · inicio de itostack 0.2.0 (2026-11-19)

Autorizado por el operador: cerrar 0.1.2 en una rama de release, crear `dev/itostack-0.2.0`, iniciar CR-1, hacer una exploración mínima de `claude plugin eval` y preparar el contrato de CR-3. CR-2 solo se diseña (modelo de amenazas para aprobación). No se corren holdouts.

- **Release 0.1.2:** commit local `7933f35` en `release/itostack-0.1.2-experimental`, con la evidencia seleccionada (`git add -f`). Sin push ni merge.
- **CR-1.1** (contrato `itostack/citas@1`): PASS. 17 pruebas por propiedades y 11/11 mutantes (`fase-0.2.0/mutantes-cr1.txt`); `test_flujos` y la autoprueba de `redactar-con-citas` siguen en verde. Las propiedades encontraron dos huecos del detector de texto libre, que se aplicaron a la alarma: un registro o una marca pegados a otra palabra no se detectaban por las anclas de palabra.
- **Reserva contaminada:** `itostack/evals/reserva.json`; `reservar` y `holdout` se niegan. 3/3 mutantes.
- **Exploración de `claude plugin eval`:** WSL sin distribución, así que se hizo en Windows nativo, y la corrida quedó bloqueada (`~/.aws` de 22 GB). Hallazgos en `fase-0.2.0/exploracion-plugin-eval.md`. El más serio: con `--keep-temp`, el temporal tenía una unión a `~/.aws/sso` real; se quitó sin seguirla y las credenciales quedaron intactas.
- **Contrato de CR-3:** `itostack/docs/contrato-cr3.md` y `evals/esquemas/`, con 18 pruebas de conformidad contra dos salidas reales.
- **CR-2:** `itostack/docs/cr2-modelo-amenazas.md`, esperando aprobación. Recomienda O3: una cuenta local de Windows con su propia distribución WSL. Un usuario Linux dentro de la distribución del operador no aísla, porque `wsl -u root` lo atraviesa.
- **Sin commit en la rama de desarrollo**: falta autorización.

### Decisiones del operador y CR-1.2 (2026-11-19, segunda parte)

- **Commit local `97f3c54`** en `dev/itostack-0.2.0` (CR-1.1 y su documentación, la reserva contaminada, el contrato de CR-3 y el modelo de amenazas). Sin push.
- **CR-1.2: PASS.** Comprobación de entrega estricta y reverificada contra las fuentes vivas, conectada a los hooks de escritura, cierre y MCP. Informe VVCA con procedencia literal; skills, plantilla y evals migrados.
  - Mutantes: CR-1.2 21/21 y CR-1.1 11/11.
  - Batería: PASS (`fase-0.2.0/bateria-cr12.txt`).
- **Hallazgos del propio trabajo:**
  1. Una propiedad nueva encontró que la comprobación de entrega **lanzaba una excepción** (`KeyError`, `TypeError`) con manifiestos mal formados, en vez de dar BLOCKED. Corregido, y lo cubre una propiedad que garantiza «nunca lanza».
  2. Un manifiesto al que le faltaba el tramo de una cita en forma «rubro» pasaba, porque su texto no dispara la alarma. Corregido con una regla de coherencia de las notas `[^evN]`.
  3. La gramática admitía `[` dentro de los argumentos y dejaba pasar `[[` anidados. Corregido.
  4. **En el laboratorio:** sin `node`, todas las guardias fallaban abiertas. Corregido y probado.
- **CR-2:** el operador eligió una VM o un CI aislados. Diseño y criterios X1 a X10 en `itostack/docs/cr2-ejecutor-aislado.md`. Sin aprovisionar.
- **Laboratorio WSL:** `itostack-lab` instalado y detenido, sin credenciales; procedimiento y hallazgos en `fase-0.2.0/laboratorio-wsl.md`. La corrida exitosa necesita una credencial (decisión del operador).
- **Por error leí con `grep` líneas de un caso `holdout-*`** (`validar-documento`). Ya estaba clasificado como contaminado, así que su estado no cambia. Desde entonces las búsquedas excluyen `holdout-*`.
- **Sin commit de CR-1.2**: falta autorización.

## Siguiente
- Fase 8 (SJF y DOF reales). **Bloqueada esperando al operador**: hace falta un registro digital real con su rubro literal del SJF, y una URL del DOF con un fragmento literal de su texto. La regla 3 del plan prohíbe buscarlos o proponerlos.
- Luego, fase 9: `pruebas-manuales/INFORME-PRUEBAS.md` con la matriz completa, los defectos por gravedad y las 3 correcciones prioritarias.

## Instrucciones vigentes del usuario (tras el reinicio con `claude --plugin-dir ./itostack`)
4. Repetir F0-01 y F0-10 y probar un hook en vivo: `git commit --dry-run -m "Add test"` debe ser DENEGADO. Si no se deniega: detenerse, hallazgo crítico.
5. `python3` → intérprete del hook de inicio; `/tmp` → `$TEMP`.
6. Ejecutar fases 1 a 6 y la 8. De la fase 7 solo `autoprueba.py` (evals nativos con Bash irán en WSL).
7. Marcar D-01 a D-03 como «corregidos en 0.1.1» solo con prueba en vivo propia y su evidencia.

## Reglas permanentes del plan
- No modificar `itostack/` salvo que una fase lo pida. Defectos: evidencia, causa probable, propuesta con nivel de la pirámide. Corregir solo con aprobación, después del informe.
- Denegación de un hook = ÉXITO esperado. No evadir hooks salvo que un paso mida una brecha.
- Solo datos FICT-#### en modo fixture; los reales los da el usuario en la fase 8.
- Por fases: tabla (ID · función · esperado · observado · OK/DEFECTO/BLOQUEADO · evidencia) y esperar «continúa».
- Salidas solo en `pruebas-manuales/`, `salidas/`, `borradores/`, `.itostack/`. Sin commits ni push. Español.
