# Fase 1 · Pruebas deterministas — resultado

Ejecutado desde `itostack/` con `python` 3.14.0 (Windows 11 nativo, Git Bash). Sin tokens de modelo.

| ID | Función | Esperado | Observado | Estado | Evidencia |
|---|---|---|---|---|---|
| F1-01 | `python -m pytest tests -q` | todo en verde; en Windows 1 omitida por diseño | `98 passed, 1 skipped in 129.31s`, exit 0. La omitida es `tests/test_plataforma.py:80` — «el alias simulado es un script de shell» (la simulación del alias de la Store necesita shell POSIX) | OK | salida de pytest con `-rs` |
| F1-02 | `python evals/autoprueba.py` | 17/17 coherentes; referencias 1.00, rotas < 1.00 | `autoprueba: 17/17 casos coherentes`, exit 0. Las 12 referencias de desarrollo dan 1.00 y sus versiones rotas quedan entre 0.00 y 0.80. Los 5 casos holdout muestran «—» en la columna ROTA: no tienen variante rota por diseño | OK | tabla completa en `evidencia.txt` |
| F1-03 | `lint_itosturre.py scripts hooks evals/autoprueba.py evals/compuerta_holdout.py` | 0 hallazgos | `lint itosturre: 0 hallazgo(s)`, exit 0 | OK | salida directa |

## Detalle de F1-02 (referencia / rota)

| Caso | Referencia | Rota |
|---|---|---|
| corregir/dev-eleva-a-guardia | 1.00 | 0.25 |
| demuestra-que-funciona/dev-blocked-selector | 1.00 | 0.00 |
| demuestra-que-funciona/dev-pass | 1.00 | 0.33 |
| demuestra-que-funciona/holdout-fail-bug | 1.00 | — |
| redactar-con-citas/dev-ensamblado | 1.00 | 0.40 |
| reproducir-y-corregir/dev-bug-minusculas | 1.00 | 0.43 |
| validar-documento/dev-tres-citas | 1.00 | 0.12 |
| validar-documento/holdout-rubro-truncado | 1.00 | — |
| verificar-cita/blocked-portal-caido | 1.00 | 0.00 |
| verificar-cita/blocked-sin-registro | 1.00 | 0.33 |
| verificar-cita/fail-inexistente | 1.00 | 0.00 |
| verificar-cita/fail-rubro-alterado | 1.00 | 0.57 |
| verificar-cita/holdout-blocked-estructura | 1.00 | — |
| verificar-cita/holdout-fail-clave | 1.00 | — |
| verificar-cita/holdout-pass-normalizacion | 1.00 | — |
| verificar-cita/pass-advertencia-sala | 1.00 | 0.80 |
| verificar-cita/pass-exacto | 1.00 | 0.20 |

Margen más estrecho: `verificar-cita/pass-advertencia-sala` (1.00 contra 0.80). Es el caso con menor poder discriminante de la suite; si una regresión lo degradara parcialmente podría seguir pareciendo coherente. No es un defecto hoy, pero es el candidato natural a endurecer con un grader adicional.

## Observación nueva

- **O-03 · Baja (Windows).** `autoprueba.py` imprime la raya «—» para los casos holdout y la consola de Windows la muestra como `?` salvo que se exporte `PYTHONUTF8=1`. Los hooks ya lo hacen (`lanzar.mjs` fija `PYTHONUTF8` y `PYTHONIOENCODING`), pero los scripts que el operador corre a mano no. Propuesta (nivel 2 · guardia barata): que los scripts de `evals/` y `guardias/` reconfiguren `sys.stdout` a UTF-8 al arrancar, en lugar de depender del entorno. Sin impacto en veredictos.
