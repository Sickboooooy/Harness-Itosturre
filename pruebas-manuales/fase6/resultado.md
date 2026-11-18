# Fase 6 · Pilar 3 Mejora continua — resultado

Detalle de los pasos 1 y 6 en `pruebas-manuales/fase6/correcciones-del-operador.md` y `pruebas-manuales/fase6/palanca-candidata.md`.

| ID | Función | Esperado | Observado | Estado |
|---|---|---|---|---|
| F6-01 | Dos correcciones iguales del operador → aviso del hook y filas en el TSV | aviso de repetición y 2 filas | A la **tercera** corrección se logró: «Esta corrección se repite (2 veces, clave «cierre-raiz-relativas-repo-rutas»)». 2 filas, misma clave, `pendientes_de_elevar` = 1 | OK, tras destapar D-13 y D-14 |
| F6-02 | `/itostack:corregir` → `propuesta.md` con su nivel, sin aplicar | propuesta nivel N | `registrar_correccion.py pendientes` listó la clave con 2 repeticiones; propuesta escrita en nivel **2** en `.itostack/mejora/propuesta.md`, con copia fechada en `.itostack/mejora/propuestas/`. **Nada aplicado** | OK |
| F6-03 | `/itostack:muestra-tu-trabajo`: decisión reversible e irreversible | exit 0 y exit 3 con detención | Reversible → exit 0. Irreversible → exit 3 y «⚠ IRREVERSIBLE: detente y pide confirmación antes de ejecutarla». Acatado: IT009 no se aplicó | OK |
| F6-04 | `/itostack:sin-relleno` sobre `pruebas-manuales/relleno.md` | REQUIERE PODA → LIMPIO | 9 hallazgos (exit 1) → tras una poda, `0 hallazgo(s) · LIMPIO` (exit 0) | OK |
| F6-05 | `/itostack:revision-salud` con los dos scripts | reportes, aunque sea en silencio | `salud_transcripciones.py`: 13 propuestas con señales reales. `salud_rutinas.py`: reporte generado, pero **la métrica está rota** (D-15) | OK con defecto |
| F6-06 | `/itostack:construir-palanca`: candidato sin escribir código | un candidato justificado | Preámbulo `cd … && R=$(cat raiz_plugin) && PYTHONUTF8=1 python "$R/scripts/…"`, 38 repeticiones medidas en una sesión. Sin escribir código | OK |
| F6-07 | `/itostack:interrogar` sobre `salidas/parrafo.md` | panel adversarial | **Panel reducido a un miembro**: Ollama no está instalado. El miembro Claude (`revisor-adversarial`) ya se ejecutó sobre este mismo archivo en la fase 3 (E7) | parcial · ver abajo |
| F6-08 | `revisar_ollama.py --rol adversarial` y `--rol juez` | skip si no hay Ollama | **skip** razonado, con el comportamiento del script verificado | OK (skip) |

## F6-01 — el paso que más información dio

Las dos primeras correcciones del operador **no** produjeron dos filas:

1. «No, te dije que en tus tablas de cierre uses rutas relativas…» → registrada.
2. «Una precisión de método: las correcciones aplican hacia adelante…» → **no registrada, sin aviso**.
3. Repetición literal de la primera → registrada, y el hook avisó de la repetición.

De ahí salieron **D-13** (el detector solo reconoce el registro confrontativo) y **D-14** (la clave agrupa por palabras del mensaje: cuatro paráfrasis de la misma corrección dan cuatro claves distintas). Ambas correcciones se aplicaron, incluida la restauración de los dos registros cerrados que había reescrito.

## F6-02 — propuesta de elevación (sin aplicar)

- **Nivel 2 · análisis estático.** `itostack/guardias/lint_itosturre.py` (regla nueva IT009) y `itostack/hooks/guardia_escritura.py`, que reusaría la misma regla.
- **Qué bloquearía:** una ruta absoluta del directorio de usuario (`C:\Users\…`, `/home/…`, `/Users/…`) escrita en una **fila de tabla Markdown** dentro de informes bajo `pruebas-manuales/`, `salidas/` y `docs/`.
- **Qué enseñaría el mensaje:** «usa la ruta relativa a la raíz del repositorio: `pruebas-manuales/fase4/resultado.md`».
- **Por qué no nivel 1:** las tablas de cierre son prosa Markdown escrita a mano, no salida de una API. No hay tipo ni estructura que haga el error imposible, que es lo que exige el nivel 1.
- **Por qué no nivel 4:** la propia skill dice que una línea de prosa no es solución si existe un nivel más fuerte, y el 2 es alcanzable.
- **Alcance acotado a propósito:** no aplica a `evidencia*.txt`, donde la ruta absoluta es transcripción literal de la salida de un comando, ni a los informes que genera itostack (`reporte_vvca.py`, `ensamblar_documento.py`), donde la ruta absoluta de la evidencia forma parte de la cadena de custodia. Restringirlo a filas de tabla evita esos falsos positivos sin perder el caso corregido.

## F6-05 — qué dijeron los reportes de salud

`salud_transcripciones.py --dias 2 --filtro Harness` (señal de frecuencia, sólida):

- 2 correcciones humanas → remite a `/corregir`.
- Error de herramienta repetido 3× («Exit code 1»).
- Guardia disparada 3×: «push forzado prohibido». **Dos de esas tres fueron mis propios intentos de *documentar* la denegación**, no acciones reales — el guardia inspecciona el texto del comando (O-02 de la fase 0). La señal viene inflada por esa asimetría.
- Comandos repetidos: 43×, 19×, 13×, 7×, 6×, 6×, 4×, 4×, 3×.
- 6 veredictos BLOCKED.

`salud_rutinas.py --dias 7 --filtro Harness --umbral 100000`: generó el reporte, pero sus cifras no son utilizables (D-15).

## F6-07 y F6-08 — el panel adversarial quedó en un miembro

`ollama` no está instalado (`command not found`), de modo que el panel multi-familia que distingue a `/interrogar` no puede ejercitarse. Se verificó que el script se comporta bien en ambas rutas de fallo:

| Caso | Resultado |
|---|---|
| Ollama ausente | «Ollama no responde en `http://127.0.0.1:11434/api/generate` … Inícialo con: ollama serve» · **exit 2 (BLOCKED)** |
| `--endpoint https://api.ejemplo-remoto.com` | «El revisor solo opera contra Ollama local: los datos no salen de la máquina.» · **exit 3** |

La guardia de privacidad funciona: rechaza un endpoint remoto antes de enviar nada.

El miembro Claude del panel (`revisor-adversarial`) **ya se ejecutó sobre `salidas/parrafo.md` en la fase 3 (E7)** y produjo 20 hallazgos con veredicto RECHAZAR el documento / CORREGIR el generador, de los que verifiqué en código las cuatro afirmaciones estructurales (D-07, D-08, D-09). El paso 4 de la skill —pasar por `/verificar-cita` toda cita que un revisor proponga— no aplica: ese revisor se negó explícitamente a proponer citas sustitutas sin verificar, que es el comportamiento correcto.

Repetir esa misma revisión, sobre el mismo archivo, con el mismo subagente y el mismo modelo, costaría del orden de 45 000–55 000 tokens (lo que costó en la fase 3) y no aportaría información nueva. Queda **a decisión del operador**, conforme a la regla 6 del plan.

---

# D-15 · Media — el «consumo por skill» no mide consumo

Dos problemas que se componen, ambos leídos en el código:

**1. `salud_rutinas.py:28-29` cuenta las lecturas de caché como consumo.** `tokens()` suma `cache_read_input_tokens`, que es el contexto completo releído en cada llamada. Sumarlo por mensaje cuenta el mismo contexto una vez por turno, y el total crece con el cuadrado de la longitud de la sesión. De ahí la cifra reportada: **126 245 841 tokens en una sesión**.

**2. `salud_rutinas.py:38-44` atribuye por skill de forma pegajosa.** `skill_actual` se fija al invocar una skill y todo mensaje posterior se le carga hasta que se invoque otra; no hay noción de que la skill terminó.

El efecto se ve en el propio reporte: `mantener-skill-verificacion` encabeza con 30 578 547 siendo un paso corto de la fase 4, porque fue la última skill invocada antes de un tramo largo de trabajo ajeno —el cierre de la fase 4 y toda la batería de guardias de la fase 5—, que se le cargó entero. `configurar-itostack`, temprana y con poco contexto, aparece con 3 612 176.

El ranking no dice «cuánto cuesta cada skill» sino «cuántos turnos hubo tras invocarla y qué tan grande era el contexto». Favorece a las skills invocadas tarde en sesiones largas. La proporción «verificación/generación 15 % / 85 %» arrastra el mismo sesgo.

**Por qué importa.** Es la entrada que `revision-salud` y `construir-palanca` deben usar para decidir dónde invertir. Con esta métrica la respuesta será siempre «la skill que precedió al tramo más largo de trabajo no relacionado». En esta fase lo evité usando solo los conteos de `salud_transcripciones.py`.

**Propuesta (sin aplicar).** Nivel 1 · diseño: excluir `cache_read_input_tokens` del total o reportarlo aparte con su nombre; y cerrar la atribución de una skill al terminar, en vez de dejarla pegada. Nivel 3 · prueba: una transcripción sintética con dos skills y un tramo intermedio sin skill, que falle si el tramo se carga a la skill anterior.
