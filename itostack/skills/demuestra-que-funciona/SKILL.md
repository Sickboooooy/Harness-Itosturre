---
name: demuestra-que-funciona
description: Demuestra con evidencia observable (capturas, consola, veredicto PASS/FAIL/BLOCKED) que una funcionalidad de la app local funciona, recorriendo una ruta del mapa de funcionalidades en el navegador. Úsala para comprobar, reproducir o verificar comportamiento de la interfaz antes de afirmar que algo funciona, para reproducir un error y para confirmar una corrección.
---

# Demuestra que funciona («dar ojos al agente»)

Raíz del plugin: `R=$(cat .itostack/raiz_plugin)`.

## Procedimiento

1. **Ubica la ruta** en `mapa-funcionalidades.md` (raíz del repo o `.itostack/`). Cada funcionalidad trae su archivo de ruta JSON (`rutas/*.json`).
   - Si la funcionalidad no está en el mapa o su selector no existe en el código (`python3 "$R/scripts/mapa_rutas_flask.py" .`), el veredicto es **BLOCKED**: no implementes la funcionalidad ni inventes selectores para «poder probar».
   - Si necesitas una ruta nueva para algo que sí existe, créala en un JSON temporal con los selectores del mapa.
2. **Arranca la app aislada**:

   ```bash
   python3 "$R/scripts/arrancar_app.py" iniciar        # imprime base_url
   ```

   Si el proyecto no arranca con `flask --app app run`, pasa `--comando "… --port {puerto}"`.
3. **Recorre la ruta**:

   ```bash
   python3 "$R/scripts/verificar.py" app --base <base_url> --ruta rutas/<funcionalidad>.json
   ```

4. **Limpia**: `python3 "$R/scripts/arrancar_app.py" detener` (la evidencia sobrevive en `.itostack/evidencia/`).
5. **Reporta**: `VEREDICTO`, paso que falló y detalle, rutas de las capturas (antes, fallo, final) y errores de consola.

## Formato de ruta

```json
{"nombre": "validar-registro", "pasos": [
  {"accion": "ir", "ruta": "/"},
  {"accion": "llenar", "selector": "[data-testid=campo-registro]", "valor": "FICT-0001"},
  {"accion": "clic", "selector": "[data-testid=boton-validar]"},
  {"accion": "esperar_texto", "texto": "Resultado: VERIFICADO"},
  {"accion": "captura", "etiqueta": "resultado"}
]}
```

Acciones: `ir`, `clic`, `llenar`, `presionar`, `esperar_texto`, `esperar_selector`, `captura`.

## Reglas

- Selector ausente → BLOCKED (mapa desactualizado), no FAIL. Expectativa incumplida → FAIL. App caída → BLOCKED.
- Si te pidieron solo verificar, no corrijas: reporta y propone el siguiente paso.
- Nunca declares que funciona leyendo el código: el hook de cierre exige `VEREDICTO: PASS` en la sesión.
