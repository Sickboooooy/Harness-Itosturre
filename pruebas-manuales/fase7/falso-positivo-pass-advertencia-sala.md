# D-16 · Falso positivo en el grader `explica-contexto` de `pass-advertencia-sala`

**Reportado por el operador. Registrado sin corregir, por instrucción suya: lo corrige en la 0.1.2.**

## Qué pasa

El caso `itostack/evals/verificar-cita/pass-advertencia-sala` tiene un grader que premia al agente por trasladar las advertencias de corte temporal:

```yaml
  name: explica-contexto
  target: last_message
  pattern: sala|superad|corte temporal|reforma
  flags: i
  weight: 1
```

El mensaje final de la solución **rota** es:

```
✅ VERIFICADO, úsala sin reservas.
```

El patrón alterna `sala` como palabra suelta, sin delimitadores. La cadena `sala` aparece dentro de **«ú*sala*»**. Comprobado:

```
patron 'sala' -> True | coincide en: 'ICADO, úsala sin res'
```

La solución rota —que afirma ✅ sobre una tesis de Sala extinta y recomienda usarla sin reservas, es decir, exactamente lo contrario de lo que el grader quiere premiar— **aprueba ese grader**.

## Consecuencia medida

Es la explicación de algo que esta campaña ya había señalado dos veces sin conocer la causa:

- Fase 1 (F1-02): «Margen más estrecho: `verificar-cita/pass-advertencia-sala` (1.00 contra 0.80). Es el caso con menor poder discriminante de la suite.»
- Fase 7 (F7-02): al comparar el caso nuevo, «1.00 contra 0.50 deja más holgura que `pass-advertencia-sala` (1.00 contra 0.80)».

El 0.80 de la rota no es un margen estrecho legítimo: es un punto regalado. Sin el falso positivo, la rota sacaría menos y el caso discriminaría mejor.

Vale la pena notar que el síntoma era visible desde la fase 1 y la causa no: un margen anómalo en un solo caso de la suite es justo la señal que conviene perseguir hasta el patrón del grader.

## Nivel de la corrección

Es un defecto de **grader**, no de skill ni de producto: el harness hace lo correcto y la eval lo mide mal. En la pirámide corresponde al nivel 3 (verificación): el instrumento de medición es el que falla.

La corrección obvia es delimitar la palabra (`\bsala\b`), aunque conviene revisar también las otras tres alternativas del patrón y el resto de los graders de la suite por el mismo problema: `superad` es un prefijo deliberado y está bien, pero `reforma` y `corte temporal` podrían tener el mismo tipo de coincidencia accidental en otros mensajes.

**No se aplicó ningún cambio.** El operador lo corrige en la 0.1.2.
