---
name: verificar-app-simulada
description: Verifica funcionalidades del validador ficticio (app Flask de pruebas) sobre la app en ejecución con evidencia (capturas y veredicto PASS/FAIL/BLOCKED) usando el mapa de funcionalidades. Úsala antes de afirmar que algo funciona en esta app, para reproducir errores y para confirmar correcciones.
---

# Verificar app-simulada

Escrita para un agente que no conoce el repositorio. Si algo de lo que necesitas no está aquí, la skill está incompleta: repórtalo.

Trabaja siempre desde la raíz del proyecto (el directorio que contiene `app.py` y `.itostack/`).

```bash
R=$(cat .itostack/raiz_plugin)
```

**Intérprete:** en Windows usa `python` (`python3` es el alias de la Microsoft Store y no ejecuta nada). Exporta `PYTHONUTF8=1` antes de correr los scripts, o las rayas y los ⚠ saldrán como `?`.

1. **Arranque.** Antes de iniciar, comprueba que no haya una app colgada de una corrida anterior:

   ```bash
   python "$R/scripts/arrancar_app.py" estado     # si reporta una app, detenla primero
   python "$R/scripts/arrancar_app.py" iniciar --comando "python -m flask --app app run --port {puerto}"
   ```

   Si `estado` dice `"sin app"` pero `.itostack/app.log` muestra un `Running on http://127.0.0.1:<puerto>` reciente, hay un servidor huérfano de un arranque que falló (ver el aviso de abajo): compruébalo con `netstat -ano -p TCP | grep <puerto>` y mátalo con `Stop-Process -Id <pid> -Force` desde PowerShell. `detener` no puede con él.

   Imprime JSON con `base_url`, `puerto` y `pid`. Guarda el `base_url`: los pasos 3 y siguientes lo necesitan. El estado vive en `.itostack/app.json`.

   ⚠ **No pases `--salud /` desde Git Bash en Windows.** MSYS convierte el `/` suelto en `C:/Program Files/Git/` y el arranque revienta con un `InvalidURL` (traceback, sin veredicto) **dejando vivo un servidor huérfano** que `detener` ya no puede matar, porque nunca llegó a escribirse `.itostack/app.json`. El valor por omisión de `--salud` ya es `/`, así que basta omitirlo. Si necesitas otra ruta de salud que empiece con `/`, antepón `MSYS_NO_PATHCONV=1`.

2. **Diagnóstico:** `python "$R/scripts/arrancar_app.py" estado` debe mostrar `"responde": true`. Si no responde, revisa `.itostack/app.log` y reporta **BLOCKED**; no sigas.

3. **Ruta:** elige una funcionalidad en `mapa-funcionalidades.md` y ejecuta:

   ```bash
   python "$R/scripts/verificar.py" app --base <base_url> --ruta rutas/<archivo>.json
   ```

   Rutas disponibles hoy: `rutas/validar-mayusculas.json` y `rutas/validar-minusculas.json`. Salida: 0 = PASS, 1 = FAIL, 2 = BLOCKED.

4. **Evidencia:** queda en `.itostack/evidencia/app/<nombre>/<marca de tiempo>/`. Capturas: `paso-1-ir.png`, `resultado.png` y `final.png` cuando pasa; `fallo-paso-N.png` cuando no. Además se guardan el HTML y el texto de la primera página (`paso-1-ir.html`, `paso-1-ir.txt`) y el `resultado.json` con el veredicto y los SHA-256.

   Dos cosas que confunden a un auditor y conviene saber de antemano:
   - **`final.png` es byte-idéntico a la última captura** (`resultado.png` cuando pasa, `fallo-paso-N.png` cuando no): mismo SHA-256. No es una confirmación independiente; la evidencia real es la penúltima.
   - **El SHA-256 que imprime el verificador para `resultado.json` no es el hash de ese archivo.** Es una huella canónica sobre el JSON ya parseado (un hash no puede contenerse a sí mismo). Si lo recalculas con `sha256sum resultado.json` dará distinto y **no** significa que la evidencia esté alterada. Para comprobar integridad usa `evidencia_db.py auditar`, que aplica el régimen correcto a cada artefacto: bytes crudos para los PNG, huella canónica para el JSON.

5. **Limpieza:** `python "$R/scripts/arrancar_app.py" detener`. No hay reinicio de estado que hacer: la app no persiste nada, el diccionario `CRITERIOS_FICTICIOS` se reconstruye en cada arranque. Tras detener, `.itostack/app.json` debe desaparecer.

6. **Confirmación:** `python "$R/scripts/evidencia_db.py" auditar` → `Integridad: OK`. La evidencia sobrevive a la limpieza.

## Reglas

- Selector que no existe en el código → **BLOCKED** (mapa desactualizado), nunca FAIL. Compruébalo con `python "$R/scripts/mapa_rutas_flask.py" .`, que lista las rutas Flask y los `data-testid` reales.
- Expectativa incumplida (el texto esperado no aparece) → **FAIL**.
- App caída o que no responde → **BLOCKED**.
- No implementes funcionalidades ni agregues `data-testid` para «poder probar»: eso es un cambio de código y requiere aprobación del operador.
- Nunca declares que algo funciona por haber leído `app.py`: hace falta `VEREDICTO: PASS` de una corrida real.

Credenciales de prueba: ninguna. Esta app no tiene autenticación ni cuentas; si una funcionalidad futura las exige y no están documentadas aquí → BLOCKED.
