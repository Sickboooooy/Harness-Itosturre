---
name: crear-skill-verificacion
description: Genera la skill de verificación propia de un proyecto (.claude/skills/verificar-<proyecto>/SKILL.md) y su mapa de funcionalidades con rutas, precondiciones, selectores data-testid, dueños de estado y rutas de verificación JSON, y la autoprueba de extremo a extremo antes de entregarla. Úsala al adoptar itostack en un repositorio con interfaz (Flask, Electron, web) o cuando los agentes desperdicien contexto redescubriendo cómo operar la app.
---

# Crear skill de verificación del proyecto

Raíz del plugin: `R=$(cat .itostack/raiz_plugin)`. Plantillas: `$R/plantillas/verify-SKILL.md` y `$R/plantillas/mapa-funcionalidades.md`.

La skill resultante se escribe para un agente que lee el repositorio **en frío**: nada de suposiciones implícitas.

## Procedimiento

1. **Inventario determinista**: `python3 "$R/scripts/mapa_rutas_flask.py" . > /tmp/inventario.md` (rutas Flask y `data-testid`). Para otros frameworks, inventaría a mano y considera agregar un extractor (/construir-palanca).
2. **Arranque**: identifica el comando que levanta la app en un puerto arbitrario y pruébalo con `arrancar_app.py iniciar --comando "… {puerto}"`.
3. **Mapa**: completa `mapa-funcionalidades.md` (raíz del repo) con una sección por funcionalidad: ruta, precondiciones (cuentas de prueba, datos semilla), selectores estables, atajos, dueño del estado, archivos fuente y archivos `rutas/<funcionalidad>.json`. Si un control no tiene `data-testid`, propón agregarlo (es un cambio de código: pide aprobación).
4. **Skill**: copia la plantilla a `.claude/skills/verificar-<proyecto>/SKILL.md` y rellena comando de arranque, salud, rutas y cómo reiniciar estado.
5. **Autoprueba obligatoria antes de entregar**, siguiendo SOLO lo escrito en la skill nueva:
   1. arranque (`arrancar_app.py iniciar`),
   2. diagnóstico (`arrancar_app.py estado` responde),
   3. una ruta mapeada (`verificar.py app …` con `VEREDICTO: PASS`),
   4. captura de evidencia (rutas en el resultado),
   5. limpieza (`arrancar_app.py detener`),
   6. confirmación de que la evidencia sobrevivió a la limpieza (`evidencia_db.py auditar` → Integridad: OK).
   Si algún paso necesitó conocimiento que no está en la skill, la skill está incompleta: corrígela y repite.
6. Entrega: rutas de la skill y del mapa, resultado de la autoprueba y huecos conocidos (funcionalidades sin ruta, selectores faltantes).
