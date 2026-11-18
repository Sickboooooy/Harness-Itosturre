---
name: redactar-con-citas
description: Redacción de escritos, promociones, proyectos o párrafos jurídicos con citas jurisprudenciales que se resuelven desde la evidencia forense mediante marcadores [[CITA:registro]], para que ningún rubro se escriba de memoria. Úsala cuando haya que redactar texto jurídico que invoque tesis, jurisprudencias o criterios del SJF.
---

# Redactar con citas (capa 1: el error es imposible por diseño)

Raíz del plugin: `R=$(cat .itostack/raiz_plugin)`.

El agente no escribe rubros, claves ni datos de publicación. Escribe marcadores; el ensamblador los sustituye con los datos oficiales capturados y añade una nota de evidencia por cita.

## Procedimiento

1. **Verifica primero** cada criterio que usarás (solo con registro digital conocido):

   ```bash
   python3 "$R/scripts/verificar.py" tesis --registro <registro> --modo existencia
   ```

   Lee las advertencias ⚠: decide si el criterio sirve (obligatorio, aislado u orientador; vigencia tras las reformas).
2. **Redacta el borrador** en `borradores/<nombre>.md` con marcadores:
   - `[[CITA:2025432]]` → cita completa (tipo, clave, rubro, órgano, época, registro).
   - `[[CITA:2025432|rubro]]`, `|clave]]` o `|corta]]` para otras formas.
3. **Ensambla**:

   ```bash
   python3 "$R/scripts/ensamblar_documento.py" borradores/<nombre>.md --salida salidas/<nombre>.md
   ```

   Si imprime `ENSAMBLADO: BLOCKED`, falta evidencia vigente o hay una cita escrita a mano: verifica y repite. No uses `--permitir-pendientes` para un documento que se va a entregar. Agrega `--docx` si se requiere Word (usa pandoc).
4. **Poda relleno**: `python3 "$R/scripts/detectar_relleno.py" salidas/<nombre>.md`.
5. **Entrega** la ruta, la lista de citas con su nota de evidencia y las advertencias ⚠ que el operador debe valorar.

## Reglas

- Si no tienes el registro de un criterio, no lo cites: escribe la idea sin cita o marca `⚠ CITA PENDIENTE: <descripción>` para el operador.
- El hook de escritura bloquea citas sin evidencia en `salidas/`, `escritos/` y `dictamenes/`; no lo evadas escribiendo en otra carpeta.
- Estilo para escritos procesales: redacción doctrinal formal, sin muletillas de IA.
