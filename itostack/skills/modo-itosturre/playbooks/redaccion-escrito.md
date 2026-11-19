# Playbook · Redacción de escrito con citas (jurídico)

1. Fijar meta y prueba: tipo de escrito, órgano, materia, pretensión y fecha de referencia para el corte temporal.
2. Detener si hay impacto procesal grave (plazo, prescripción, competencia, suspensión) y pedir confirmación al operador.
3. Investigar criterios en fuentes oficiales y anotar candidatos SOLO con su registro digital (sin rubros de memoria).
4. Verificar cada candidato con /verificar-cita en modo existencia (o cotejo si ya hay rubro escrito por terceros).
5. Leer las advertencias ⚠ de cada resultado y clasificar: jurisprudencia obligatoria, tesis aislada o criterio orientador.
6. Redactar el borrador en `borradores/` usando marcadores `[[CITA:registro]]` o `[[CITA:registro|forma]]`; nunca transcribir rubros a mano.
7. Ensamblar: `python3 "$R/scripts/ensamblar_documento.py" borradores/<archivo>.md --salida salidas/<archivo>.md` hasta obtener `ENSAMBLADO: PASS`.
8. Podar relleno: `python3 "$R/scripts/detectar_relleno.py" salidas/<archivo>.md` (sin tocar fórmulas forenses legítimas). Las correcciones van en el borrador y se vuelve a ensamblar: el entregable no se edita.
9. Comprobar la entrega: `python3 "$R/scripts/verificar_entrega.py" salidas/<archivo>.md` debe dar PASS.
9. Revisión adversarial con el subagente `revisor-adversarial` (y, si está disponible, `/interrogar` con un modelo local).
10. Entregar: ruta del escrito, citas con evidencia, advertencias ⚠ pendientes y la advertencia fija de verificación.
