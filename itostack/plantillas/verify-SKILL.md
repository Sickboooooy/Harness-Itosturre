---
name: verificar-<proyecto>
description: Verifica funcionalidades de <proyecto> sobre la app en ejecución con evidencia (capturas y veredicto PASS/FAIL/BLOCKED) usando el mapa de funcionalidades. Úsala antes de afirmar que algo funciona en <proyecto>, para reproducir errores y para confirmar correcciones.
---

# Verificar <proyecto>

Escrita para un agente que no conoce el repositorio. Si algo de lo que necesitas no está aquí, la skill está incompleta: repórtalo.

R=$(cat .itostack/raiz_plugin)

1. Arranque: `python3 "$R/scripts/arrancar_app.py" iniciar --comando "<comando exacto con {puerto}>" --salud <ruta de salud>`
2. Diagnóstico: `python3 "$R/scripts/arrancar_app.py" estado` debe mostrar `"responde": true`.
3. Ruta: elige en `mapa-funcionalidades.md` y ejecuta `python3 "$R/scripts/verificar.py" app --base <base_url> --ruta rutas/<archivo>.json`.
4. Evidencia: las capturas quedan en `.itostack/evidencia/app/<nombre>/`.
5. Limpieza: `python3 "$R/scripts/arrancar_app.py" detener` y <reinicio de estado>.
6. Confirmación: `python3 "$R/scripts/evidencia_db.py" auditar` → `Integridad: OK`.

Credenciales de prueba: <dónde están; nunca en el chat ni en el repositorio>. Si faltan → BLOCKED.
