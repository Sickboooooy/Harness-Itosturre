# Exploración mínima de `claude plugin eval` (insumo del contrato de CR-3)

Fecha: 2026-11-19. Rama `dev/itostack-0.2.0`. Autorizada por el operador como prueba exploratoria mínima **en WSL**.

## Resultado en una línea

**WSL no se pudo usar:** no hay ninguna distribución instalada, e instalarla requiere crear un usuario Linux con contraseña, un paso del operador. La exploración se hizo en **Windows nativo**, con un solo caso de desarrollo, y la corrida misma quedó bloqueada por el sandbox de la evaluación. Aun así fijó ocho hechos del contrato. La prueba fiel sigue pendiente en WSL.

## Qué se corrió

```text
claude plugin eval itostack --case "verificar-cita.pass-exacto" --runs 1 --ablation none --scaffold --keep-temp
  --no-publish --trust-plugin --allow-tools Bash Write Edit --model claude-haiku-5-5 --max-cost-usd 2
  --output-dir <scratchpad> --json <scratchpad>/resultado.json --report <scratchpad>/informe.html
```

- Solo un caso de **desarrollo**; ningún caso holdout (la reserva está contaminada).
- `--no-publish`: el informe no salió a claude.ai.
- Sin `ITOSTACK_*` en el entorno.
- Costo: 0 USD, porque la corrida no llegó a lanzar al agente.

## Lo observado

1. **La corrida no ocurrió.** `error` = «the AWS (~/.aws) credential store on this machine is too large to check for symbolic links, so the Bash sandbox cannot reliably exclude it — a Bash-granting evaluation cannot run here».
   - `~/.aws` ocupa 22 GB. No se tocó: es el almacén de credenciales del operador.
   - Consecuencia: en esta máquina **ninguna** evaluación que conceda Bash corre en Windows nativo.
2. **Una corrida que no ocurrió igual entrega puntaje:** `score` 0, `passed` false, `graders` [] y `turns` 0.
   - La salida real anterior de Linux (`tests/datos/resultado_claude_plugin_eval.json`, sin sesión iniciada) es peor: `score` 0.2857 con `error` no vacío y `partial: true`.
   - La compuerta de 0.1.2 solo lee el puntaje. → Regla R6 del contrato.
3. **El sandbox no puede sellar en Windows:** «could NOT seal what the plugin under test wrote (directory modes do not restrict access on Windows)». → CR-2, hecho H1.
4. **Con `--keep-temp`, el temporal contenía una unión (junction) a `C:\Users\licjo\.aws\sso` real.** La CLI sugería limpiar con `Remove-Item -Recurse -Force`, que en Windows PowerShell 5.1 puede seguir una unión.
   - Se limpió quitando primero la unión, sin seguirla, con `[System.IO.Directory]::Delete(ruta, $false)`.
   - Se verificó que el destino quedó intacto: 1 archivo antes y 1 después. Recién entonces se borró el resto.
   - → Contrato CR-3, V4.
5. **Estructura del temporal:** `config/.claude.json`, `home/` (HOME aislado, con `cwd/` como espacio del caso, donde el andamiaje sí dejó `.itostack/` y `.git`), `out/` (vacío: sin corrida no hay `trace.jsonl`) y `tmp/`.
6. **Esquema de la salida** (`schemaVersion` 1, claude 2.1.327). Lo describe ahora `itostack/evals/esquemas/resultado-plugin-eval.schema.json`, que validan las dos salidas reales (`tests/test_contrato_cr3.py`). El esquema estricto detectó un campo que la primera lectura no vio: `graderMarkdown`, en los calificadores `llm`.
7. **`runsPerCase` informa el valor del caso (3)** aunque `--runs 1` lo cambie; las corridas reales se cuentan en `arms.with`.
8. **Opciones por omisión que importan**, según `--help`:
   - el informe se publica en claude.ai;
   - los resultados van dentro del plugin;
   - el calificador `llm` es Haiku;
   - la ablación «con y sin plugin» excluye del puntaje los calificadores `withOnly`.

## Pendiente en WSL (lo que la exploración no pudo ver)

Una corrida **exitosa**, con:

- la forma de `graders[]` con resultados reales;
- `tracePath` y el contenido de `out/`;
- la fórmula del puntaje;
- dónde queda el artefacto que califica el juez;
- los códigos de salida.

Detalle y criterio de cada una en `itostack/docs/contrato-cr3.md`, sección 8.

**Requisito del operador:** instalar una distribución, la de la cuenta de servicio si se aprueba la opción O3 de CR-2; crear su usuario e iniciar `claude` en ella. Con eso, el spike corre con el mismo comando.

## Archivos

- `itostack/tests/datos/resultado_plugin_eval_windows_bloqueado.json`: salida de esta corrida, con la ruta local reemplazada por `C:/ruta/itostack`.
- El informe HTML y la salida completa quedaron solo en el scratchpad de la sesión: no aportan nada que no esté en el JSON.
