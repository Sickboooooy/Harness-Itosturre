# Playbook · Nueva funcionalidad (desarrollo)

1. Fijar meta y prueba observable en la app («terminado cuando la ruta X muestra Y»).
2. Resta antes de sumar: buscar código, rutas o reglas que la funcionalidad vuelva obsoletos.
3. Agregar la entrada al mapa de funcionalidades con selectores `data-testid` y su ruta de verificación JSON (/mantener-skill-verificacion).
4. /tdd: prueba que falle primero.
5. Implementar el cambio mínimo suficiente.
6. Correr pruebas y `lint_itosturre.py --diff`.
7. /demuestra-que-funciona sobre la ruta nueva hasta `VEREDICTO: PASS`.
8. PR en borrador con evidencia y sin relleno.
