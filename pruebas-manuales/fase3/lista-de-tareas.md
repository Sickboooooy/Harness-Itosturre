# Fase 3 · Lista de tareas de modo-itosturre

**Meta:** ejecutar la fase 3 del plan de prueba integral (pilar 1 jurídico, modo fixture) y entregar la tabla de resultados con evidencia.
**Prueba (terminado cuando):** los 8 veredictos de `verificar-cita` coinciden con lo esperado; los 2 informes de `validar-documento` dan 1 PASS / 1 FAIL / 1 BLOCKED y FAIL por rubro truncado; `salidas/parrafo.md` existe con `[^ev1]` y `[^ev2]`; el borrador con `[[CITA:FICT-0404]]` imprime `ENSAMBLADO: BLOCKED` sin escribir archivo; `evidencia_db.py auditar` imprime `Integridad: OK`.

## 1 · Principios leídos (`principios/INDICE.md`)

Los 13 principios en una pasada. Aplican a esta fase: **demuestralo** (nada se cierra sin artefacto), **falla-cerrado** (ante la duda BLOCKED), **no-inventar** (ningún registro ni rubro sale de la memoria: todo se lee de `basico.json`), **corte-temporal** (FICT-0002 es de Segunda Sala y Décima Época), **privacidad-local** (modo fixture, sin red real).

## 2 · Playbook elegido: `playbooks/orquestacion-multietapa.md`

Es trabajo de varias etapas y varios subagentes. Entre este y `validacion-forense.md` elegí el más abarcador, como manda la regla 3; `validacion-forense` se aplica dentro del paso 4 de la etapa de `validar-documento`.

### Pasos copiados palabra por palabra

1. Descomponer la meta en etapas, cada una con una compuerta verificable (comando y veredicto esperado).
2. Asignar a cada subagente un único trabajo y sus anti-trabajos explícitos (p. ej. «redacta, no envía»; «audita, no edita»).
3. Aislar escritores: un `git worktree` por agente que modifica archivos; los roles no son fronteras de credenciales.
   - `skip:` ningún subagente de esta fase escribe. `auditor-citas` audita sin editar y `revisor-adversarial` es de solo lectura por definición de su herramientas (Read, Grep, Glob). Sin escritores concurrentes no hay nada que aislar.
4. Ejecutar etapa por etapa; ninguna avanza sin su compuerta en PASS.
5. Registrar decisiones en la bitácora (`muestra-tu-trabajo`).
   - `skip parcial:` la bitácora se ejercita formalmente en la fase 6 (F6-03). Aquí solo se registra la decisión del paso 3 y la del sustituto de la lista de tareas, al pie de este archivo.
6. Integrar y correr la verificación final completa (pruebas, lint, rutas del mapa o lote de citas).

## 3 · Etapas y compuertas

| # | Etapa | Compuerta (comando) | Veredicto esperado |
|---|---|---|---|
| E1 | 8 casos de `verificar-cita` | `verificar.py tesis` por caso | PASS ×3, FAIL ×2, BLOCKED ×3 |
| E2 | Capturas PNG | abrir 1 PASS y 1 BLOCKED | franja FIXTURE visible |
| E3 | `verificar.py url` (DOF ficticio) | `--contiene` presente / ausente | PASS y FAIL |
| E4 | `validar-documento` ×2 + `auditor-citas` | informe + auditoría | 1 PASS/1 FAIL/1 BLOCKED; FAIL por rubro truncado |
| E5 | `redactar-con-citas` ×2 | `ensamblar_documento.py` | `salidas/parrafo.md` con `[^ev1]`/`[^ev2]`; `ENSAMBLADO: BLOCKED` sin archivo |
| E6 | `corte-temporal` sobre FICT-0002 | análisis | ⚠ Sala extinta |
| E7 | `revisor-adversarial` sobre `salidas/parrafo.md` | reporte | hallazgos, sin editar |
| E8 | `evidencia_db.py recientes` y `auditar` | auditoría de huellas | `Integridad: OK` |

## Decisiones registradas (anticipo de `muestra-tu-trabajo`)

- **D3-1 · reversible.** El contrato del modo exige copiar los pasos «en la lista de tareas», pero esta sesión **no tiene la herramienta TodoWrite** (verificado con ToolSearch: ningún nombre de herramienta diferida coincide con todo/task/list). Decidí usar este archivo como lista de tareas y dejar constancia, en vez de omitir el paso 4 del contrato. Alternativa descartada: declarar el paso en `skip`, que habría ocultado la dependencia. Reversible: si la herramienta aparece, se vuelca este contenido.
- **D3-2 · reversible.** Playbook `orquestacion-multietapa` en lugar de `validacion-forense`, por abarcar las 8 etapas; el segundo se usa dentro de E4.
