---
name: crear-eval
description: Crea casos de evaluación para una skill del harness en el formato nativo de claude plugin eval (case.yaml con graders regex, file_exists, tool_used y llm), con andamiaje, solución de referencia y solución rota. Úsala para escribir "pruebas unitarias de skills", reproducir un defecto de una skill o ampliar la cobertura de evals.
---

# Crear eval

Raíz del plugin: `R=$(cat .itostack/raiz_plugin)`. Ejemplos: `$R/evals/verificar-cita/*`.

## Estructura de un caso

```
evals/<skill>/<caso>/            # holdout-<caso> si es de reserva
  case.yaml                      # schema_version "1.0", name "<skill>.<caso>", tags [<skill>, desarrollo|holdout, perfil]
  preparar.sh                    # exec bash "$CASO/../../_comun/preparar.sh" "$CASO" <perfil> [documentos]
  referencia.sh                  # solución correcta con los scripts del plugin; escribe el mensaje final en "$MENSAJE"
  referencia_rota.sh             # agente que NO verifica (afirma éxito, inventa, se salta pasos)
  archivos/                      # opcional: archivos extra que se copian al espacio de trabajo
```

## Reglas para graders

1. Jerarquía: verificable (regex sobre archivos/resultado, file_exists) → binario → llm. Usa `llm` solo si lo anterior no alcanza, con afirmaciones comprobables.
2. Banderas de regex en `flags: i`, no `(?i)` (el motor es JavaScript).
3. **Las herramientas siguen a los graders**: si un grader exige un archivo creado, el caso debe permitir `Write`/`Bash`.
4. Cada skill necesita casos positivos, casos rotos (FAIL) y al menos un holdout donde la única respuesta aceptable sea BLOCKED.
5. Datos solo ficticios (`FICT-####` en `evals/fixtures/sjf/`). Nunca uses registros reales en fixtures.
6. Prueba la eval antes de usarla: `python3 "$R/evals/autoprueba.py" --caso "<skill>/<caso>"` debe dar referencia 1.00 y rota < 1.00. Si la rota pasa, el grader es una métrica de vanidad: endurécelo.
7. Si el caso es holdout, créalo con `ITOSTACK_EDITAR_HOLDOUT=1` (lo hace el operador, no el agente que mejora la skill).
