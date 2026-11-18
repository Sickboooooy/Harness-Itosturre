---
name: interrogar
description: Revisión adversarial multi-modelo de un escrito, dictamen o diff - un subagente abogado del diablo y, si hay Ollama, un modelo local de otra familia - con hallazgos consolidados por gravedad. Úsala antes de entregar trabajo de alto impacto, cuando el usuario pida contraargumentos, una segunda opinión o "que otro modelo lo revise".
---

# Interrogar

Raíz del plugin: `R=$(cat .itostack/raiz_plugin)`. Modelos por rol en `.itostack/modelos.json`.

1. Fija qué se revisa (archivo o `git diff`) y el criterio de éxito.
2. Lanza en paralelo:
   - Subagente `revisor-adversarial` (modelo según `modelos.json`, rol `revisor`).
   - Revisor local de otra familia, si Ollama responde:

     ```bash
     python3 "$R/scripts/revisar_ollama.py" --modelo <modelo local> --archivo <archivo> --rol adversarial
     ```

3. Consolida en una tabla: gravedad, ubicación, problema, quién lo detectó, acción. Dos revisores que coinciden elevan la prioridad; un hallazgo aislado se valida contra la evidencia antes de aceptarlo.
4. Toda cita que un revisor proponga pasa por /verificar-cita antes de incorporarse.
5. Entrega la tabla y la decisión (aprobar, corregir, rechazar) al operador; no apliques cambios sustantivos sin su visto bueno.

Privacidad: el revisor local corre en `127.0.0.1`; el script rechaza endpoints remotos y modelos de la familia Claude.
