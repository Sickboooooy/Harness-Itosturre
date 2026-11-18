# Fase 2 · Configuración en la raíz (perfil jurídico, modo fixture) — resultado

Comando: `python itostack/scripts/inicializar.py --proyecto . --perfil juridico --modo fixture --sjf-fixture itostack/evals/fixtures/sjf/basico.json`

| ID | Función | Esperado | Observado | Estado | Evidencia |
|---|---|---|---|---|---|
| F2-01 | `/itostack:configurar-itostack` con perfil jurídico y modo fixture | `.itostack/` creado, sin tocar CLAUDE.md | «itostack inicializado … modo: fixture · perfil: juridico», exit 0. Detectó el navegador: `chromium-1255/chrome-win64/chrome.exe` | OK | salida del script |
| F2-02 | `.itostack/config.json` en modo fixture | `modo: fixture`, perfil y ruta del fixture | `{"version":1,"perfil":"juridico","modo":"fixture","sjf":{"fixture":"…itostack\evals\fixtures\sjf\basico.json"},"navegador":{"ejecutable":"…chrome.exe"}}`. La ruta apunta a un archivo que existe (claves `tesis` y `urls`) | OK | `config.json` |
| F2-03 | `evidencia_forense.db` | almacén creado | 20 480 bytes. Tabla `verificaciones` con `CHECK (tipo IN ('tesis','url','app'))`, `CHECK (veredicto IN ('PASS','FAIL','BLOCKED'))`, `CHECK (modo_fuente IN ('real','fixture'))` y dos índices (`idx_verificaciones_busqueda`, `idx_verificaciones_clave`). 0 filas | OK | esquema en `evidencia.txt` |
| F2-04 | `raiz_plugin` | ruta de la raíz del plugin | `C:\Users\licjo\.harness\Harness-Itosturre\itostack` | OK | `cat` |
| F2-05 | `mejora/` | carpeta con las bitácoras de corrección | `mejora/correcciones.tsv` (cabecera `fecha sesion clave extracto`), `mejora/elevaciones.tsv` (`fecha clave nivel artefacto descripcion`), `mejora/reportes/` vacía | OK | `head -1` de cada TSV |
| F2-06 | `bitacora/` | carpeta creada | presente y vacía (se llena con `/muestra-tu-trabajo`, fase 6) | OK | `ls` |
| F2-07 | `evidencia/` | carpeta del almacén de capturas | presente y vacía | OK | `ls` |
| F2-08 | `modelos.json` | modelo por rol | roles ejecutor/revisor/auditor_citas/reproductor/jardinero/juez_evals; panel de `/interrogar` = `revisor-adversarial` + `ollama:qwen2.5:14b`; regla «el juez no debe ser el mismo modelo que el agente evaluado» | OK | `modelos.json` |
| F2-09 | CLAUDE.md sin tocar | skip | **No existe `CLAUDE.md` en la raíz**: no había nada que editar. El script solo sugirió la línea `@.itostack/CLAUDE.itostack.md`; no se agregó. La plantilla `CLAUDE.itostack.md` sí se generó | OK (skip) | `test -f CLAUDE.md` → NO |
| F2-10 | Hook de inicio invocado a mano | «Harness activo» y «MODO FIXTURE» | Ambas presentes. Salida completa en `evidencia.txt`: «[itostack] Harness activo · raíz del plugin: …\itostack · modo: fixture.» … «MODO FIXTURE: la evidencia usa datos ficticios y no sirve para uso procesal.» | OK | `node itostack/hooks/lanzar.mjs inicio_sesion.py abierto SessionStart` |
| F2-11 | Árbol de git limpio | `.itostack/` no ensucia el repo | `git status --porcelain` vacío. `git check-ignore -v` confirma que lo ignora `.gitignore:8 (.itostack/)` del propio repo, además del `.gitignore` interno que excluye `evidencia/`, `*.db`, `raiz_plugin`, `app.json` | OK | `git check-ignore -v` |

## O-01 resuelta: `PY` queda definido

El hook de inicio, ya con `.itostack/` presente, anuncia:

    Intérprete de Python que funciona aquí: "C:/Python314/python.exe"

Coincide con `python` del PATH (`which python` → `/c/Python314/python`, `sys.executable` → `C:\Python314\python.exe`). Por tanto **`PY` = `python`** para el resto de la campaña, que es lo que `ESTADO.md` ya venía usando. La observación O-01 de la fase 0 queda cerrada: no era un defecto, solo que el aviso llega después de configurar.

## Pasos de la skill que quedaron fuera, con su razón

- **Paso 3 (instalar Playwright):** ya instalado en la fase 0; el script no lo pidió.
- **Paso 4 (editar CLAUDE.md):** skip por instrucción del plan, y además no hay CLAUDE.md en la raíz.
- **Paso 7 (prueba de humo con un registro real):** imposible en modo fixture y por la regla 3 del plan (los datos reales los da el operador en la fase 8). El equivalente en fixture son los casos de la fase 3.
- **Paso 8 (`/crear-skill-verificacion`):** corresponde al perfil desarrollo; se ejecuta en la fase 4 sobre el proyecto anidado `pruebas-manuales/app`.

## Observación nueva

- **O-04 · Informativa.** `config.json` guarda la ruta del fixture en **absoluto y con separadores de Windows**. Funciona, pero ata el archivo a esta máquina: si el repo se moviera o se compartiera `.itostack/`, la ruta rompería. Hoy no importa porque `.itostack/` está en `.gitignore`. Propuesta (nivel 1 · diseño, si alguna vez se quiere compartir configuración): guardar la ruta relativa a la raíz del proyecto y resolverla al leer.

---

**Nota 2026-11-18 (posterior al cierre de la fase).** El operador indicó que las tablas de cierre usen rutas relativas a la raíz del repositorio en vez de rutas absolutas de `C:\Users`. Esta tabla se entregó con la ruta absoluta y **se conserva tal cual**, porque las correcciones aplican hacia adelante y un registro cerrado no se reescribe. La convención rige desde la fase 6 en adelante. (La ruta absoluta de esta celda, además, es el formato literal que imprime la herramienta.)
