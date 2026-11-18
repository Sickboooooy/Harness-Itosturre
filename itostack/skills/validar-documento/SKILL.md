---
name: validar-documento
description: Validación forense VVCA de todas las citas de un documento ajeno (dictamen, proyecto, demanda, respuesta de otra IA como ChatGPT o Gemini) con informe auditable PASS/FAIL/BLOCKED por cita. Úsala cuando pidan revisar, auditar o validar las citas, tesis o jurisprudencias de un texto, detectar alucinaciones en citas, o entregar un informe de validación.
---

# Validar documento (núcleo Itosturre: validador, no generador)

Raíz del plugin: `R=$(cat .itostack/raiz_plugin)`.

## Procedimiento

1. **Extrae candidatos**:

   ```bash
   python3 "$R/scripts/reporte_vvca.py" extraer <documento.md|.docx|.txt>
   ```

2. **Revisa `.itostack/citas.json` contra el documento** (aquí está tu juicio): rubros truncados por la extracción se corrigen copiando el texto exacto del documento; citas fusionadas se separan; una cita sin registro se deja con `"registro": null`. Prohibido completar registros, claves o rubros con conocimiento propio.
3. **Verifica en lote**:

   ```bash
   python3 "$R/scripts/verificar.py" lote --archivo .itostack/citas.json
   ```

4. **Genera el informe**:

   ```bash
   python3 "$R/scripts/reporte_vvca.py" informe --documento <documento>
   ```

   Queda en `salidas/informe-vvca.md` (matriz VVCA, detalle por cita, evidencia y conclusión).
5. **Audita** el informe con el subagente `auditor-citas` si el documento tiene más de tres citas o va a entregarse a un cliente.
6. **Responde** con: ruta del informe, conteo PASS/FAIL/BLOCKED, las citas que no deben usarse y por qué, y las que requieren verificación manual.

## Reglas

- Nunca afirmes que «todas las citas están verificadas» si hay un solo FAIL o BLOCKED.
- Una cita inexistente o discrepante se reporta ❌; no propongas una sustituta sin verificarla con /verificar-cita.
- No edites a mano el informe para cambiar veredictos: el veredicto lo da el verificador.
- Advertencia fija al final de la respuesta.
