# Fase 7 · Pilar 2 Evals — resultado parcial

Alcance ejecutado: `crear-eval` y la autoprueba determinista. Los evals nativos (`claude plugin eval`) quedan **pendientes de WSL**: requieren el sandbox de bubblewrap y socat, ausentes en Windows nativo (F0-06).

| ID | Función | Esperado | Observado | Estado |
|---|---|---|---|---|
| F7-01 | `/itostack:crear-eval` · caso `verificar-cita/fail-epoca-discrepante` | caso nuevo con referencia y rota | 4 archivos creados en `itostack/evals/verificar-cita/fail-epoca-discrepante/` | OK |
| F7-02 | Autoprueba del caso nuevo | referencia 1.00, rota < 1.00 | **1.00 / 0.50**, coherente | OK |
| F7-03 | Autoprueba de la suite completa | sigue coherente | **18/18** (antes 17/17) | OK |
| F7-04 | Sin commit | el caso queda sin confirmar | `git status` → `?? itostack/evals/verificar-cita/fail-epoca-discrepante/` | OK |
| F7-05 | `/itostack:mejorar-skill` en seco | explicación de qué se haría | Ejercicio completo en `pruebas-manuales/fase7/mejorar-skill-en-seco.md`. Sin ejecutar correcciones | OK |
| F7-06 | `juez-evals` sobre `salidas/informe-vvca.md` con `itostack/evals/rubricas/informe-vvca.md` | calificación con rúbrica | Devolvió 10/10 y «cumplimiento completo». Al cotejarlo: 5 criterios cumplidos, **1 no aplicable** forzado como cumplido, y un puntaje que la rúbrica no define. Ver `pruebas-manuales/fase7/juez-evals-informe-vvca.md` (D-17) | OK con defecto |
| F7-07 | Evals nativos con `claude plugin eval` | puntaje con y sin plugin | **pendiente WSL**: sin bubblewrap ni socat | skip razonado |
| D-16 | Falso positivo en `pass-advertencia-sala` (reportado por el operador) | registrar sin corregir | Verificado y documentado en `pruebas-manuales/fase7/falso-positivo-pass-advertencia-sala.md`. **Sin corregir** | registrado |

## El caso creado

**Situación que prueba:** una cita cuyo rubro y clave coinciden letra por letra con el portal, pero cuya **época** no. Es más exigente que su hermano `fail-rubro-alterado`, donde la discrepancia salta a la vista en el texto: aquí el agente ve «cotejo rubro: coincide idéntico» y debe no dejarse llevar por eso.

Comprobado antes de escribir el caso, para no construirlo sobre una suposición:

```
VEREDICTO: FAIL · ❌ NO VERIFICABLE — DISCREPANTE O INEXISTENTE
tesis FICT-0001 — epoca discrepante (época 11 citada vs 12 oficial)
  cotejo rubro: coincide idéntico
  cotejo clave: coincide
  cotejo epoca: discrepante época 11 citada vs 12 oficial
```

**Graders (peso total 8), siguiendo la jerarquía de la regla 1 — verificable antes que llm:**

| Grader | Tipo | Peso | Qué exige |
|---|---|---|---|
| `veredicto-fail` | regex sobre `.itostack/ultimo_resultado.json` | 3 | `"veredicto": "FAIL"` |
| `no-afirma-verificado` | regex `not_contains` sobre el mensaje final | 2 | que no aparezca ✅ |
| `senala-la-epoca` | regex sobre el mensaje final | 2 | que nombre la **época**, no una «discrepancia» genérica |
| `usa-verificador` | `tool_used` | 1 | que haya corrido `verificar.py` |
| `calidad-del-reporte` | llm | 1 | veredicto, que identifique que lo discrepante es la época y no el rubro, evidencia, y que no presente evidencia de fixture como procesal |

El grader `senala-la-epoca` es el que da valor al caso: sin él, una respuesta vaga («hay una discrepancia») puntuaría igual que una precisa.

**La solución rota** imita al agente que se conforma con que el rubro coincida: corre el verificador, pero concluye «✅ VERIFICADO: el rubro y la clave coinciden… puedes usarla». Reprueba `no-afirma-verificado` (−2), `senala-la-epoca` (−2) y el grader llm (−1): **4 de 8 = 0.50**.

**Margen discriminante.** 1.00 contra 0.50 deja más holgura que `pass-advertencia-sala` (1.00 contra 0.80), que es el caso más estrecho de la suite.

Corrección posterior a esta medición: el operador señaló que **ese 0.80 es un falso positivo del grader**, no un margen estrecho legítimo. El patrón `sala|superad|corte temporal|reforma` encuentra «sala» dentro de «ú**sala**» en el mensaje de la solución rota (`✅ VERIFICADO, úsala sin reservas.`), de modo que la rota cobra un punto que debería reprobar. Verificado y documentado en `pruebas-manuales/fase7/falso-positivo-pass-advertencia-sala.md` (D-16). **No se corrigió**: el operador lo arregla en la 0.1.2.

Rutas: `itostack/evals/verificar-cita/fail-epoca-discrepante/{case.yaml,preparar.sh,referencia.sh,referencia_rota.sh}`.
