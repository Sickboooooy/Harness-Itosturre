# Ejecutor aislado de itostack (CR-2): plantilla, sin aprovisionar

Esta carpeta prepara la arquitectura aprobada por el operador para CR-2: una CI privada y separada, en Linux y con
ejecutores efímeros. Aquí no se aprovisiona nada. No hay repositorio creado, ni credenciales, ni claves, ni secretos.
La plantilla tampoco corre desde este repositorio: vive en una carpeta anidada y GitHub solo lee `.github/` en la raíz.

## Qué hay

| Archivo | Para qué |
|---|---|
| `plantilla/.github/workflows/holdout.yml` | Workflow del ejecutor. Se dispara solo a mano y cada corrida la aprueba una persona (environment `holdout`). Los permisos son mínimos y el ejecutor es `ubuntu-24.04` efímero. Cada secreto llega solo al paso que lo usa. |
| `plantilla/ejecutor/obtener_candidata.sh` | Trae el commit exacto de la candidata con una clave de despliegue de solo lectura. Verifica el SHA y descarta las reservas contaminadas `holdout-*` de la candidata. |
| `plantilla/ejecutor/verificar.sh` | Verificación previa. Cualquier falla deja la corrida sin evaluar y sin consumir el intento. |
| `plantilla/ejecutor/comprobar_versiones.py` | Exige las versiones exactas de las herramientas y la copia fijada del orquestador, archivo por archivo con su huella. |
| `plantilla/ejecutor/validar_reserva.py` | Valida la reserva nueva. Cada caso necesita una aprobación con autor ≠ aprobador, datos sintéticos declarados y la huella aprobada. |
| `plantilla/ejecutor/correr.sh` | Corre el holdout con el orquestador fijado del ejecutor, nunca con el de la candidata. Requiere CR-3.2b. |
| `plantilla/ejecutor/firmar.sh` | Firma el manifiesto con la clave privada del ejecutor (`ssh-keygen -Y sign -n itostack-holdout`). |
| `plantilla/ejecutor/versiones.json` | Lo verificado y lo pendiente de verificar. |
| `plantilla/ejecutor/known_hosts` | Claves de host de github.com. Está vacío: lo llena el operador. |
| `instanciar.py` | Copia la plantilla al repositorio del ejecutor. Falla cerrado (ver abajo). |

Hay dos piezas más, fuera de esta carpeta. Las dos son parte de la copia fijada del orquestador:

- `scripts/nucleo/atestacion.py`: firma y verificación con OpenSSH. «Aislada» solo vale con una atestación firmada sobre esa reserva (X10).
- `evals/humo_guardias.py`: prueba de humo de las guardias de la candidata en el ejecutor.

Las propiedades del workflow y de los scripts las comprueba `tests/test_ejecutor_ci.py`.

## Cómo cumple lo que pidió el operador

| Requisito | Cómo |
|---|---|
| **Repositorio y permisos independientes del constructor** | El ejecutor vive en otro repositorio, privado; `instanciar.py` rechaza un destino dentro de este. Del constructor solo tiene una clave de despliegue de solo lectura. El constructor no tiene ningún acceso al ejecutor. |
| **Reserva holdout nueva, no contaminada, fuera del repositorio dev** | La reserva vive en `reserva/` del repositorio del ejecutor. Las reservas `holdout-*` de la candidata se borran al obtenerla y nunca participan. |
| **Casos de un revisor humano independiente, aprobados por el operador** | `validar_reserva.py` exige una aprobación por caso con `autor` ≠ `aprobado_por`, fecha, `datos_sinteticos: true` y la huella del caso aprobado. Un caso editado después no corre. |
| **Workflows y dependencias fijados a versiones verificadas** | Cada `uses:` va fijado a un SHA de 40 hex. Las herramientas van en versión exacta y el orquestador en copia fijada archivo por archivo. Con cualquier `PENDIENTE-DE-VERIFICAR` no se instancia ni se evalúa. |
| **Ninguna credencial ni clave de firma accesible al constructor** | Los secretos son del environment del ejecutor. Ninguno se interpola en un script: pasan por `env` a un solo paso, como archivos temporales con permisos 600 que se borran al salir. |
| **Atestación vinculada al código, resultados, rúbrica, artefactos y evaluador** | Firma el manifiesto CR-3, que lleva la huella de la candidata y, por caso, `sha256_caso`, `sha256_rubrica`, `sha256_evaluador`, `sha256_artefacto` y juicios. También lleva la cabeza del diario encadenado y el sha256 de `resultados.json`. El constructor lo verifica con la clave pública (`atestacion.verificar`). |
| **Sin resultado aprobado si falla la infraestructura** | El orquestador (CR-3.2a) clasifica la falla de infraestructura como INCONCLUSA o REINTENTABLE, nunca ACEPTADA. Cualquier paso que falle corta el workflow antes de firmar. |
| **Publicación externa desactivada salvo autorización expresa** | La evaluación corre con `--no-publish` y escribe todo dentro del almacén del ejecutor. El único artefacto que sale es el manifiesto y su firma: sin trazas y sin casos, con 7 días de retención. |

## Qué falta, y quién lo hace

Lo marcado como **operador** requiere una autorización nueva. Aquí no se hizo nada de eso.

1. **CR-3.2b (constructor):** la CLI `orquestador.py ejecutar` con la evaluación y el juez reales, y la atestación de la reserva (X10) conectada a la compuerta.
2. **Verificar en un ejecutor real (operador):**
   - `node` y `codex` en versión exacta;
   - el SHA de `actions/upload-artifact`;
   - las claves de host de github.com, cotejadas fuera de banda.

   Después se quitan de `pendientes_de_verificar`.
3. **Fijar el orquestador (operador y revisor):**
   - copiar a `orquestador/` el subconjunto de itostack que usa, con su misma estructura (`evals/` y `scripts/nucleo/`), desde un commit revisado;
   - registrar en `versiones.json` → `fijados` la huella de cada archivo.
4. **Aprovisionar (operador):**
   - el repositorio privado;
   - el environment `holdout` con revisores obligatorios;
   - los secretos `CONSTRUCTOR_DEPLOY_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, `CODEX_AUTH_JSON` y `CLAVE_FIRMA_EJECUTOR`;
   - la variable `REPO_CONSTRUCTOR`;
   - la clave de despliegue de solo lectura en el repositorio del constructor;
   - la clave pública de firma en un archivo de firmantes del constructor.
5. **Reserva nueva (revisor independiente y operador):** los casos y `reserva/aprobaciones.json`. El constructor no los ve.

`instanciar.py` se niega mientras quede cualquier punto de 2 o 3.

## Riesgo abierto: la candidata corre dentro del ejecutor

Durante `correr.sh`, el código de la candidata (sus skills y hooks) se ejecuta en el mismo ejecutor que tres cosas:

- el orquestador fijado;
- el almacén de resultados;
- los tokens de evaluación.

Que no pueda leer los tokens, reescribir `resultados.json` ni alterar el orquestador después de `verificar.sh` depende del sandbox de `claude plugin eval` (bubblewrap). Sus fronteras **no se han observado en una corrida exitosa**: el laboratorio no tiene credencial.

| | |
|---|---|
| Riesgo | Alto |
| Reproducibilidad | No evaluada |
| Causa raíz | El instrumento de medición y lo medido comparten cuenta y sistema de archivos |

**Control propuesto, para CR-3.2b y el aprovisionamiento:**

- correr la evaluación con un usuario sin privilegios distinto del que corre el orquestador;
- dejar el orquestador y su almacén fuera del alcance de escritura de ese usuario;
- pasarle a ese usuario solo el token que la evaluación necesita.

**Criterio de aceptación:** una candidata **canario**, sintética, que intente las tres cosas (leer el token, escribir en el almacén, modificar el orquestador). Ninguna debe lograrlo, y la corrida debe quedar INCONCLUSA o RECHAZADA, nunca ACEPTADA.
