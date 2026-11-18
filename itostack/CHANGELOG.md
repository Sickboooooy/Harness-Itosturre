# Cambios

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
