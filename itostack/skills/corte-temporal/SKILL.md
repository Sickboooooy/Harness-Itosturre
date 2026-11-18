---
name: corte-temporal
description: Revisión de vigencia de criterios jurisprudenciales frente a la reforma judicial (DOF 15-IX-2024), la Duodécima Época (1-IX-2025), la reforma a la Ley de Amparo (17-X-2025) y la extinción de las Salas de la SCJN. Úsala cuando una tesis sea anterior a esas fechas, provenga de la Primera o Segunda Sala, o el usuario pregunte si un criterio sigue vigente o fue superado.
---

# Corte temporal

Raíz del plugin: `R=$(cat .itostack/raiz_plugin)`.

## Procedimiento

1. Verifica la tesis con /verificar-cita: el resultado ya trae las advertencias automáticas de corte temporal.
2. Para cada advertencia ⚠, determina qué hay que confirmar:
   - **Sala extinta**: ¿el Pleno reiteró, interrumpió o superó el criterio? ¿Hay contradicción resuelta posterior?
   - **Reforma judicial / Duodécima Época**: ¿el criterio depende de competencias u órganos que cambiaron?
   - **Reforma de amparo (materia común)**: ¿el criterio interpreta artículos reformados? Revisar el transitorio 3° para asuntos en trámite.
3. Busca criterios posteriores en el SJF y verifica cada hallazgo con /verificar-cita (no basta con mencionarlo).
4. Concluye por criterio: «vigente con evidencia», «superado (evidencia)» o «⚠ sin confirmación de vigencia».

## Reglas

- Sin confirmación verificada, la conclusión es ⚠, nunca «vigente».
- Las fechas de corte viven en `.itostack/config.json` (`cortes_temporales`); provienen del marco declarado por el operador y deben confirmarse en el DOF antes de uso procesal.
