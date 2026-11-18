---
name: corregir
description: Convierte correcciones humanas repetidas en reglas deterministas - revisa el registro de correcciones, elige la más frecuente y propone elevarla al nivel más fuerte de la pirámide (tipo/API, lint/hook, prueba/eval, prosa). Úsala cuando el operador repita una corrección, cuando el hook avise que una corrección se repite, o al pedir "que no vuelva a pasar".
---

# Corregir (de corrección a regla)

Raíz del plugin: `R=$(cat .itostack/raiz_plugin)`.

## Procedimiento

1. **Lista pendientes**: `python3 "$R/scripts/registrar_correccion.py" pendientes` (correcciones con ≥2 repeticiones sin elevar). Si el operador acaba de corregirte algo que no está, igual puede elevarse.
2. **Elige** la de más repeticiones (o la que el operador indique).
3. **Decide el nivel más fuerte posible** y justifícalo:
   - 1 · diseño: un tipo, API o estructura que haga imposible el error.
   - 2 · análisis estático: regla nueva en `guardias/lint_itosturre.py` o en un hook (mensaje de error que enseñe la alternativa).
   - 3 · verificación: prueba, caso de eval o ruta del mapa.
   - 4 · prosa: solo si 1–3 son imposibles; explica por qué.
4. **Escribe la propuesta** (no apliques nada todavía):

   ```bash
   python3 "$R/scripts/registrar_correccion.py" proponer --clave <clave> --nivel <1-4> \
     --artefacto "<archivo y regla>" --descripcion "<qué bloquea y qué alternativa enseña>"
   ```

   Queda en `.itostack/mejora/propuesta.md`.
5. **Presenta** la propuesta al operador y espera aprobación.
6. **Con aprobación**: implementa la guardia, agrega una prueba que demuestre que bloquea el caso, corre pytest y registra con `registrar_correccion.py elevar …`.

## Reglas

- Una línea más en CLAUDE.md no es una solución si existe un nivel más fuerte.
- Las reglas de proyecto se proponen, no se imponen: el operador decide.
