---
name: jardineria
description: Jardinería de código para agentes - localizar y arrancar patrones defectuosos que los agentes copian (parches, esperas fijas, comentarios-excusa, acoplamientos, código muerto) y dejar una guardia que impida su regreso. Úsala para pagar deuda técnica, preparar un repositorio antes de paralelizar agentes, o cuando el mismo error aparezca en varios lugares.
---

# Jardinería

Raíz del plugin: `R=$(cat .itostack/raiz_plugin)`.

1. Haz un censo: `python3 "$R/guardias/lint_itosturre.py" <rutas>` y delega al subagente `jardinero` la búsqueda de patrones repetidos (parches, TODO/HACK, `waitForTimeout`, imports cruzados, duplicación).
2. Prioriza por propagación: el patrón que más se copia primero.
3. Captura la línea base de comportamiento (/demuestra-que-funciona o pruebas).
4. Un PR atómico por patrón: elimina todas sus apariciones.
5. Agrega o ajusta la guardia que lo impide (regla IT00X, hook o prueba) y una prueba de la guardia.
6. Verifica que el comportamiento no cambió y registra la elevación (`registrar_correccion.py elevar`).

Las reglas de un proyecto (p. ej. vetar comentarios o un hook de React) no son dogmas universales: proponlas al operador con su justificación antes de imponerlas.
