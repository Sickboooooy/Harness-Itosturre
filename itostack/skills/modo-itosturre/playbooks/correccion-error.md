# Playbook · Corrección de error (desarrollo)

1. Congelar el reporte original (texto, capturas, ubicación) en la bitácora; toda respuesta se da en ese mismo hilo.
2. Triaje: leer el reporte completo, rastrear el código y el historial (`git log -p`, `git blame`) y buscar duplicados antes de actuar.
3. Reproducir con /demuestra-que-funciona sobre la ruta del mapa: describir estado correcto, estado roto y punto de divergencia.
4. Reiniciar el estado y reproducir por segunda vez de forma independiente; solo con dos observaciones se declara reproducido.
5. /tdd: escribir primero una prueba que falle (o documentar por qué se omite si exige integración pesada).
6. Aplicar la corrección acotada, sin limpiezas ajenas; correr `lint_itosturre.py --diff`.
7. Volver a verificar la ruta y capturar evidencia del funcionamiento correcto (`VEREDICTO: PASS`).
8. Redactar el PR y pasarlo por /sin-relleno: pasos de reproducción, causa raíz, evidencia antes/después y radio de impacto.
9. Abrir solo PR en borrador (`gh pr create --draft`); prohibido fusionar o desplegar.
