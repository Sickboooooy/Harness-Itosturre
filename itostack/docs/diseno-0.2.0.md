# Diseño de itostack 0.2.0: eliminar familias de defectos

Estado: **diseño aprobado en dirección por el operador (2026-11-19).** En curso en la rama `dev/itostack-0.2.0`; avance por incremento en la sección «Incrementos».

Criterio rector: no se optimiza para que un revisor deje de encontrar problemas. Se optimiza para que los invariantes críticos se cumplan **por construcción** y se demuestren con pruebas reproducibles, controles estructurales y evidencia verificable.

Este documento cubre las tres causas raíz del diagnóstico de la ronda 4 (`pruebas-manuales/fase-codex/diagnostico-ronda4.md`):

| Cambio | Causa raíz | Invariantes que pasa a demostrar | Familia que elimina |
|---|---|---|---|
| CR-1 · Citas estructuradas | Interpretar citas en prosa como frontera de seguridad | I-8, I-9, I-10 | Unos 19 hallazgos de cotejo heurístico (D-04, N-01, R1-8 … R4-9) |
| CR-2 · Reserva aislada por permisos | Reserva holdout en el árbol de trabajo, protegida por patrones de texto | I-5 | Unos 6 hallazgos de lectura de la reserva (R2-5, R2-7, R3-6, N-08, R4-6, R4-7) |
| CR-3 · Holdout orquestado por la compuerta | La compuerta confía en archivos que le entregan | I-7, más el entorno de la corrida | Unos 9 hallazgos (N-06, R2-1 … R3-8, R4-5, R4-10) |

## Modelo de amenaza

Es el mismo de 0.1.x: **un agente cooperativo que se equivoca, se apura o toma atajos**, no un atacante que falsifica archivos a propósito.

La diferencia en 0.2.0: los controles dejan de depender de que el agente no encuentre otra vía. Cada invariante lo garantiza:

- una frontera del sistema operativo (CR-2);
- un único productor de los datos que se deciden (CR-3);
- o una representación en la que el error no puede expresarse (CR-1).

**Fuera de alcance**, igual que en 0.1.x: el operador malicioso; la manipulación con privilegios de administrador; y la corrección jurídica del fondo de un escrito. Esta última la revisa siempre un abogado.

**0.2.0 no se declarará apta para producción jurídica.** Lo que demuestra es acotado: las citas de los entregables provienen de evidencia oficial o se marcan como no verificadas, y el proceso de mejora de skills mide con una reserva que el agente no puede leer.

---

## CR-1 · Citas estructuradas

### Invariantes

- **I-8.** Ninguna referencia jurisprudencial identificable (registro digital o clave de tesis) aparece en un entregable sin una de dos cosas: evidencia PASS vigente, o una advertencia visible de no verificada que el propio sistema produce.
- **I-9.** El rubro, la clave, el órgano y la época que muestra el entregable son los de la evidencia oficial, byte a byte después del formato.
- **I-10.** Ningún texto escrito por el agente cambia el estado de verificación de una cita: las marcas ⚠/❌ solo las emite el renderizador.

### Principio

**El agente nunca escribe una cita jurisprudencial; la pide.** Escribe la prosa y, donde va una cita, un marcador. El texto de la cita lo produce `ensamblar_documento.py` desde el almacén de evidencia. Los marcadores existen desde 0.1.0 (`[[CITA:registro|forma]]`); en 0.2.0 dejan de ser una opción y pasan a ser **la única vía**.

### Gramática de marcadores (borrador interno)

| Marcador | Significado | Se renderiza como |
|---|---|---|
| `[[CITA:<registro>]]` / `[[CITA:<registro>\|completa\|rubro\|clave\|corta]]` | Cita verificada | La cita oficial en la forma pedida, desde la evidencia vigente. Sin evidencia PASS vigente, el ensamblado **falla**: no se degrada a no verificada |
| `[[CITA_AJENA:<referencia>\|<fuente>]]` | Cita que hizo un tercero (contraparte, autoridad, resolución impugnada) y que se reproduce sin avalarla | La referencia tal como aparece en la fuente, con «⚠ CITA NO VERIFICADA: así la cita [fuente]; no se cotejó con el Semanario». **La referencia se comprueba literal en el documento fuente del expediente.** Así «ajena» es verificable y no sirve para lavar una cita propia |
| `[[NO_VERIFICADO:<texto>]]` | Afirmación propia que no se pudo verificar | El texto con «(⚠ NO VERIFICADO)» |
| `[[TRANSCRIPCION:<fuente>]] … [[/TRANSCRIPCION]]` | Transcripción literal de un documento del expediente que puede contener citas de terceros | El bloque citado con la advertencia de que sus citas no se verificaron. **El contenido se comprueba literal en la fuente** |

Reglas de la gramática. El analizador es formal, no un conjunto de expresiones regulares independientes:

- Un `[[` que no abre un marcador válido es un error.
- No hay marcadores anidados, salvo `CITA_AJENA` dentro de `TRANSCRIPCION`.
- `<registro>` es un registro digital; la clave la aporta siempre la evidencia.

### Flujo

1. El agente redacta un **borrador** (`borradores/**`) con prosa y marcadores.
2. **Guardia del borrador (alarma):** cualquier patrón de registro, clave de tesis, `rubro:` o marca ⚠/❌ **fuera de un marcador** → deny, con la indicación de qué marcador usar.
   - El detector de texto libre de 0.1.x se conserva solo como alarma. Un falso positivo produce una denegación de más; un falso negativo no exime, porque el entregable final igual pasa por el paso 4.
3. `ensamblar_documento.py` resuelve los marcadores y escribe el **entregable** en `salidas/**`, junto con un **manifiesto de procedencia** (`<entregable>.procedencia.json`, contrato `itostack/citas@1`) con:
   - el sha256 del entregable;
   - cada tramo renderizado, con su posición, tipo, registro y huella de la evidencia;
   - la versión del renderizador.
4. **Comprobación de entrega:** un entregable jurídico es válido solo si:
   - su manifiesto existe y el hash coincide (no se editó después de ensamblar);
   - todo patrón de cita del texto final cae dentro de un tramo del manifiesto;
   - no queda ningún `[[`.

   La aplican el hook de cierre, `validar-documento` y la compuerta de salida MCP. **Escribir a mano en `salidas/**` ya no se intenta interceptar por patrones de Bash: un archivo sin manifiesto válido simplemente no es entregable.**
5. El documento final tiene presentación jurídica natural: citas completas en el cuerpo, advertencias legibles y una nota de evidencia al final. No expone marcadores.

### Qué conserva y qué retira

- Se conserva `validar-documento` (auditar documentos **ajenos**) con la extracción heurística de `nucleo/citas.py`. Ahí cada cita extraída termina en `verificar.py` y en un informe renderizado, nunca en una exención.
- Se retiran del guardia de escritura las heurísticas que **eximen**: la marca junto a la cita, el cotejo de rubros declarados y el emparejamiento por proximidad. Con marcadores obligatorios no hay nada que eximir.
- El informe de verificación (`reporte_vvca.py`) ya es un renderizador. Se le agrega el manifiesto.

### Criterios de aceptación

| ID | Prueba | Tipo |
|---|---|---|
| A1-1 | Por propiedades: borradores generados con marcadores y texto libre que contiene registros, claves, «rubro:», ⚠ y ❌ en posiciones aleatorias (dentro y fuera de comillas, varias líneas) → el guardia deniega **si y solo si** hay un patrón fuera de un marcador | Hypothesis, más de 1000 ejemplos |
| A1-2 | Por propiedades: para borradores solo con marcadores y un almacén de evidencia generado, el rubro, la clave, el órgano y la época del entregable coinciden exactamente con la evidencia de cada tramo | Hypothesis |
| A1-3 | Un marcador `CITA` sin evidencia PASS vigente → el ensamblado falla y no escribe nada | Unitaria |
| A1-4 | `CITA_AJENA` o `TRANSCRIPCION` cuyo texto no aparece literal en la fuente → falla | Unitaria y propiedades |
| A1-5 | Entregable editado después de ensamblar (1 byte), o sin manifiesto → la comprobación de entrega lo rechaza | Unitaria y propiedades |
| A1-6 | Ninguna marca ⚠/❌ del entregable está fuera de un tramo emitido por el renderizador | Propiedades |
| A1-7 | Pase de mutantes sobre guardia, ensamblador y comprobación de entrega: 100 % detectados | `mutantes` |
| A1-8 | Evals de `redactar-con-citas` con el formato nuevo: autoprueba 1.00 en las referencias y menor que 1.00 en las rotas | autoprueba |

**Límites declarados** (no los cubre I-8):

- citas solo por nombre o descripción («la tesis de la Primera Sala sobre…»);
- citas textuales sin referencia;
- citas de legislación (artículos, DOF), que quedan para una versión posterior con su propio almacén de evidencia.

---

## CR-2 · Reserva holdout aislada por permisos

> **Antes de implementar, el operador aprueba el modelo de amenazas:** `docs/cr2-modelo-amenazas.md`. Ahí se descarta un usuario Linux dentro de la distribución WSL del operador, que `wsl -u root` atraviesa, y se recomienda una cuenta local de Windows con su propia distribución (O3).

### Invariante

- **I-5.** Ningún proceso que corra con la identidad del agente (el usuario del sistema operativo con el que corre Claude Code) puede leer la reserva holdout ni listar sus nombres de caso.

### Principio

**La frontera es el sistema operativo, no el texto del comando.** En 0.1.x, la reserva vive en `evals/<skill>/holdout-*` y la protegen guardias que inspeccionan rutas y comandos como texto. Cada guardia tiene otra vía: comillas, mayúsculas, variables, `python -c`.

En 0.2.0, la reserva vive donde el sistema operativo le niega el acceso al usuario del agente. Cifrarla no basta: una clave que el agente puede leer no es frontera. El cifrado en reposo (BitLocker o EFS) es opcional y no sustituye el control de acceso.

### Componentes

1. **Cuenta de servicio de la compuerta** (`itostack-compuerta`): una cuenta local sin privilegios de administrador.
   - Windows: `New-LocalUser`.
   - Linux/WSL: `useradd --system`.
2. **Almacén de la reserva**, fuera del repositorio:
   - Windows: `C:\ProgramData\itostack\reserva\`.
   - Linux: `/var/lib/itostack/reserva/`.

   Permisos:
   - Windows: la herencia se desactiva y solo quedan dos entradas, control total para `itostack-compuerta` y para SYSTEM. **Sin entrada para el usuario del operador ni para Administradores.** Un proceso no elevado del operador tiene el grupo Administradores solo como «deny-only», y sin esa entrada tampoco lo usaría.
   - Linux: dueño `itostack-compuerta`, modo `0700`.
3. **Almacén de decisiones** (`…\itostack\compuerta\`): historial, marcas, diario y manifiestos.
   - `itostack-compuerta` puede escribir; el operador solo lee.
   - Ya no hay marcas ni historial que el agente pueda borrar o editar.
4. **Ejecución de la compuerta como esa cuenta.** El operador la lanza a mano y escribe la contraseña: `runas /user:itostack-compuerta …` en Windows, `sudo -u itostack-compuerta …` con contraseña en Linux.
   - Sin `/savecred` y sin `NOPASSWD`: el agente no puede lanzar el holdout. Correrlo es un acto humano, que es lo que el protocolo quiere.
5. **Autoría de los casos holdout:** los escribe el operador, o un modelo de otra familia fuera de la sesión del agente, directamente en el almacén y desde una sesión de `itostack-compuerta`.
   - **Los casos `holdout-*` actuales se consideran quemados.** Los escribió el mismo agente que mejora las skills y están en la historia de Git. Pasan al conjunto de desarrollo.
6. **Trazas selladas:** las trazas del holdout (transcripciones y espacios de trabajo) quedan en el almacén de la reserva.
   - El operador puede revelarlas después de la decisión. Revelar marca esos casos como quemados y los mueve a desarrollo.
7. **Defensa adicional:** `guardia_lectura` y las reglas de Bash de 0.1.x se mantienen, pero ningún invariante depende de ellas.

Se consideraron y se descartaron como frontera principal:

- El sandbox de Claude Code: no está disponible en Windows nativo y su configuración la puede tocar la propia sesión.
- Una reserva remota en CI: es una frontera fuerte y puede servir para varios operadores, pero agrega un servicio externo y su costo. Queda como opción.

### Criterios de aceptación

| ID | Prueba | Tipo |
|---|---|---|
| A2-1 | Como el usuario del agente, cada vía de lectura sobre el almacén falla con «acceso denegado» del sistema operativo: Read, Grep y Glob de Claude Code; `cat`, `type`, `Get-Content` y `rg`; `python -c open(...)`; `robocopy` y `cp`; y el listado del directorio | Script en vivo, con evidencia adjunta |
| A2-2 | Centinela: un texto aleatorio dentro de un caso holdout no aparece en ningún archivo legible por el usuario del agente después de una corrida completa del holdout (repositorio, `%TEMP%`, perfil, objetos de Git, bitácoras) | Script en vivo, con búsqueda en todo lo legible |
| A2-3 | `git log -p --all` sin contenido de la reserva (búsqueda del centinela = 0) | Script |
| A2-4 | El almacén de decisiones no admite escritura del usuario del agente: crear, borrar y editar marcas fallan | Script en vivo |
| A2-5 | Scripts de instalación idempotentes (`instalar_compuerta.ps1` / `.sh`) que verifican sus propias ACL al terminar (`icacls` / `stat`) | Script con salida verificada |

---

## CR-3 · Holdout orquestado por la compuerta

> Contrato técnico (entorno, invocación, validación de resultados, identidad del evaluador, manifiesto): `docs/contrato-cr3.md`, con esquemas ejecutables en `evals/esquemas/`.

### Invariante

- **I-7.** Una candidata se acepta solo si se cumplen tres condiciones. Cada una se demuestra con un **manifiesto producido por la propia compuerta**, que se puede verificar recalculándolo:
  - desarrollo en 1.0;
  - holdout en 1.0 en todos los casos;
  - el juez de otra familia aprueba cada caso con la rúbrica asignada a la skill y cobertura completa.

### Principio

**La compuerta no recibe resultados ni veredictos: los produce.** En 0.1.x el operador corre la evaluación y el juez por su cuenta y entrega los archivos con `--resultados` y `--juez`. Cada archivo entregado es una superficie: el formato, la rúbrica, la fecha o la identidad pueden venir mal. R4-10 se resolvió en 0.1.2 validando en el consumidor, pero la clase sigue existiendo mientras haya archivos entregados.

### Transacción

`compuerta_holdout.py ejecutar --skill X` corre como `itostack-compuerta` (CR-2), en un entorno controlado (sin `ITOSTACK_*` y con PATH fijo), como una máquina de estados con **diario de solo anexar**. Cada paso queda en el diario con el sha256 de la entrada anterior:

1. **Precondiciones.** Candidata congelada, huella recalculada igual a la congelada y huella de la reserva igual. Se registran la identidad del juez congelado y las versiones de `claude`, `codex` y `python`.
2. **Reserva** del único intento, con marca exclusiva como en 0.1.x, ahora en el almacén de decisiones.
3. **Materialización:** una copia de la candidata, verificada por huella, más los casos de la reserva, en un espacio temporal del almacén.
4. **Evaluación:** `claude plugin eval <copia> --tag holdout --case "X.*" --runs 1 --scaffold --json`.
5. **Extracción** del artefacto de cada caso desde el directorio de resultados. El artefacto que califica cada rúbrica se declara en `por_skill.json`: archivo del espacio o último mensaje.
6. **Juicio:** por cada caso, la compuerta llama al juez como función (no por archivos) con la rúbrica de `por_skill.json` de la copia congelada.
   - La respuesta cruda se guarda, se valida contra el contrato y se califica.
   - Una respuesta BLOCKED se reintenta hasta K veces, todas registradas.
   - Si sigue BLOCKED, el estado queda **pendiente de juicio**: `reanudar` vuelve a llamar solo al juez sobre los artefactos sellados, que no cambian. Nunca se acepta.
7. **Decisión** única (marca exclusiva) y **manifiesto**:
   - huellas de la candidata y de la reserva;
   - identidad y versión del juez;
   - huella de la rúbrica;
   - por caso: puntaje de la evaluación, sha256 del artefacto, sha256 de la respuesta cruda, calificación y decisión;
   - la cabeza de la cadena del diario.

   La cabeza se imprime al operador y se anota en el historial.

`compuerta_holdout.py verificar-manifiesto <ruta>` recalcula todo:

- los hashes de los artefactos y de las respuestas guardadas;
- la calificación desde las respuestas crudas, que debe dar el mismo resultado;
- la cadena del diario;
- la rúbrica contra `por_skill.json` de la copia congelada.

`congelar` también se orquesta: corre la evaluación de desarrollo y al juez por sí misma. Desaparecen `--resultados` y `--juez` de toda la interfaz. La exención `--sin-juez-externo` se conserva, declarada y registrada.

### Prerrequisito

Un **spike en WSL** que corra `claude plugin eval` sobre un caso de desarrollo y documente el esquema real de `--json` y dónde quedan el espacio final y el último mensaje de cada caso. Su salida se guarda como fixture de las pruebas. Sin el spike no se escribe el paso 5.

### Criterios de aceptación

| ID | Prueba | Tipo |
|---|---|---|
| A3-1 | Integración con un `claude` y un juez falsos (como `CODEX_FALSO`): un juez que reprueba → RECHAZADA; uno que aprueba todo → ACEPTADA; uno BLOCKED → pendiente, nunca ACEPTADA, y reanudable | Integración |
| A3-2 | Por propiedades: para cada skill de `por_skill.json`, el juez recibe exactamente los bytes de su rúbrica; ningún argumento de la interfaz la cambia | Hypothesis |
| A3-3 | `verificar-manifiesto` detecta el cambio de cualquier byte en artefactos, respuestas, manifiesto o diario | Propiedades |
| A3-4 | La interfaz no acepta veredictos ni resultados externos para el holdout: `--juez` y `--resultados` no existen | Unitaria |
| A3-5 | Entorno controlado: `ITOSTACK_PROYECTO` o `ITOSTACK_MODO` definidos al lanzar no llegan a la evaluación. Cierra el límite de CR-4 documentado en 0.1.2 | Integración |
| A3-6 | Concurrencia: dos `ejecutar` simultáneos → exactamente una evaluación y una decisión (procesos reales) | Integración |
| A3-7 | Pase de mutantes sobre el orquestador: 100 % detectados | `mutantes` |
| A3-8 | Corrida real en WSL de un holdout completo con Codex de juez, con el manifiesto verificado | En vivo, con evidencia |

---

## Secuencia recomendada

```
CR-1 (sin prerrequisitos) ─────────────────────────────┐
Spike WSL de claude plugin eval ─► CR-3 (orquestador) ─► CR-2 (cuenta, ACL, migración de la reserva) ─► cierre 0.2.0
```

- **CR-1 primero.** No tiene prerrequisitos y protege lo que el despacho entrega: los escritos. Además elimina la familia más grande.
- **En paralelo, el spike de WSL**, porque bloquea el paso 5 de CR-3.
- **CR-3 antes que CR-2.** La cuenta de servicio de CR-2 ejecuta el orquestador de CR-3; sin orquestador, aislar la reserva obligaría al operador a manejar archivos a mano como cuenta de servicio.
- **CR-2 al final.** Requiere configuración del sistema que hace el operador (cuenta, contraseña, ACL) y casos holdout nuevos escritos por él.

## Incrementos

Cada incremento tiene una propiedad verificable y un criterio de terminación. No se agregan reglas sin una observación nueva que las motive, y no hay revisiones generales en bucle.

| Incremento | Propiedad verificable | Terminación | Estado |
|---|---|---|---|
| **CR-1.1** · Contrato `itostack/citas@1`: gramática formal, ensamblado desde la evidencia, manifiesto de procedencia y comprobación de entrega (`nucleo/procedencia.py`, `ensamblar_documento.py`, `verificar_entrega.py`) | Todo «[[» es un marcador válido o un error. Un patrón de cita fuera de un marcador impide ensamblar. Cada cita del entregable es exactamente la de su evidencia. Sin evidencia no hay documento. Cualquier byte cambiado, o una cita a mano, invalida la entrega. Las marcas ⚠/❌/✅ solo las escribe el ensamblador | `tests/test_procedencia.py` (17 pruebas, propiedades con más de 400 ejemplos) + 11/11 mutantes + `test_flujos` + autoprueba de `redactar-con-citas` | **PASS** |
| **Reserva contaminada** · `evals/reserva.json`: solo «aislada» admite un holdout | Para todo contenido del archivo de estado, `reservar` y `holdout` se niegan salvo con exactamente `{"estado": "aislada"}`; no dejan marcas ni historial | `TestReservaContaminada` + 3/3 mutantes | **PASS** |
| **CR-3.0** · Contrato técnico de CR-3 | Las salidas reales de `claude plugin eval` cumplen el esquema; faltar, sobrar o cambiar el tipo de un campo lo incumple | `tests/test_contrato_cr3.py` (18) | **PASS** |
| **CR-1.2** · Conectar la entrega a los guardias, migrar skills y evals | A1-1. Además: ningún archivo de `salidas/**` sin manifiesto válido sale por MCP ni pasa el cierre de sesión. El guardia de escritura deja de sugerir marcas escritas a mano | A1-1, A1-7, A1-8 | Siguiente |
| **CR-3.1** · Spike en WSL | Una corrida exitosa real cumple el esquema; fórmula del puntaje (R7) confirmada | Fixture nuevo en `tests/datos/` validado | **Bloqueado:** no hay distribución WSL (paso del operador) |
| **CR-3.2** · Orquestador | De A3-1 a A3-9 | Ídem | Después de CR-3.1 |
| **CR-2** · Cuenta de servicio y ACL | De A2-1 a A2-6 | Ídem | **Esperando la aprobación** del modelo de amenazas |

**Incoherencia transitoria, documentada hasta CR-1.2:** el guardia de escritura de 0.1.x todavía sugiere marcar a mano una cita ajena con ⚠ o ❌ cuando el agente escribe directamente en `salidas/**`. El ensamblador de CR-1.1 rechaza esas marcas en un borrador. La skill `redactar-con-citas` ya indica los marcadores nuevos.

## Protocolo de cierre de 0.2.0

1. Cada criterio A1-x, A2-x y A3-x en PASS con su prueba nombrada en la matriz de invariantes.
2. Pase de mutantes: 100 % detectados en los módulos de CR-1 y CR-3.
3. Mediciones en vivo con evidencia adjunta: A2-1, A2-2, A2-4 y A3-8. Se repiten I-1 e I-3 de 0.1.2.
4. Batería determinista completa: pytest, autoprueba, lint, `lint --diff`, `tsc` y `claude plugin validate`.
5. Una revisión externa **acotada a la matriz**, que responda una sola pregunta: ¿cada prueba ejercita de verdad su invariante? No es una revisión general en bucle.
6. CHANGELOG con «Límites conocidos» actualizados. Sin commit, push ni publicación sin autorización expresa.
