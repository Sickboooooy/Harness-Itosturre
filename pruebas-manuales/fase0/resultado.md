# Fase 0 · Entorno — resultado

Plataforma: Windows 11 nativo (Git Bash), sin distribución WSL. Repo extraído de `Harness-Itosturre-v0.1.0.zip` en `c:\Users\licjo\.harness\Harness-Itosturre` (commit 34603cd). Evidencia cruda: `evidencia.txt`.

| ID | Función | Esperado | Observado | Estado | Evidencia |
|---|---|---|---|---|---|
| F0-01 | Mensaje del hook de inicio en el contexto | «[itostack] …» con la raíz del plugin | Ausente. itostack no está instalado (solo `telegram`) | BLOQUEADO | `claude plugin list` |
| F0-02 | node ≥ 22.6 | ≥ 22.6 | v24.10.0 | OK | `node --version` |
| F0-03 | python3 ≥ 3.10 | `python3` funcional | `python3` = alias de Microsoft Store (exit 49); `python` = 3.14.0 | DEFECTO (D-03) | evidencia.txt |
| F0-04 | Playwright en `itostack/scripts/node_modules` | instalado | no existe `node_modules` | BLOQUEADO | `ls` |
| F0-05 | pytest / hypothesis / yaml / flask | los 4 importan | pytest 9.0.1, yaml 6.0.3, flask 3.1.2; falta hypothesis | BLOQUEADO (parcial) | evidencia.txt |
| F0-06 | bwrap y socat | presentes | ausentes (Windows, no aplica) | BLOQUEADO | `command -v` |
| F0-07 | `claude plugin validate ./itostack` | válido | Validation passed (también el marketplace) | OK | evidencia.txt |
| F0-08 | `npx tsc --noEmit -p .` | 0 errores | no ejecutable: sin node_modules, npx resuelve un `tsc` global equivocado | BLOQUEADO | salida «This is not the tsc command you are looking for» |
| F0-09 | Exclusiones en `.git/info/exclude` | 3 líneas agregadas | agregadas | OK | `tail -4 .git/info/exclude` |
| F0-10 | Hooks ejecutables en esta plataforma | deny con exit 2 o JSON | `python3` → exit 49; `python` → exit 1 (ImportError `pwd`) | DEFECTO (D-01, D-02) | evidencia.txt |
| F0-11 | Árbol limpio tras extraer | sin cambios | 47 `.sh` con cambio de modo (pierden +x), 0 líneas | Observación | `git diff --stat` |

## Defectos

- **D-01 · Crítica (Windows).** `itostack/scripts/nucleo/config.py:9` importa `pwd` a nivel de módulo (lo usa en :112 para el HOME real). En Windows todo el núcleo falla al importarse: hooks, `verificar.py`, `inicializar.py`, `evidencia_db.py` y pruebas. La CI solo corre en `ubuntu-24.04`, por eso no se detectó. Propuesta: import condicional con respaldo `Path.home()`; para que no regrese, **nivel 3 · Verificación**: agregar `windows-latest` a la matriz de `.github/workflows/pruebas.yml`.
- **D-02 · Crítica.** Las guardias fallan **abiertas**: si un hook revienta, sale con código ≠ 2 y Claude Code lo trata como error no bloqueante; la herramienta se ejecuta. Medido: `guardia_bash.py` ante `git push --force origin main` sale con 1, no con 2. Contradice «Falla cerrado» del contrato de veredictos. Propuesta: **nivel 1 · Diseño**, un envoltorio común que capture cualquier excepción en los guardias PreToolUse y responda deny (exit 2).
- **D-03 · Alta (Windows).** `hooks/hooks.json` fija `python3` en los 7 comandos (70 archivos lo mencionan). En Windows con el alias de la Store sale con 49 y, por D-02, las guardias quedan abiertas. Propuesta: **nivel 1 · Diseño**, un lanzador que resuelva el intérprete (`python3` → `python` → `py -3`), más **nivel 4 · Prosa**: declarar plataformas soportadas en el README.
