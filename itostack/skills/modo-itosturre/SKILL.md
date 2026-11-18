---
name: modo-itosturre
description: Modo de trabajo persistente de Itosturre para cualquier tarea no trivial, jurídica o de desarrollo. Recibe una meta con prueba verificable, elige un playbook, copia sus pasos en la lista de tareas y no declara nada terminado sin evidencia PASS/FAIL/BLOCKED. Úsalo al redactar o validar escritos con citas, analizar criterios, computar plazos, corregir errores, crear funcionalidades, refactorizar o investigar código de Itosturre, o cuando el usuario diga "modo itosturre".
---

# Modo Itosturre

Router del harness. Convierte una petición en un procedimiento verificable.

**Raíz del plugin:** `R=$(cat .itostack/raiz_plugin)` (la escribe el hook de inicio; también es el directorio dos niveles arriba de esta skill). Si no existe `.itostack/`, ejecuta primero la skill `configurar-itostack`.

**Intérprete:** donde las skills dicen `python3`, usa el intérprete que anuncia el hook de inicio (en Windows suele ser `python` o `py -3`; `python3` puede ser el alias de la Microsoft Store).

## Contrato (no negociable)

1. **Meta + prueba.** Reformula la petición en una frase y su prueba: «terminado cuando …». Si no hay prueba posible, propón una y espera confirmación.
2. **Principios.** Lee `principios/INDICE.md` antes de planear. Es el primer elemento de la lista de tareas.
3. **Playbook.** Elige uno de la tabla. Si dudas entre dos, el más estricto.
4. **Copia literal.** Copia los pasos del playbook palabra por palabra en la lista de tareas. Un paso que no aplica se marca `skip: <razón>`; nunca se borra.
5. **Evidencia.** Ningún paso de verificación se cierra sin artefacto: `VEREDICTO: …` impreso por un script, con ruta y SHA-256.
6. **Tres veredictos.** PASS, FAIL o BLOCKED (`docs/contrato-veredictos.md`). Faltan datos, selector, permiso o portal → BLOCKED. Prohibido improvisar un PASS.
7. **Decisiones sin supervisión** → skill `muestra-tu-trabajo`. Una decisión irreversible se prepara y se detiene.
8. **Cierre.** Veredicto, evidencia (rutas), advertencias ⚠, pasos en `skip:` y riesgos. Nada más.

## Playbooks

| Situación | Playbook | Perfil |
|---|---|---|
| Redactar un escrito, promoción, proyecto o dictamen con citas | `playbooks/redaccion-escrito.md` | jurídico |
| Validar las citas de un texto ajeno (otra IA, contraparte, proyecto) | `playbooks/validacion-forense.md` | jurídico |
| Responder una consulta o analizar un criterio (solo lectura) | `playbooks/analisis-juridico.md` | jurídico |
| Computar un plazo o término procesal | `playbooks/computo-plazos.md` | jurídico |
| Corregir un error reportado | `playbooks/correccion-error.md` | desarrollo |
| Agregar una funcionalidad | `playbooks/nueva-funcionalidad.md` | desarrollo |
| Entender código sin modificarlo | `playbooks/investigacion.md` | desarrollo |
| Refactorizar o pagar deuda técnica | `playbooks/refactor-jardineria.md` | desarrollo |
| Trabajo de varias etapas o varios agentes | `playbooks/orquestacion-multietapa.md` | común |
| Tarea no estándar | `playbooks/resuelvelo.md` | común |
| Una skill falló, se desvió o se ignoró | `playbooks/mejora-skill.md` | común |

## Detención obligatoria

Impacto procesal grave (plazos, prescripción, caducidad, competencia, suspensión, admisión) o ambigüedad normativa: **DETENER** y pedir confirmación al operador antes de entregar. Se registra en la bitácora.

## Cuándo NO usar este modo

Una errata, una línea o una pregunta factual breve. El modo completo cuesta lectura y tokens; para lo trivial, haz el cambio mínimo y verifica con el comando más barato que lo demuestre.
