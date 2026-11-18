---
name: verificar-cita
description: Verificación forense de una cita jurisprudencial (tesis o jurisprudencia del SJF) con captura del portal oficial, huella SHA-256 y veredicto PASS, FAIL o BLOCKED. Úsala SIEMPRE antes de usar, confirmar o descartar una tesis, cuando alguien pregunte si una cita existe o es correcta, o cuando un texto mencione un registro digital, una clave de tesis o un rubro. También para verificar una publicación del DOF o un artículo en LeyesBiblio.
---

# Verificar cita

Raíz del plugin: `R=$(cat .itostack/raiz_plugin)`. Si no existe `.itostack/`, ejecuta antes la skill `configurar-itostack`.

## Procedimiento

1. **Separa lo que dice la cita**: registro digital, rubro (tal como lo cita el texto), clave, época, instancia, tipo. No corrijas ni completes nada: se coteja lo citado contra lo oficial.
2. **Ejecuta el verificador** (una cita por llamada):

   ```bash
   python3 "$R/scripts/verificar.py" tesis --registro 2025432 --rubro "RUBRO COMO SE CITÓ" --clave "1a./J. 45/2019 (10a.)"
   ```

   - Sin rubro ni clave que cotejar (solo quieres confirmar existencia y tomar los datos oficiales): `--modo existencia`.
   - **Sin registro digital: NO lo busques de memoria ni lo inventes.** Ejecuta igual el verificador sin `--registro` (pasa `--rubro`/`--clave`) para dejar constancia BLOCKED, y pide al operador el registro o una búsqueda en el SJF.
   - Publicación del DOF o artículo de ley: `python3 "$R/scripts/verificar.py" url --url <url oficial> --contiene "texto esperado"`.
3. **Lee la salida completa**: la línea `VEREDICTO:`, el motivo, los cotejos y las advertencias ⚠. El resultado íntegro queda en `.itostack/ultimo_resultado.json` y en el almacén de evidencia (inmutable).
4. **Reporta** con este formato, sin agregar datos que no estén en la evidencia:

   ```
   VEREDICTO: <PASS|FAIL|BLOCKED> · <etiqueta>
   Motivo: <motivo del verificador>
   Advertencias: ⚠ … (todas, textuales)
   Evidencia: <ruta de resultado.json> · capturas: <rutas>
   Recomendación: usar / no usar / verificar manualmente (qué falta)
   ```

## Reglas

- PASS solo si el verificador imprimió `VEREDICTO: PASS`. Nunca escribas ✅ para un FAIL o un BLOCKED.
- FAIL = el portal contradice la cita (rubro, clave u órgano discrepante) o confirma que no existe. Una cita FAIL no se «arregla» proponiendo otra sin verificar.
- BLOCKED = no se pudo comprobar (portal caído, estructura no reconocida, sin registro). Di qué falta para resolverlo.
- Las advertencias de corte temporal (Sala extinta, reforma judicial, Duodécima Época, reforma de amparo) se trasladan siempre; no son opcionales.
- Si el resultado dice `EVIDENCIA DE FIXTURE`, decláralo: no es apto para uso procesal.
- Termina las respuestas con contenido jurídico con: ⚠ Respuesta generada por IA. Verificar citas en fuentes oficiales antes de uso procesal: sjf.scjn.gob.mx · dof.gob.mx · diputados.gob.mx/LeyesBiblio

## Si el verificador no puede correr

Falta Node o Playwright: el resultado será BLOCKED con la instrucción de instalación. No sustituyas el verificador por `curl`, WebFetch ni memoria: el hook de Bash lo bloquea y, sobre todo, no deja captura forense.
