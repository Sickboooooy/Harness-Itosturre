# Pirámide invertida de guardias

Regla: cada corrección repetida se resuelve en el nivel más fuerte posible. La prosa es el último recurso.

| Nivel | Mecanismo | Guardia en itostack | Qué impide |
|---|---|---|---|
| 1 · Diseño | Imposibilidad estructural | Contrato `itostack/citas@1`: marcadores (`[[CITA:…]]`, `[[CITA_AJENA:…|…]]`, `[[NO_VERIFICADO:…]]`) + renderizadores (`ensamblar_documento.py`, `reporte_vvca.py`) con manifiesto de procedencia | Que el agente escriba un rubro, una clave o una marca de verificación; que una cita ajena pierda su procedencia literal |
| 1 · Diseño | API única | `visitarConEvidencia()` en `lib/navegador_forense.ts` | Visitar un portal oficial sin captura y SHA-256 |
| 1 · Diseño | Datos inmutables | Triggers `BEFORE UPDATE/DELETE` en `evidencia_forense.db` | Alterar o borrar evidencia |
| 2 · Estático | Lint IT001 | Visita a la SCJN fuera del navegador forense | Scraping sin evidencia |
| 2 · Estático | Lint IT002 / IT003 | Postgres, Supabase, Mongo; FastAPI | Cambios de stack no decididos |
| 2 · Estático | Lint IT004 / IT005 | POST a servidores externos; LLM en la nube en código de producto | Fuga de datos legales |
| 2 · Estático | Lint IT006 | `executemany` sobre tesis, `/tesis/ids`, descargas masivas | Bases masivas de jurisprudencia |
| 2 · Estático | Lint IT007 | `waitForTimeout` | Esperas fijas que ocultan la causa raíz |
| 2 · Estático | Lint IT008 | Comentarios HACK/FIXME/workaround/«por ahora» | Parches que los agentes copian |
| 2 · Hook | `guardia_bash.py` | Push forzado, `gh pr merge`, PR sin `--draft`, `--no-verify`, `rm -rf` de raíces, scp/rsync/curl de subida, curl a portales oficiales, dependencias fuera de stack, commits en inglés o poco descriptivos, leer casos `holdout-*`; push a `main`/`master` o con `--force-with-lease` pasa por la compuerta humana | Acciones irreversibles o fuera de política |
| 2 · Hook | `guardia_escritura.py` | Lint sobre código nuevo; toda escritura a mano en `salidas/`, `escritos/`, `dictamenes/`, `*.juridico.md` y manifiestos; en `borradores/`, marcadores inválidos y citas o marcas escritas a mano (sobre el contenido resultante); edición de evidencia, holdout, compuerta y estado de la reserva | Entregables jurídicos sin procedencia; enseñar al examen |
| 2 · Hook | `guardia_lectura.py` | Leer o buscar dentro de un caso `holdout-*` (Read, Grep, Glob) | Enseñar al examen |
| 2 · Hook | `guardia_externo.py` | Enviar, publicar o compartir vía MCP pasa por la compuerta humana; un envío que nombra un entregable que no supera `verificar_entrega` se deniega; un texto con citas sin evidencia se deniega (heurística del mensaje) | Mensajes externos no revisados; entregables sin procedencia |
| 2 · Hook | Compuerta humana (`_comun.compuerta_humana`) | Pregunta solo en los modos que de verdad preguntan (default, acceptEdits, plan); en auto, dontAsk o bypassPermissions deniega (B-02). Excepciones curadas por el operador en `acciones_externas_permitidas` | Un «ask» que el anfitrión aprueba sin mostrarlo |
| 2 · Hook | `guardia_cierre.py` | Afirmar «verificado», «funciona» o «las pruebas pasan» sin la salida que lo pruebe; terminar con un entregable de la sesión que no supera `verificar_entrega` (BLOCKED) | Éxitos declarados sin evidencia; entregables sin procedencia |
| 3 · Verificación | `verificar.py`, `verificar_entrega.py` (manifiesto completo y coherente, reverificado contra evidencia y fuentes vivas), rutas del mapa, pytest, evals, propiedades | Regresiones funcionales y de contrato |
| 4 · Prosa | `CLAUDE.itostack.md` (7 líneas), skills, playbooks | Juicio que aún no se puede automatizar |

## Excepciones auditables

En código: `# itostack: permitir IT00X — <justificación de al menos 10 caracteres>` en la misma línea o la anterior. Sin justificación, la excepción no vale. En entregables jurídicos no hay excepciones escritas a mano (desde 0.2.0, CR-1.2): una cita ajena va en `[[CITA_AJENA:referencia|fuente]]` y una afirmación sin verificar en `[[NO_VERIFICADO:…]]`; las marcas ⚠/❌ las escribe el ensamblador.

## Agregar una regla

`/corregir` propone el nivel; al aprobarse, la regla se agrega a `REGLAS` en `guardias/lint_itosturre.py` (o al hook), con un mensaje que enseñe la alternativa y una prueba en `tests/test_guardias.py`.
