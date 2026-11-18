# Mapa de funcionalidades — validador ficticio

Mapa leído en frío por agentes. Cada entrada trae su ruta de verificación ejecutable con
`verificar.py app --base <base_url> --ruta <archivo.json>`.

## validar-registro

- Ruta: `GET /` (formulario) → `POST /validar`
- Precondiciones: app arrancada con `arrancar_app.py iniciar` (no requiere cuenta de prueba).
- Selectores estables: `[data-testid=campo-registro]`, `[data-testid=boton-validar]`, `[data-testid=resultado]`
- Propietario del estado: `CRITERIOS_FICTICIOS` en `app.py`
- Archivos fuente: `app.py`, `templates/index.html`
- Rutas de verificación:
  - `rutas/validar-mayusculas.json` — registro `FICT-0001` debe mostrar «VERIFICADO».
  - `rutas/validar-minusculas.json` — registro `fict-0001` debe mostrar «VERIFICADO» (los registros no distinguen mayúsculas).
