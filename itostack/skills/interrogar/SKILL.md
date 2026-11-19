---
name: interrogar
description: Revisión adversarial multi-modelo de un escrito, dictamen o diff - un subagente abogado del diablo y un modelo de otra familia (Codex en desarrollo, Ollama local en producción) - con hallazgos consolidados por gravedad. Úsala antes de entregar trabajo de alto impacto, cuando el usuario pida contraargumentos, una segunda opinión o "que otro modelo lo revise".
---

# Interrogar

Raíz del plugin: `R=$(cat .itostack/raiz_plugin)`. Modelos por rol en `.itostack/modelos.json`.

1. Fija qué se revisa (archivo o `git diff`) y el criterio de éxito.
2. Lanza en paralelo:
   - Subagente `revisor-adversarial` (modelo según `modelos.json`, rol `revisor`).
   - Revisor de otra familia. En desarrollo, Codex:

     ```bash
     python3 "$R/scripts/revisar_codex.py" --archivo <archivo> --rol adversarial
     git diff | python3 "$R/scripts/revisar_codex.py" --rol adversarial
     ```

     En producción (o si el script responde 3 por el entorno), el local: `revisar_ollama.py --modelo <modelo local> --archivo <archivo> --rol adversarial`.

3. Consolida en una tabla: gravedad, ubicación, problema, quién lo detectó, acción. Dos revisores que coinciden elevan la prioridad; un hallazgo aislado se valida contra la evidencia antes de aceptarlo.
4. Toda cita que un revisor proponga pasa por /verificar-cita antes de incorporarse.
5. Entrega la tabla y la decisión (aprobar, corregir, rechazar) al operador; no apliques cambios sustantivos sin su visto bueno.

Privacidad: `revisar_codex.py` envía el texto a OpenAI y solo corre con `"entorno": "desarrollo"` en `.itostack/config.json`; corre con sandbox de solo lectura, sin sesión persistida y desde un directorio neutro. `revisar_ollama.py` corre en `127.0.0.1` y rechaza endpoints remotos. Ambos rechazan modelos de la familia Claude.
