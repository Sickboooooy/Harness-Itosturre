# Playbook · Refactor y jardinería (desarrollo)

1. Identificar el patrón defectuoso que los agentes copian (parche, espera fija, acoplamiento, comentario-excusa) con el subagente `jardinero`.
2. Capturar evidencia del comportamiento actual con /demuestra-que-funciona (línea base).
3. Eliminar el patrón en cambios atómicos (un PR por patrón).
4. Agregar la guardia que impide su regreso en el nivel más fuerte posible (regla IT00X, hook o prueba).
5. Verificar que el comportamiento observado no cambió (mismas rutas en PASS) y que el lint pasa.
6. PR en borrador con evidencia antes/después.
