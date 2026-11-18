---
name: reproducir-y-corregir
description: Flujo completo para un error reportado (estilo Benny): triaje, reproducción doble con evidencia, prueba que falla primero, corrección acotada, verificación posterior y PR solo en borrador. Úsala cuando llegue un reporte de error, un "no funciona", un bug de usuario o un hilo de incidencia que haya que reproducir y arreglar.
---

# Reproducir y corregir

Raíz del plugin: `R=$(cat .itostack/raiz_plugin)`.

Falla cerrado: si falta configuración, mapa o datos para reproducir, detente con BLOCKED y di qué falta.

## Procedimiento

1. **Congela el reporte**: copia el texto original y sus capturas a la bitácora (`python3 "$R/scripts/bitacora.py" registrar --tarea "<id>" --decision "reporte congelado" --razon "<resumen>"`). Las respuestas van en el mismo hilo.
2. **Triaje**: lee todo el reporte; rastrea el código (`git log -p`, `git blame`) y busca si ya existe un issue o PR. No toques código aún.
3. **Reproduce** con /demuestra-que-funciona sobre la ruta del mapa que describe el síntoma (o una ruta JSON nueva con los mismos selectores). Anota estado correcto, estado roto y dónde divergen.
4. **Segunda reproducción independiente**: detén y vuelve a arrancar la app, repite exactamente la misma ruta. Solo con dos `VEREDICTO: FAIL` se declara reproducido.
5. **/tdd**: escribe la prueba que falla y córrela (`python3 -m pytest -q`). Si el objetivo exige integración pesada, documenta por qué se omite.
6. **Corrige** con el cambio mínimo, sin limpiezas ajenas. Corre `python3 "$R/guardias/lint_itosturre.py" --diff`.
7. **Verifica después**: pruebas en verde y la misma ruta con `VEREDICTO: PASS`.
8. **PR en borrador** (si hay remoto): texto pasado por /sin-relleno con pasos de reproducción, causa raíz, evidencia antes/después y radio de impacto. `gh pr create --draft`. Prohibido fusionar o desplegar.

## Cierre

Reporta: reproducción (dos FAIL con rutas de captura), causa raíz, prueba agregada, corrección, verificación final (PASS) y PR. Si algo quedó en `skip:`, dilo.
