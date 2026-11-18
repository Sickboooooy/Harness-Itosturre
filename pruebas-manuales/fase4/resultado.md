# Fase 4 · Pilar 1 desarrollo (proyecto anidado) — resultado

Proyecto: `pruebas-manuales/app`, copia de `itostack/evals/fixtures/app_flask_simulada`, perfil `desarrollo`, modo `real`. `PY` = `python`. Evidencia cruda: `evidencia.txt` (F4-01…06) y `evidencia-2.txt` (F4-07…10).

| ID | Función | Esperado | Observado | Estado |
|---|---|---|---|---|
| F4-01 | Copia + `inicializar.py --perfil desarrollo` | `.itostack/` en el proyecto anidado | «modo: real · perfil: desarrollo», navegador detectado, exit 0 | OK |
| F4-02 | `mapa_rutas_flask.py .` | rutas y selectores reales | `/` GET `inicio` (`app.py:18`), `/validar` POST `validar` (`app.py:23`); 3 `data-testid`. Coincide con el código | OK |
| F4-03 | `demuestra-que-funciona` · validar-mayusculas | PASS | `PASS`. Abrí `resultado.png`: campo con `FICT-0001` y «Resultado: VERIFICADO» | OK |
| F4-04 | `data-testid=boton-historial` | BLOCKED, sin implementarlo | `BLOCKED` «selector ausente», exit 2, con `fallo-paso-2.png`. Confirmado antes por `grep` e inventario que no existe. No se implementó nada | OK |
| F4-05 | validar-minusculas, solo verificar | FAIL | `FAIL` en «paso 4 (esperar_texto)», exit 1. Sin corregir en este punto | OK |
| F4-06 | Limpieza y supervivencia | sin `app.json`, evidencia viva | `app.json` desaparece al detener; sobreviven 3 `resultado.json` y 9 capturas | OK |
| F4-07 | Subagente `reproductor`: reproducción doble | 2 FAIL | 4 veredictos en 2 corridas con puertos y procesos distintos; las dos `fallo-paso-4.png` **byte-idénticas**. Divergencia en `app.py:14`, que verifiqué yo con `cat -n` | OK |
| F4-08 | `reproducir-y-corregir` + `tdd` | prueba roja → corrección → verde → ruta PASS | Prueba falla por la razón correcta; corrección de un token; 2 passed; `validar-minusculas` PASS sin regresión en mayúsculas | OK con defecto en la compuerta (D-10) |
| F4-09 | `crear-skill-verificacion` | SKILL.md + autoprueba de 6 pasos | Falló 1/6 en la primera vuelta (D-11); corregida la skill, **6/6** en la segunda | OK (la autoprueba cumplió su función) |
| F4-10 | `mantener-skill-verificacion` | ruta con selector inexistente → BLOCKED | `BLOCKED` por selector ausente; aplicada la resta: entrada y `rutas/ver-historial.json` eliminadas | OK |
| F4-11 | Subagente `agente-itosturre` sobre validar-mayusculas | reporte comparable al mío | **PASS**, mismo motivo textual, SHA-256 recalculados desde disco, 3 huecos útiles de la skill | OK |

## Comparación con el reporte del `agente-itosturre` (F4-11)

Coincidimos en lo esencial: mismo veredicto `PASS`, mismo motivo literal («la ruta del mapa se recorrió completa sobre la app en ejecución»), misma ruta, los 5 pasos en `ok: true`, sin errores de consola. Abrió la captura en vez de confiar en el hash, y dijo explícitamente que no leyó `app.py`: la afirmación descansa en lo observado.

Aportó tres cosas que yo no había puesto en la skill, las tres correctas y las tres ya corregidas:

1. **Falta un chequeo previo de app viva.** Mi paso 1 iba directo a `iniciar`. Él encontró un `app.log` de una corrida anterior sin `app.json` —el huérfano de D-11— y tuvo que decidir por su cuenta correr `estado` primero. Agregado al paso 1, junto con cómo detectar y matar un huérfano.
2. **`sha256_resultado` no es el hash del archivo.** Recalculó `sha256sum resultado.json` y le dio distinto del que imprime el verificador. Es correcto por diseño (huella canónica autorreferente, lo mismo que verifiqué en la fase 3), pero un auditor que lo recompute creerá que la evidencia fue alterada. Documentado en el paso 4.
3. **`final.png` es byte-idéntico a `resultado.png`.** Comprobado: ambos `439c1120eb045721…`, 15 443 bytes. No es confirmación independiente. Documentado, y anotado como O-07.

Tras las tres correcciones repetí la autoprueba completa: **6/6 otra vez**, con `Integridad: OK`.

---

# Defectos encontrados en esta fase

## D-11 · Media-alta — un arranque fallido deja un servidor huérfano que el harness no puede detener

**Qué pasa.** `arrancar_app.py iniciar` lanza el proceso de la app y después sondea la ruta de salud. Si ese sondeo lanza una excepción, el script muere con **traceback** —ni PASS, ni FAIL, ni BLOCKED— **antes** de escribir `.itostack/app.json`. El servidor ya está vivo, pero `arrancar_app.py detener` depende de ese archivo, así que no puede matarlo.

**Reproducción.** En Git Bash, `--salud /` basta: MSYS convierte el `/` suelto en `C:/Program Files/Git/`, la URL queda inválida y `urllib` lanza `http.client.InvalidURL` en `arrancar_app.py:65` (llamado desde `:86`).

**Evidencia del huérfano.**

```
.itostack/app.json  -> no existe
.itostack/app.log   ->  * Running on http://127.0.0.1:50344
urlopen(http://127.0.0.1:50344/)        -> HTTP 200
netstat -ano -p TCP | grep 50344        -> 127.0.0.1:50344  LISTENING  380
Get-CimInstance Win32_Process Id=380    -> python.exe · python -m flask --app app run --port 50344
```

Eliminado a mano con `Stop-Process -Id 380 -Force`.

**Por qué importa.** No es solo cosmético: cada arranque fallido filtra un servidor vivo que retiene un puerto, y el harness no ofrece forma de recuperarlo. Además contradice su propio contrato: una herramienta del harness debe terminar en PASS/FAIL/BLOCKED, no en traceback. La causa inmediata (la conversión de rutas de MSYS) es del entorno, pero cualquier excepción durante el sondeo produce el mismo resultado.

**Propuesta (sin aplicar).** Nivel 1 · diseño: envolver el sondeo en `try/except`, y en caso de fallo matar el proceso hijo y emitir `BLOCKED` con el motivo. Nivel 3 · prueba: un caso que fuerce una ruta de salud inválida y verifique que no queda proceso escuchando.

## D-10 · Media — `lint_itosturre.py --diff` aprueba en vacío y no se distingue de aprobar de verdad

**Qué pasa.** El paso 6 de `reproducir-y-corregir` prescribe `lint_itosturre.py --diff`. En este trabajo imprimió `lint itosturre: 0 hallazgo(s)` con exit 0 **sin haber examinado una sola línea**: `revisar_diff()` (`lint_itosturre.py:148-149`) parsea la salida de `git diff -U0 BASE`, y aquí `git diff` no devuelve nada porque `pruebas-manuales/` está excluido (`.git/info/exclude:9`).

**Alcance mayor que este caso.** `git diff HEAD` **no incluye archivos sin rastrear**. Un archivo nuevo creado por un agente —el caso más común al agregar una funcionalidad— es invisible para esta compuerta incluso en un repositorio normal, sin exclusiones de por medio. El lint sí funciona cuando se le pasan rutas explícitas: con `app.py tests/test_app.py` examinó los archivos y dio 0 hallazgos reales (la corrección está limpia).

**Por qué importa.** Un `0 hallazgos` con exit 0 significa hoy dos cosas incompatibles: «revisé y está limpio» y «no revisé nada». La compuerta no distingue, y quien la lee concluye lo primero.

**Propuesta (sin aplicar).** Nivel 1 · diseño: reportar cuántos archivos y líneas se examinaron («0 archivos examinados» es un resultado distinto de «0 hallazgos»), e incluir los archivos sin rastrear vía `git ls-files --others --exclude-standard`. Nivel 4 · prosa: que el paso 6 de la skill diga que, fuera de un árbol rastreado, hay que pasar las rutas explícitamente.

## O-07 · Baja — `final.png` duplica la captura anterior

Cada corrida guarda `final.png` byte-idéntico a la última captura: `resultado.png` cuando pasa (`439c1120eb045721…`, 15 443 bytes en ambas) y `fallo-paso-N.png` cuando no (`65be2d4f2f14ce83…` en el caso BLOCKED). El conjunto de evidencia aparenta una confirmación más de las que hay. Propuesta (nivel 1 · diseño): omitir `final.png` cuando coincida con la captura anterior, o nombrarlo de forma que se vea que es la misma toma.

## E-01 · Entorno, no defecto de itostack

En Git Bash sobre Windows, MSYS convierte un argumento que sea un `/` suelto en la raíz de la instalación de Git. Afecta a `--salud /` y también a banderas de herramientas de Windows como `tasklist /FI`. Remedios: omitir el argumento cuando su valor por omisión ya sirva, anteponer `MSYS_NO_PATHCONV=1`, o usar PowerShell. Conviene anotarlo en las convenciones de plataforma del plan de pruebas.

---

# Correcciones a premisas del plan

- **«No hay remoto: el PR va en skip».** Sí hay remoto: `origin https://github.com/Sickboooooy/harness-itosturre`. El paso 8 queda igualmente en `skip:`, pero por otra razón: los archivos corregidos viven en `pruebas-manuales/`, excluido del repositorio, así que no hay nada que confirmar ni empujar; y la regla 5 del plan prohíbe commits y push.
- **`/tmp` → `$TEMP`** ya estaba previsto; en el paso 1 de `crear-skill-verificacion` se usó el directorio de borradores de la sesión en lugar de `/tmp/inventario.md`.
