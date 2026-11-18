# Fase 0 (repetición en 0.1.1) — resultado

Sesión: reinicio con `claude --plugin-dir ./itostack` desde la raíz del repo.
Commit probado: `06cc4fe` (plan) sobre itostack 0.1.1 (`56c2920`, `80fe1fe`). Árbol limpio.
Plataforma: Windows 11 nativo, Git Bash, sin WSL. Evidencia cruda: `evidencia-011.txt`.

| ID | Función | Esperado | Observado | Estado | Evidencia |
|---|---|---|---|---|---|
| F0-01 | Mensaje del hook de inicio en el contexto | «[itostack] …» con la raíz | Presente: «[itostack] Plugin disponible (raíz: C:\Users\licjo\.harness\Harness-Itosturre\itostack). Este proyecto aún no tiene .itostack/…» | OK | contexto inicial de esta sesión |
| F0-01b | Intérprete anunciado por el hook | ruta de Python usable (= `PY`) | No se anuncia: la rama que imprime el intérprete solo corre si existe `.itostack/` (`inicio_sesion.py:36-47`). Queda pendiente hasta la fase 2 | Observación (O-01) | `inicio_sesion.py:36-47` |
| F0-10 | **Prueba en vivo del guardia Bash** | commit en inglés DENEGADO | Denegado: «itostack: commit en inglés («Add test»). Escribe commits descriptivos en español: «Agrega…», «Corrige…», «Elimina…».» | OK (denegación = éxito) | llamada Bash real de esta sesión |
| F0-02 | node ≥ 22.6 | ≥ 22.6 | v24.10.0 | OK | `node --version` |
| F0-03 | Intérprete de Python | 3.10+ usable | `python` 3.14.0 y `py -3` 3.14.0; `python3` sigue siendo el alias de la Microsoft Store | OK (ya no bloquea) | `evidencia-011.txt` |
| F0-04 | Playwright + Chromium | instalados | `node_modules/.bin/playwright` presente; `ms-playwright` con chromium-1194…1255, headless_shell y ffmpeg | OK | `ls` |
| F0-05 | pytest / hypothesis / yaml / flask | los 4 importan | pytest 9.0.1 · hypothesis 6.170.15 · yaml 6.0.3 · flask 3.1.2 | OK | `evidencia-011.txt` |
| F0-06 | bwrap y socat | presentes | ausentes (Windows nativo) | BLOQUEADO por diseño | fase 7 queda «pendiente WSL» |
| F0-07 | `claude plugin validate ./itostack` | válido | ✔ Validation passed. 1 aviso del *directorio* de plugins: falta icono (`ICON_MISSING`); no afecta el resultado | OK | salida completa |
| F0-08 | `tsc --noEmit -p .` en `itostack/scripts` | 0 errores | 0 errores (exit 0) con `./node_modules/.bin/tsc.cmd`; `npx` global sigue resolviendo un `tsc` equivocado | OK | exit 0 |

## Estado de los defectos de 0.1.0 — confirmado en vivo

- **D-01 · `import pwd` a nivel de módulo → CORREGIDO.** `nucleo/config.py:13-15` usa `try/except ImportError` con `pwd = None`, y `:115-117` lo consulta solo si existe. Importar `nucleo.config` con `python` en Windows funciona y el HOME real resuelve a `C:\Users\licjo`.
- **D-02 · Las guardias fallaban abiertas → CORREGIDO.** `hooks/lanzar.mjs` deniega cuando no puede evaluar. Medido con `ITOSTACK_PYTHON` apuntando a un ejecutable inexistente:
  - modo `cerrado` + intérprete ausente → JSON con `permissionDecision: "deny"` y el motivo «Falla cerrado: acción bloqueada»;
  - modo `cerrado` + hook inexistente (`no_existe.py`) → el mismo `deny`;
  - modo `abierto` (SessionStart) → deja pasar y avisa por stderr, como corresponde;
  - guardia sana con carga inocua (`ls -la`) → permite (sin salida).
- **D-03 · `python3` fijo en `hooks.json` → CORREGIDO.** `grep -c python3 hooks/hooks.json` = 0. Los 7 hooks pasan por `node "${CLAUDE_PLUGIN_ROOT}/hooks/lanzar.mjs"`, que en win32 prueba `py -3` → `python` → `python3` y descarta el alias de la Store por los códigos de salida 9009/49.

## Observaciones nuevas

- **O-01 · Baja.** La convención del plan («PY = el intérprete que anuncia el hook de inicio») no se puede cumplir antes de la fase 2: el hook solo anuncia el intérprete en proyectos que ya tienen `.itostack/`. Mientras tanto se usa `python`. Propuesta (nivel 4 · prosa): que la rama sin `.itostack/` también imprima el intérprete, o que el plan lo aclare.
- **O-02 · Informativa, con consecuencia práctica.** El guardia Bash inspecciona el **texto** del comando, no la acción. Al intentar escribir este mismo informe con un heredoc, la llamada fue denegada dos veces porque el documento *cita* comandos prohibidos (el commit en inglés y el push forzado). Consecuencias: (a) documentar una denegación desde Bash es imposible; hay que usar Write, que pasa por `guardia_escritura.py` y no evalúa comandos de git; (b) para ejercitar el camino de fallo del lanzador hay que usar cargas inocuas. No es un fallo de seguridad, pero sí una asimetría entre los dos guardias que conviene anotar junto a las brechas de la fase 5.

---

**Nota 2026-11-18 (posterior al cierre de la fase).** El operador indicó que las tablas de cierre usen rutas relativas a la raíz del repositorio en vez de rutas absolutas de `C:\Users`. Esta tabla se entregó con la ruta absoluta y **se conserva tal cual**, porque las correcciones aplican hacia adelante y un registro cerrado no se reescribe. La convención rige desde la fase 6 en adelante. (La ruta absoluta de esta celda, además, es el formato literal que imprime la herramienta.)
