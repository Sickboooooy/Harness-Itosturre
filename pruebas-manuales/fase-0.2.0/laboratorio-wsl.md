# Laboratorio WSL para `claude plugin eval` (insumo del contrato de CR-3)

Fecha: 2026-11-19. Rama `dev/itostack-0.2.0`. Autorizado por el operador: preparar el procedimiento de instalación y hacer pruebas exploratorias con datos exclusivamente sintéticos, después de las comprobaciones previas. No se modificó `~/.aws`, no se eliminó ninguna credencial y no hubo limpiezas automáticas riesgosas.

**No es el ejecutor aislado de CR-2.** El operador eligió una VM o un CI para eso. Este laboratorio es local y desechable: sirve para conocer el comportamiento real de `claude plugin eval` en Linux.

## Procedimiento (reproducible)

Scripts en `lab/`. Todo lo que corre dentro del laboratorio entra **por stdin**, porque con las unidades de Windows desmontadas no hay rutas compartidas; además, la conversión de rutas de Git Bash altera los argumentos (`MSYS_NO_PATHCONV=1`).

| Paso | Comando (desde Git Bash, en la raíz del repositorio) | Resultado |
|---|---|---|
| 1 · Instalar | `wsl.exe --install Ubuntu-24.04 --name itostack-lab --no-launch` | Ubuntu 24.04.5, distribución propia; se quita con `wsl.exe --unregister itostack-lab` |
| 2 · Configurar (root) | `wsl.exe -d itostack-lab -u root -- bash -s < lab/configurar.sh` y `wsl.exe --terminate itostack-lab` | Sin montaje de unidades de Windows, sin interoperabilidad ni PATH de Windows; usuario `lab` con la cuenta bloqueada (sin contraseña) y sin `sudo`; python 3.12.3, git 2.43.0 |
| 3 · Copiar el plugin | `tar -C itostack --exclude=node_modules … --exclude='holdout-*' -cf - . \| wsl.exe -d itostack-lab -u lab -- tar -C /home/lab/itostack -xf -` | 200 archivos; **sin casos holdout** |
| 4 · Comprobar | `wsl.exe -d itostack-lab -u lab -- bash -s < lab/comprobar.sh` | 8/8 PASS (abajo) |
| 5 · Instalar Claude Code | `… -u lab -- bash -s < lab/instalar_claude.sh` | 2.1.327, la misma versión del lado Windows (contrato P2); **sin iniciar sesión** |
| 6 · Backend de sandbox (root) | `… -u root -- bash -s < lab/sandbox.sh` | bubblewrap 0.9.0 y socat 1.8.0.0 |
| 7 · Explorar | `cat lab/comprobar.sh lab/explorar.sh \| … -u lab -- bash -s` | Solo corre si las comprobaciones pasan en la misma invocación |
| 8 · Limpiar | `… -u lab -- bash -s < lab/limpiar.sh` | Temporal borrado, sin enlaces que seguir |

## Comprobaciones previas (`lab/comprobar.sh`)

Todas en PASS antes de cada exploración (`lab/exploracion-lab*.txt`):

1. Corre como `lab`, no como root.
2. `lab` no pertenece a `sudo`.
3. Ninguna unidad de Windows montada ni legible. Los directorios `/mnt/c` y `/mnt/d` existen, pero vacíos y sin montar; `/mnt/c/Users` no existe.
4. Interoperabilidad con Windows desactivada.
5. Ningún ejecutable de Windows en el PATH.
6. Ninguna variable de credenciales en el entorno (AWS, Azure, GCP, GitHub, Anthropic, OpenAI, HF, NPM).
7. Ningún almacén de credenciales en el home (`.aws`, `.ssh`, `gh`, `.git-credentials`, `.netrc`, docker, npm, codex, `.claude/.credentials.json`).
8. Copia del plugin completa y sin casos holdout.

**Dos defectos de mis propias comprobaciones, corregidos antes de dar nada por bueno:**

- La primera copia del plugin quedó **vacía**, por la conversión de rutas de Git Bash, y la comprobación «sin holdout» pasaba igual. Ahora exige además que la copia exista y esté completa.
- La primera comprobación de unidades miraba `/proc/mounts` con un patrón. Ahora prueba cada `/mnt/<letra>` con `mountpoint` e intenta leer `/mnt/c/Users`.

## Lo observado

| Corrida | Configuración | `error` | `partial` | `turns` | Código de salida |
|---|---|---|---|---|---|
| 1 | Sin backend de sandbox | «A shell tool (Bash or PowerShell) was granted but this machine cannot confine it (no sandbox backend…)» | **false** | 0 | **1** |
| 2 | Con bubblewrap y socat, sin sesión | «exit 1: Not logged in · Please run /login» | **true** (`auth_failed`) | 1 | **2** |

1. **Ni el código de salida ni `partial` distinguen una falla de infraestructura.** El código 1 es el mismo que un fallo de la candidata (puntaje por debajo del umbral). `partial` vale `false` en la corrida 1 aunque el agente nunca corrió. → Contrato CR-3, R6: decide `error` no vacío o un calificador con «grader threw»; el código y `partial` son solo información.
2. **Calificadores que «lanzan»:** sin artefacto, un calificador de archivo da «grader threw: … does not exist». El calificador `llm` da «grader threw: judge call failed: Not logged in». Los dos cuentan como no aprobados (`scored: true`), así que el puntaje sale de una evaluación que no ocurrió.
3. **En Linux el temporal se sella:** lo que escribe el agente queda en `sealed/` con modo 000 y el directorio en solo lectura. La limpieza necesita abrir permisos **solo en directorios** (`find -P -xdev -type d`, sin seguir enlaces ni cruzar montajes). No hubo enlaces simbólicos ni montajes en el temporal de Linux. En Windows, el temporal tenía una **unión a `~/.aws/sso` real**.
4. **El HOME aislado de la evaluación tiene señuelos vacíos** (`.aws`, `.ssh`, `.config/anthropic`, `.gitconfig`): enmascara los almacenes de credenciales reales.
5. **`out/trace.jsonl` registra los hooks**, y así apareció el siguiente hallazgo.
6. **Defecto de seguridad del plugin (corregido en CR-1.2): sin `node`, los guardias de itostack fallaban abiertos.**
   - La traza muestra el hook de inicio con «/bin/sh: 1: node: not found» y código 127.
   - Todos los hooks se lanzan con `node …/lanzar.mjs`. Claude Code solo bloquea cuando el hook sale con código 2; cualquier otro error lo trata como no bloqueante y deja pasar la acción.
   - Corrección: los cuatro hooks PreToolUse terminan en `|| { …; exit 2; }`.
   - Prueba: `test_plataforma.py::test_sin_node_las_guardias_previas_fallan_cerradas` ejecuta el comando exacto de `hooks.json` con un PATH sin `node` y espera 2. Mutante detectado.
   - El hook de cierre (Stop) no se cambió: salir siempre con 2 sin poder leer `stop_hook_active` atraparía la sesión en un bucle. Lo documento como residual.

## Lo que falta: una corrida exitosa

Para ver la forma de una corrida completa (calificadores con resultados reales, fórmula del puntaje, dónde queda el artefacto que califica el juez) hace falta que `claude` tenga **una credencial dentro del laboratorio**. Eso contradice «sin credenciales reales» y requiere una decisión del operador.

**Recomendación:** una clave de API dedicada, con tope de gasto, que el operador escriba directamente en la consola del laboratorio, nunca a través del agente. Se retira al terminar. La alternativa es esperar al ejecutor aislado de CR-2.

## Estado del laboratorio

`itostack-lab` queda **instalado y detenido**: sin credenciales, sin temporales y sin unidades de Windows. Para quitarlo: `wsl.exe --unregister itostack-lab` (borra la distribución entera). Es decisión del operador.
