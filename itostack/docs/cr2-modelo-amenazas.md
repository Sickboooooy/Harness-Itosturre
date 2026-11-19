# CR-2 · Modelo de amenazas, identidad de servicio y aislamiento de la reserva holdout

Estado: **propuesta para aprobación del operador. No se implementa nada de CR-2 hasta que se apruebe.** Rama `dev/itostack-0.2.0`, 2026-11-19.

> **Decisión del operador (2026-11-19):** la arquitectura objetivo es una **VM o un ejecutor de CI aislados**, preferentemente Linux. La opción O3 (cuenta de Windows + WSL) no es la solución definitiva. El diseño del ejecutor y sus criterios de aceptación están en `docs/cr2-ejecutor-aislado.md`. Este documento conserva el modelo de amenazas (secciones 2 a 4), que sigue vigente.

Ningún paso de este documento pide, guarda ni transmite una contraseña a un agente o a un script.

## 1. Qué debe garantizar CR-2

- **I-5.** Ningún proceso con la identidad del agente puede leer la reserva holdout ni listar sus nombres de caso.
- **I-4 reforzado.** El agente no puede borrar ni editar el estado de la compuerta: marcas, historial, diario y manifiestos.
- **Integridad de la evidencia.** Las trazas y los artefactos de un holdout no aparecen en ninguna ubicación que el agente pueda leer, salvo que el operador los revele a propósito, y revelarlos quema esos casos.

La frontera es el **sistema operativo**. Cifrar no basta: una clave que el agente puede leer no es frontera. El cifrado en reposo (BitLocker) es opcional y no sustituye el control de acceso.

## 2. Activos

| Activo | Por qué importa |
|---|---|
| Casos de la reserva (contenido **y nombres**) | Si el agente los ve, el holdout deja de medir generalización |
| Trazas y espacios de trabajo del holdout | Contienen los prompts y las respuestas de los casos |
| Estado de la compuerta (marcas, historial, diario, manifiestos) | Si se edita o se borra, se puede repetir un intento o fingir una decisión |
| Credenciales de la cuenta de servicio para `claude` y `codex` | Con ellas se corre o se juzga como la compuerta |
| Contraseña de la cuenta de servicio | La conoce solo el operador |

## 3. Actores y amenazas

Modelo de amenaza declarado: **un agente cooperativo que se equivoca, se apura o toma atajos**. No es un atacante.

| ID | Actor | Amenaza | Vía concreta |
|---|---|---|---|
| T1 | Agente (usuario `licjo`, sin elevar) | Lectura accidental o «atajo» | Read, Grep o Glob de Claude Code; `cat`, `type`, `Get-Content`, `rg`; `python -c open(...)`; copiar el directorio |
| T2 | Agente | Ver los nombres de los casos | Listar el directorio, mensajes de error, historial |
| T3 | Agente | Repetir un intento o fingir una decisión | Borrar `.consumido` o `.decidido`; editar el historial o `evals/reserva.json` |
| T4 | Herramientas | Fuga por efecto lateral | Resultados de `claude plugin eval` dentro del plugin; informe publicado en claude.ai; temporales legibles; historia de Git; carpetas sincronizadas (OneDrive) |
| T5 | Operador | Error de procedimiento | Correr el holdout con su propia cuenta; guardar la contraseña con `runas /savecred`; teclearla en una terminal del agente |
| T6 | Agente | Elevarse | Pedir UAC o usar privilegios de copia de seguridad (`robocopy /B`) |

**Fuera de alcance:** un operador malicioso, malware con privilegios de administrador, el núcleo del sistema y el acceso físico.

## 4. Hechos que condicionan el diseño

H1 a H3 se verificaron en esta máquina durante la exploración de `claude plugin eval`. H4 es el comportamiento documentado de WSL; aquí no hay ninguna distribución instalada, así que lo comprueba A2-2 antes de dar CR-2 por cerrado.

- **H1.** `claude plugin eval` advierte en Windows que no puede sellar su directorio temporal: «directory modes do not restrict access on Windows». El sandbox propio de la evaluación no es una frontera aquí.
- **H2.** Con `--keep-temp`, ese temporal incluye una **unión a `C:\Users\licjo\.aws\sso`**. La exploración la quitó sin seguirla, y las credenciales quedaron intactas.
- **H3.** `~/.aws` ocupa 22 GB, y con eso el sandbox se niega a cualquier evaluación con Bash en Windows nativo.
- **H4.** **Una distribución de WSL pertenece a la cuenta de Windows que la instaló.** Esa cuenta entra como root sin contraseña (`wsl -u root`). Por eso un usuario Linux «de servicio» dentro de la distribución de `licjo` **no aísla nada** del agente, que corre como `licjo` y puede invocar `wsl.exe`. Esto descarta la opción que parecía más simple.

## 5. Identidad de servicio: opciones

| Opción | Frontera | Ventajas | Costos y riesgos |
|---|---|---|---|
| **O1.** Cuenta local de Windows `itostack-compuerta` y holdout en Windows nativo | NTFS por cuenta | Sin máquina extra | H1 y H3: el holdout **no puede correr** en Windows nativo en esta máquina. Descartada mientras sigan |
| **O2.** Usuario Linux dentro de la distribución WSL de `licjo` | Ninguna frente a `licjo` (H4) | Simple | **Descartada:** `wsl -u root` la atraviesa |
| **O3. Cuenta local de Windows `itostack-compuerta` con su propia distribución WSL** | NTFS de su perfil, más la pertenencia de la distribución a esa cuenta | Linux para `claude plugin eval` (evita H1 y H3); la distribución, su disco virtual y sus credenciales viven en un perfil que `licjo` no puede leer | Instalar WSL e iniciar `claude` y `codex` como esa cuenta (sesión interactiva del operador). Más disco |
| **O4.** Máquina o CI separados (por ejemplo, un repositorio privado con la reserva y un runner) | Otra máquina | La separación más fuerte; sirve para varios operadores | Servicio externo, costo y credenciales en el CI. Los casos son sintéticos, sin datos jurídicos, así que privacidad-local no lo impide |

**Recomendación: O3.** Es la única opción local que resiste H1 a H4. O4 queda como alternativa si la compuerta debe servir a más de un operador.

## 6. Mecanismos de aislamiento (con O3)

1. **Cuenta.** `itostack-compuerta`: cuenta local estándar, sin administración, sin inicio de sesión remoto y con una contraseña larga que **teclea el operador** al crearla. Ningún script la recibe.
2. **Almacén** en `C:\ProgramData\itostack\` o dentro del perfil de la cuenta, con herencia desactivada:
   - `reserva\`: control total para `itostack-compuerta` y SYSTEM. **Sin entrada para `licjo` ni para Administradores.** Sin «listar carpeta» para nadie más (T2).
   - `decisiones\` (historial, marcas, diario y manifiestos): escritura solo para `itostack-compuerta`; `licjo` solo lectura (T3).
   - `trazas\`: igual que `reserva\`. Revelar una traza es una acción explícita del operador que marca esos casos como quemados (T4).
3. **Ejecución.** El operador abre **su propia terminal, fuera de la sesión del agente**, y lanza `runas /user:itostack-compuerta …` tecleando la contraseña (T5).
   - Nunca `/savecred`: guardaría una credencial que cualquier proceso de `licjo`, el agente incluido, podría reutilizar.
   - El agente no puede lanzar el holdout: su terminal no es una consola interactiva y no tiene la contraseña.
4. **Credenciales de `claude` y `codex`.** El operador inicia sesión una vez, interactivamente, como `itostack-compuerta` dentro de su distribución WSL. Los tokens quedan en ese perfil, ilegible para `licjo`.
5. **Elevación (T6).** El agente corre sin elevar; con UAC, el grupo Administradores es «deny-only» en su token, y el almacén no le da entrada a ese grupo. Los privilegios de copia de seguridad exigen elevación, que el agente no puede aprobar: el aviso de UAC aparece en el escritorio seguro.
6. **Fugas laterales (T4).**
   - `--no-publish` y `--output-dir` dentro del almacén (contrato CR-3, V1).
   - Ninguna ruta del almacén dentro de OneDrive ni de una carpeta sincronizada.
   - Los casos nuevos **nunca entran a Git**.
7. **Defensa adicional.** `guardia_lectura` y las reglas de Bash de 0.1.x se mantienen, pero ningún invariante depende de ellas.

## 7. Plan de verificación (criterios de aceptación de CR-2)

Todo se ejecuta **como `licjo`**, el usuario del agente, sobre una reserva con un centinela aleatorio.

| ID | Prueba | Criterio |
|---|---|---|
| A2-1 | Cada vía de T1 y T2 sobre `reserva\` y `trazas\`: Read, Grep y Glob de Claude Code; `Get-Content`; `type`; `python open`; `robocopy`; `dir`; `icacls` | Todas fallan con «acceso denegado» del sistema operativo |
| A2-2 | `wsl -l` y `\\wsl.localhost\` como `licjo` | La distribución de la cuenta de servicio no aparece ni es accesible (H4) |
| A2-3 | Centinela después de un holdout completo | 0 apariciones en todo lo legible por `licjo`: repositorio, `%TEMP%`, perfil, OneDrive, objetos de Git y bitácoras |
| A2-4 | Crear, borrar y editar en `decisiones\` como `licjo` | Falla; la lectura funciona |
| A2-5 | Script de instalación idempotente | Al terminar verifica sus propias ACL (`icacls`) y falla si sobra una entrada |
| A2-6 | Holdout lanzado desde la terminal del agente | Falla: sin consola interactiva no hay contraseña |

**Terminación de CR-2:** de A2-1 a A2-6 en PASS con su evidencia, más un holdout real bajo O3 con el manifiesto de CR-3 verificado.

## 8. Riesgos residuales (lo que CR-2 no garantiza)

- Un operador que teclee la contraseña en una terminal del agente, o que use `/savecred`, rompe la frontera. Es un procedimiento, no una garantía técnica; el instructivo lo prohíbe expresamente.
- Si el operador eleva al agente o lo corre como administrador, la frontera desaparece.
- Los casos holdout los debe escribir **una persona o un modelo de otra familia fuera de la sesión del agente**. Si los escribe el mismo agente, vuelven a quedar contaminados, igual que los actuales.

## 9. Decisiones que necesito del operador

1. ¿Apruebas **O3** (cuenta local de Windows con su propia distribución WSL)? ¿O prefieres **O4** (máquina o CI separados)?
2. Crear la cuenta, instalar su distribución WSL e iniciar `claude` y `codex` en ella son pasos del operador, porque requieren privilegios y contraseñas. ¿Preparo el instructivo paso a paso y el script de ACL (A2-5) para que los ejecutes tú?
3. ¿Quién escribe los casos holdout nuevos: tú, o un modelo de otra familia en una sesión aparte?
