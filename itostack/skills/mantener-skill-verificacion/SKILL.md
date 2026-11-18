---
name: mantener-skill-verificacion
description: Mantiene al día el mapa de funcionalidades y la skill de verificación del proyecto cuando cambian rutas, selectores o flujos, o cuando una verificación termina BLOCKED por selector ausente. Úsala después de agregar o cambiar una funcionalidad de interfaz o al ver "selector ausente" en un veredicto.
---

# Mantener la skill de verificación

Raíz del plugin: `R=$(cat .itostack/raiz_plugin)`.

1. Compara el inventario actual (`python3 "$R/scripts/mapa_rutas_flask.py" .`) con `mapa-funcionalidades.md`: rutas nuevas, eliminadas o renombradas; selectores que ya no existen.
2. Resta antes de sumar: elimina del mapa lo que ya no existe y sus `rutas/*.json`.
3. Actualiza o agrega entradas y rutas JSON; cada entrada nueva con al menos una ruta de verificación.
4. Corre cada ruta modificada con /demuestra-que-funciona. Una ruta que nunca ha dado PASS no se documenta como válida.
5. Si cambió el arranque o el reinicio de estado, actualiza `.claude/skills/verificar-<proyecto>/SKILL.md` y repite su autoprueba de seis pasos.
6. Reporta el diff del mapa y los veredictos obtenidos.
