# Playbook · Validación forense de texto ajeno (jurídico)

1. Fijar meta: qué documento, de quién proviene y para qué se usará el informe.
2. Extraer candidatos: `python3 "$R/scripts/reporte_vvca.py" extraer <documento>`.
3. Revisar `.itostack/citas.json` contra el documento: corregir rubros truncados por la extracción tal como aparecen en el texto, separar citas fusionadas; no agregar ni completar registros.
4. Verificar en lote: `python3 "$R/scripts/verificar.py" lote --archivo .itostack/citas.json`.
5. Generar el informe: `python3 "$R/scripts/reporte_vvca.py" informe --documento <documento>`.
6. Auditar el informe con el subagente `auditor-citas` (ninguna cita FAIL/BLOCKED con ✅; toda PASS con evidencia).
7. Entregar la ruta del informe y el resumen PASS/FAIL/BLOCKED; nunca proponer una cita sustituta sin verificarla.
