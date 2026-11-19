# CR-5 · Compuerta de entrega independiente (diseño)

Estado: **diseño**. Nada de esto está implementado. Lo pidió el operador el 2026-11-19:

> «Diseñar una compuerta de validación independiente, obligatoria antes de publicar o enviar entregables jurídicos. El cierre de sesión no debe quedar atrapado en un bucle de denegaciones.»

## Por qué los hooks no bastan

Los hooks corren dentro de la sesión de Claude Code. Dependen de `node` y de un shell POSIX, y solo ven lo que pasa por las herramientas del agente. En la tabla, «vivo» es el resultado de `pruebas-manuales/fase-0.2.0/hooks_sin_node_vivo.py`: Windows, Claude Code nativo, PATH sin node, 2026-11-19.

| Hook | Modo | Sin `node` | Con `node` y sin Python | Garantía real | Evidencia |
|---|---|---|---|---|---|
| PreToolUse: Bash, escritura, lectura, MCP externo | cerrado | **Deniega.** El respaldo `\|\| { …; exit 2; }` de `hooks.json` sale con 2 | **Deniega.** `lanzar.mjs` falla cerrado | Bloquea la acción del agente | Vivo (Bash). `test_plataforma.py`: los 4 comandos exactos sin node, y D-02/D-03 |
| SessionStart | abierto | Sale con 127: **no bloqueante**, la sesión sigue | Deja pasar y avisa | Ninguna: es informativo | Vivo (código 127 registrado) |
| UserPromptSubmit | abierto | Sale con 127: no bloqueante | Deja pasar y avisa | Ninguna | Mismo mecanismo que SessionStart. No observado en vivo |
| Stop (`guardia_cierre`) | abierto | Sale con 127: **no bloqueante. La sesión termina sin comprobar la entrega** | Deja pasar y avisa | **Un recordatorio, como mucho una vez.** Bloquea el primer cierre si hay entregables de la sesión que no son PASS. El segundo llega con `stop_hook_active` y pasa | Vivo: termina en 2 turnos, sin bucle. `test_guardias.py::test_stop_hook_active_no_bucle`, `test_entrega.py::test_no_entra_en_bucle` |

Hay tres hallazgos.

1. **El respaldo «falla cerrado» depende de un shell POSIX.** `|| { …; exit 2; }` es sintaxis de sh. En Windows, Claude Code corre los hooks con Git Bash, verificado en vivo. Si una versión futura los corriera con PowerShell o cmd, el respaldo dejaría de aplicar. La guardia previa sin node volvería a ser no bloqueante, igual que el hallazgo del laboratorio WSL antes de CR-1.2.
   - *Riesgo:* alto si ocurre.
   - *Reproducible:* sí, con `hooks_sin_node_vivo.py`.
   - *Causa raíz:* el comando del hook se interpreta con un shell que el plugin no controla.
   - *Mitigación:* repetir `hooks_sin_node_vivo.py` en cada actualización de Claude Code, como requisito de publicación, y mantener la prueba de humo del ejecutor (`evals/humo_guardias.py`).
2. **Sin node, el cierre no comprueba nada.**
   - *Riesgo:* medio.
   - *Reproducible:* sí, en vivo.
   - *Causa raíz:* Stop es «abierto» por diseño, para no atrapar la sesión.
   - Hacerlo cerrado no arregla nada. Un Stop que bloquea sin node bloquearía siempre, y `stop_hook_active` lo dejaría pasar en el segundo intento. Sería un bucle o un control vacío.
3. **El Stop no es una compuerta, ni siquiera con node.**
   - Bloquea una vez y cede.
   - No ve lo que pasa fuera de la sesión: un archivo copiado a mano, un correo, otra herramienta.
   - Evitar el bucle es correcto. Pero significa que **ningún hook puede ser la compuerta previa a enviar**.

Conclusión: la compuerta tiene que vivir **fuera de la sesión y del agente**, sin depender de node ni del shell de los hooks. Los hooks quedan como defensa en profundidad y como recordatorio.

## Invariante

**E-1.** Un entregable jurídico se publica o se envía solo desde `entregas/`. Debe tener un registro de entrega cuya comprobación (`verificar_entrega`, contrato `itostack/citas@1`) dio PASS sobre **exactamente esos bytes**, con la confirmación de una persona.

## Diseño: `scripts/entregar.py`

La CLI es solo Python, con la biblioteca estándar y `nucleo`. No usa node. No corre como hook.

```
python scripts/entregar.py salidas/escrito.md --destinatario "Juzgado X (expediente 123/2026)" --canal "presentación física"
```

1. **Comprobar.**
   - Corre `verificar_entrega.revisar` sobre el documento y su manifiesto de procedencia, contra la evidencia y las fuentes vivas del proyecto.
   - Si no da PASS, sale con 2 y no copia ni registra nada.
2. **Confirmar con una persona.**
   - Exige una terminal interactiva: `stdin` y `/dev/tty` (o `CONIN$`) deben ser TTY. Si no lo son, sale con 2. El Bash del agente no tiene TTY.
   - Muestra la huella sha256, el destinatario, el canal y el resumen de la comprobación.
   - Pide teclear los primeros 8 caracteres de la huella. Si no coinciden, sale con 2.
3. **Congelar.**
   - Copia el documento y su manifiesto a `entregas/<fecha>-<sha8>-<nombre>`.
   - Vuelve a calcular la huella **de la copia**. Si difiere, borra la copia y sale con 2. Así se cierra el hueco entre comprobar y copiar.
   - Marca la copia como de solo lectura.
4. **Registrar.**
   - Agrega una entrada a `entregas/registro.jsonl` con: fecha, sha256 del documento y del manifiesto, resultado de la comprobación, versión de itostack, destinatario, canal y usuario del sistema que confirmó.
   - El registro va encadenado por huellas, igual que el diario M1 del orquestador CR-3: cada entrada lleva la huella de la anterior.
5. **Fallar cerrado.** Cualquier excepción sale con 2, sin copia y sin registro.

**Re-comprobación del lado receptor.**

```
python scripts/verificar_entrega.py --entrega entregas/<archivo>
```

- Coteja los bytes con su entrada del registro y verifica la cadena.
- Vuelve a correr la comprobación contra las fuentes vivas, porque la evidencia puede haber caducado desde la entrega.
- Puede correrla quien recibe o revisa el escrito antes de firmarlo o presentarlo.

### Defensa en profundidad (hooks; no son la compuerta)

- `guardia_escritura`: el agente no escribe en `entregas/**`. Solo `entregar.py` lo hace, fuera de la sesión.
- `guardia_bash`: deniega que el agente invoque `entregar.py`. La confirmación humana no se delega.
- `guardia_externo`: una herramienta MCP de envío o subida (correo, almacenamiento) que lleve un documento jurídico se deniega salvo que ese documento esté en `entregas/` y registrado.
- `guardia_cierre`: sigue avisando una sola vez y nombra `entregar.py`. No se vuelve cerrado (hallazgo 2).

## Criterios de aceptación (cuando se implemente)

| Tipo | Criterio |
|---|---|
| Positiva | Un documento PASS con confirmación correcta queda copiado, de solo lectura y registrado. La cadena verifica, y `--entrega` da PASS |
| Negativas | Cada uno de estos sale con 2, sin nada en `entregas/` y sin entrada en el registro: documento BLOCKED; sin TTY; confirmación incorrecta; documento cambiado entre comprobar y copiar; excepción a mitad del proceso |
| Negativas (registro) | Editar, quitar, reordenar o insertar una entrada se detecta. Una copia cambiada después de entregarse no pasa `--entrega` |
| Regresión | `verificar_entrega` sin cambios de comportamiento. El Stop sigue sin bucle (`test_no_entra_en_bucle`). Las guardias previas sin node siguen fallando cerradas |
| Mutación | Cada uno de estos defectos debe detectarse: comprobación omitida, aceptar sin TTY, huella de la copia sin cotejar, cadena del registro sin verificar, guardia de escritura que deja escribir en `entregas/` |
| Vivo | El agente intenta `entregar.py` y la guardia lo deniega, con node y sin node |

## Límites que esta compuerta no elimina

- **Una persona siempre puede enviar un archivo por otro medio**, por ejemplo con su cliente de correo. La compuerta no lo impide. La regla «solo desde `entregas/`» es organizacional, y la detecta la re-comprobación del lado receptor.
- **La confirmación por TTY es presencia humana, no una frontera de seguridad.** Un proceso local con los privilegios del usuario puede simular una terminal. Frente a un agente que lo intente, la barrera es la guardia de Bash, que es la capa 1 y tiene sus propios límites, documentados arriba.
- **Este diseño no hace apto a itostack para producción jurídica.** Eso requiere demostrar los invariantes críticos y la autorización expresa del operador.
