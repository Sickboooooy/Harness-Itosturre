# Fase 6 · `construir-palanca` — candidato identificado (paso 1, sin escribir código)

El plan pide identificar un candidato con base en los reportes de salud. Solo se ejecutó el paso 1 de la skill; los pasos 2 a 6 (escribir el CLI, pruebas, podar la skill, evals, commit) quedan **sin hacer**, por la regla 1 del plan y porque tocarían `itostack/`.

## Qué señal usé, y cuál descarté

`salud_transcripciones.py` da conteos de comandos repetidos: es una señal de frecuencia, verificable y sin supuestos. La usé.

`salud_rutinas.py` da un ranking de «consumo por skill». **No la usé**, porque la medición está rota (D-15, abajo). Decidir dónde invertir con ese ranking apuntaría a la skill equivocada.

## El candidato

**La mecánica:** el preámbulo que precede a casi toda invocación de una herramienta del harness.

```
cd <proyecto> && R=$(cat .itostack/raiz_plugin) && PYTHONUTF8=1 python "$R/scripts/<herramienta>.py" <argumentos>
```

**Frecuencia medida** (`salud_transcripciones.py --dias 2 --filtro Harness`):

| Forma normalizada | Veces |
|---|---|
| `cd … && echo … &&` | 43 |
| `cd … && R=$(cat .itostack/raiz_plugin) &&` | 19 |
| `cd … && R=$(cat .itostack/raiz_plugin) echo` | 13 |
| `cd … && sed -n …` | 7 |
| `cd … && grep -rn …` | 6 |
| `cd … && export PYTHONUTF8=1 &&` | 6 |

Las tres formas con `raiz_plugin` o `PYTHONUTF8` suman **38 repeticiones en una sola sesión**.

**Entradas:** el subcomando (`tesis`, `url`, `app`, `lote`, `informe`, `auditar`, `iniciar`, `detener`…) y sus argumentos.
**Salida:** la misma de hoy, sin cambios en los veredictos ni en los códigos de salida (0 PASS · 1 FAIL · 2 BLOCKED · 3 uso).

**Qué resolvería, además de ahorrar tecleo.** Cada pieza del preámbulo es un error que ya ocurrió en esta campaña:

| Pieza | Error real que evita |
|---|---|
| `R=$(cat .itostack/raiz_plugin)` | El `raiz_plugin` no existe hasta que se configura el proyecto (fase 2); un agente que lo lea antes obtiene una ruta vacía. |
| `PYTHONUTF8=1` | Sin ella, las rayas y los ⚠ salen como `?` en la consola de Windows (O-03, fase 1). |
| `python` en vez de `python3` | `python3` es el alias de la Microsoft Store (D-03, fase 0). Las skills siguen diciendo `python3` en su prosa. |
| `cd <proyecto>` | Los scripts resuelven el proyecto desde el directorio actual; invocarlos desde otro sitio cambia dónde cae la evidencia. |

Un CLI único resolvería las cuatro en un solo lugar en vez de repetirlas en cada skill y en cada invocación.

**Forma propuesta (no implementada):** un envoltorio `itostack` en `scripts/` que resuelva la raíz, fije la codificación, elija el intérprete y despache al script correspondiente, de modo que las skills pasen de
`python3 "$R/scripts/verificar.py" tesis --registro X` a `itostack verificar tesis --registro X`.

**Qué se podaría después (paso 4, «resta antes de sumar»):** la línea `R=$(cat .itostack/raiz_plugin)` aparece en la cabecera de **todas** las skills del plugin; con la palanca, desaparece de todas.

**Riesgo a vigilar:** el envoltorio añade una capa entre el operador y el script. Si falla, debe fallar con veredicto y no con traceback — justo el error de D-11.

---

# D-15 · Media — el «consumo por skill» no mide consumo

`salud_rutinas.py` tiene dos problemas que se componen, ambos leídos en el código, no inferidos:

**1. Cuenta las lecturas de caché como consumo.** `salud_rutinas.py:28-29`:

```python
def tokens(uso: dict) -> int:
    return sum(int(uso.get(k) or 0) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
```

`cache_read_input_tokens` es el contexto completo releído en **cada** llamada. Sumarlo por mensaje cuenta el mismo contexto una vez por turno, de modo que el total crece con el cuadrado de la longitud de la sesión. De ahí la cifra que reportó: **126 245 841 tokens en una sesión**, implausible por tres órdenes de magnitud.

**2. La atribución por skill es pegajosa.** `salud_rutinas.py:38-44`: `skill_actual` se fija al invocar una skill y **todo mensaje posterior se le carga** hasta que se invoque otra. No hay noción de que la skill terminó.

El efecto combinado se ve en el propio reporte: `mantener-skill-verificacion` encabeza con 30 578 547, siendo un paso corto de la fase 4. Lo que ocurrió es que fue la última skill invocada antes de un tramo largo de trabajo ajeno a ella — el cierre de la fase 4 y toda la batería de guardias de la fase 5—, y ese tramo se le cargó entero. `configurar-itostack`, que corrió temprano con poco contexto, aparece con 3 612 176.

**Qué significa el ranking de verdad:** no «cuánto cuesta cada skill», sino «cuántos turnos ocurrieron después de invocarla y qué tan grande era el contexto para entonces». Favorece sistemáticamente a las skills invocadas tarde en sesiones largas.

**Por qué importa.** Es la entrada que `construir-palanca` y `revision-salud` deben usar para decidir dónde invertir. Con esta métrica, la respuesta siempre será «la skill que precedió al tramo más largo de trabajo no relacionado». La proporción «verificación/generación 15% / 85%» arrastra el mismo sesgo.

**Propuesta (sin aplicar).** Nivel 1 · diseño: excluir `cache_read_input_tokens` del total, o reportarlo aparte y con su nombre; y atribuir a cada skill solo los mensajes hasta que aparezca otra invocación de herramienta de nivel superior, o marcar el fin de la skill explícitamente. Nivel 3 · prueba: una transcripción sintética con dos skills y un tramo intermedio sin skill, que falle si el tramo se carga a la skill anterior.
