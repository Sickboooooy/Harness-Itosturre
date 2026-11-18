# Construye la palanca

**Regla.** Si un agente reescribe la misma mecánica (scripts de Playwright, consultas, parseos), extráela a un CLI determinista en `scripts/`. La skill conserva el juicio: cuándo invocarlo y cómo interpretar su salida.

**Por qué.** Ahorra contexto y tokens, y vuelve el resultado repetible y auditable. `salud_transcripciones.py` detecta comandos repetidos candidatos.
