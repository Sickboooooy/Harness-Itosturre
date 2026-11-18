---
name: revision-salud
description: Chequeos de salud del harness - fricción recurrente en transcripciones (correcciones, errores, guardias disparadas, comandos repetidos) y consumo de tokens por sesión y por skill - con propuestas que esperan la selección del operador. Úsala en la revisión diaria o semanal, o cuando el operador pregunte qué está fallando, qué se repite o dónde se gastan tokens.
---

# Revisión de salud

Raíz del plugin: `R=$(cat .itostack/raiz_plugin)`.

1. Transcripciones (días hábiles): `python3 "$R/scripts/salud_transcripciones.py" --dias 1 --filtro <nombre del proyecto>`.
2. Rutinas y tokens (semanal): `python3 "$R/scripts/salud_rutinas.py" --dias 7 --filtro <nombre del proyecto>`.
3. Ambos guardan reporte en `.itostack/mejora/reportes/` solo si hay propuestas; sin propuestas, silencio.
4. Presenta las propuestas numeradas y **espera a que el operador elija**. No crees ni modifiques skills, guardias o bots por iniciativa propia.
5. Para cada propuesta elegida, deriva al flujo correcto: /corregir (correcciones), /construir-palanca (comandos repetidos), /mejorar-skill (skill desviada).

Programación sugerida en `plantillas/cron-itostack.txt` (8:44 días hábiles y lunes 8:49, hora local).
