# Demuéstralo (Prove It Works)

**Regla.** Un mensaje de «listo», una compilación en verde o una prueba que replica la implementación no demuestran nada. Funciona cuando se observó funcionando en la superficie real: el portal oficial para una cita, la app en ejecución para una funcionalidad.

**Cómo.** `verificar.py tesis|url|app` imprime `VEREDICTO:` con captura y SHA-256. Esa línea es la prueba; el hook de cierre bloquea afirmaciones de éxito sin ella.

**Antipatrón.** «Revisé el código y debería funcionar». «La cita es conocida».
