# Mapa de funcionalidades — <proyecto>

Escrito para un agente que lee el repositorio en frío. Cada entrada debe poder verificarse con:
`python3 "$(cat .itostack/raiz_plugin)/scripts/verificar.py" app --base <base_url> --ruta <rutas/archivo.json>`

Arranque: `python3 "$(cat .itostack/raiz_plugin)/scripts/arrancar_app.py" iniciar --comando "<comando con {puerto}>"`
Reinicio de estado: <cómo dejar la app limpia entre corridas (base de pruebas, semilla, borrar caché)>

## <funcionalidad>

- Ruta: `<método> <ruta>`
- Precondiciones: <cuentas de prueba, datos semilla, permisos> (si faltan → BLOCKED)
- Selectores estables: `[data-testid=…]`, …
- Atajos: <teclas o URLs directas>
- Dueño del estado: <módulo, tabla de SQLite, store>
- Archivos fuente: `<archivo>`, …
- Rutas de verificación:
  - `rutas/<funcionalidad>.json` — <qué demuestra>
