# Mapa de funcionalidades — validador ficticio

Mapa leído en frío por agentes. Cada entrada trae su ruta de verificación ejecutable con
`verificar.py app --base <base_url> --ruta <archivo.json>`.

Arranque: `python "$(cat .itostack/raiz_plugin)/scripts/arrancar_app.py" iniciar --comando "python -m flask --app app run --port {puerto}"`
(No agregues `--salud /` desde Git Bash: MSYS convierte el `/` suelto y el arranque falla dejando un servidor huérfano. El valor por omisión ya es `/`.)
Reinicio de estado: no aplica. La app no tiene base de datos ni sesión: todo el estado vive en el diccionario `CRITERIOS_FICTICIOS` de `app.py`, que se reconstruye en cada arranque. Basta `arrancar_app.py detener` y volver a iniciar.

Intérprete: en Windows usa `python` (`python3` es el alias de la Microsoft Store). Exporta `PYTHONUTF8=1`.

## validar-registro

- Ruta: `GET /` (formulario) → `POST /validar`
- Precondiciones: app arrancada con `arrancar_app.py iniciar`. No requiere cuenta de prueba, datos semilla ni permisos. Si la app no responde → BLOCKED.
- Selectores estables: `[data-testid=campo-registro]`, `[data-testid=boton-validar]`, `[data-testid=resultado]`
- Atajos: ninguno. No hay URL directa que muestre un resultado: `/validar` solo acepta POST, así que la ruta debe pasar por el formulario.
- Dueño del estado: el diccionario `CRITERIOS_FICTICIOS` (`app.py:7-10`), leído por `consultar()` (`app.py:13-14`). En memoria, sin persistencia.
- Archivos fuente: `app.py`, `templates/index.html`
- Datos de prueba conocidos: `FICT-0001` → `VERIFICADO` · `FICT-0404` → `INEXISTENTE` · cualquier otro → `NO ENCONTRADO`
- Rutas de verificación:
  - `rutas/validar-mayusculas.json` — registro `FICT-0001` debe mostrar «VERIFICADO».
  - `rutas/validar-minusculas.json` — registro `fict-0001` debe mostrar «VERIFICADO» (los registros no distinguen mayúsculas).

## Huecos conocidos

- No hay ruta de verificación para el registro inexistente (`FICT-0404` → «INEXISTENTE») ni para el caso de registro vacío. Son comportamientos reales de `consultar()` sin cobertura en el mapa.
- No existe ningún historial de consultas ni control `[data-testid=boton-historial]`: una verificación que lo use dará BLOCKED por selector ausente, que es el comportamiento correcto.

## ver-historial

- Ruta: `GET /historial`
- Precondiciones: app arrancada. Sin cuenta de prueba.
- Selectores estables: `[data-testid=boton-historial]`, `[data-testid=tabla-historial]`
- Atajos: ninguno.
- Dueño del estado: pendiente.
- Archivos fuente: `app.py`, `templates/index.html`
- Rutas de verificación:
  - `rutas/ver-historial.json` — el botón de historial debe abrir la tabla de consultas previas.
