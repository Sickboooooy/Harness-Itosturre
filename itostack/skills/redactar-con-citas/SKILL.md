---
name: redactar-con-citas
description: Redacción de escritos, promociones, proyectos o párrafos jurídicos con citas jurisprudenciales que se resuelven desde la evidencia forense mediante marcadores [[CITA:registro]], para que ningún rubro se escriba de memoria. Úsala cuando haya que redactar texto jurídico que invoque tesis, jurisprudencias o criterios del SJF.
---

# Redactar con citas (capa 1: el error es imposible por diseño)

Raíz del plugin: `R=$(cat .itostack/raiz_plugin)`.

El agente no escribe rubros, claves, datos de publicación ni marcas de verificación (⚠, ❌, ✅). Escribe marcadores; el ensamblador los sustituye con los datos oficiales capturados, añade una nota de evidencia por cita y deja junto al documento su manifiesto de procedencia (contrato `itostack/citas@1`).

## Procedimiento

1. **Verifica primero** cada criterio que usarás (solo con registro digital conocido):

   ```bash
   python3 "$R/scripts/verificar.py" tesis --registro <registro> --modo existencia
   ```

   Lee las advertencias ⚠: decide si el criterio sirve (obligatorio, aislado u orientador; vigencia tras las reformas).
2. **Redacta el borrador** en `borradores/<nombre>.md` con marcadores:
   - `[[CITA:2025432]]` → cita completa (tipo, clave, rubro, órgano, época, registro).
   - `[[CITA:2025432|rubro]]`, `|clave]]` o `|corta]]` para otras formas.
   - `[[CITA_AJENA:<referencia>|<fuente>]]` → una cita que hizo un tercero (contraparte, autoridad, resolución impugnada). La referencia debe aparecer literal en `<fuente>`, un documento del expediente dentro del proyecto; se entrega con «⚠ CITA NO VERIFICADA».
   - `[[NO_VERIFICADO:<texto>]]` → una afirmación propia que no pudiste verificar; se entrega con «(⚠ NO VERIFICADO)».
   - Fuera de un marcador no escribas registros, claves, «rubro:» ni marcas ⚠/❌/✅: el ensamblador lo rechaza.
3. **Ensambla**:

   ```bash
   python3 "$R/scripts/ensamblar_documento.py" borradores/<nombre>.md --salida salidas/<nombre>.md
   ```

   Si imprime `ENSAMBLADO: BLOCKED`, falta evidencia vigente, hay una cita o marca escrita a mano, o un marcador es inválido: verifica y repite. El ensamblador escribe `salidas/<nombre>.md.procedencia.json`; no lo edites, ni edites el documento después de ensamblarlo (cualquier cambio lo invalida). Compruébalo con `python3 "$R/scripts/verificar_entrega.py" salidas/<nombre>.md`. No uses `--permitir-pendientes` para un documento que se va a entregar. Agrega `--docx` si se requiere Word (usa pandoc).
4. **Poda relleno**: `python3 "$R/scripts/detectar_relleno.py" salidas/<nombre>.md`. Si hay que podar, corrige el **borrador** y vuelve a ensamblar: editar el entregable lo invalida.
5. **Entrega** la ruta, la lista de citas con su nota de evidencia y las advertencias ⚠ que el operador debe valorar.

## Reglas

- Si no tienes el registro de un criterio, no lo cites: escribe la idea sin cita o usa `[[NO_VERIFICADO:<descripción>]]` para el operador.
- El hook de escritura bloquea citas sin evidencia en `salidas/`, `escritos/` y `dictamenes/`; no lo evadas escribiendo en otra carpeta.
- Estilo para escritos procesales: redacción doctrinal formal, sin muletillas de IA.
