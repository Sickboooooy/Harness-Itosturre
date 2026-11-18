---
name: construir-palanca
description: Extrae una mecánica repetida (scripts ad hoc de Playwright, consultas, parseos, secuencias de comandos) a un CLI determinista en scripts/ con pruebas, y reduce la skill al juicio de cuándo usarlo. Úsala cuando un agente reescriba lo mismo en varias sesiones, cuando el chequeo de salud reporte comandos repetidos, o para ahorrar contexto y tokens.
---

# Construir la palanca

Raíz del plugin: `R=$(cat .itostack/raiz_plugin)`.

1. Identifica la mecánica (de la transcripción, del reporte de salud o de la petición) y sus entradas y salidas.
2. Escribe el CLI en `scripts/` (Python estándar o TypeScript con Playwright), con nombres y mensajes en español, salida legible y códigos de salida claros. Si toca portales oficiales, solo a través de `lib/navegador_forense.ts` (regla IT001).
3. Agrega pruebas en `tests/` y córrelas.
4. Reduce la skill que hacía la mecánica a mano: deja el cuándo y el cómo interpretar la salida; borra los pasos mecánicos (resta antes de sumar).
5. Si la skill tiene evals, córrelas: la palanca debe mantener o subir el puntaje y bajar tokens.
6. Commit descriptivo en español.
