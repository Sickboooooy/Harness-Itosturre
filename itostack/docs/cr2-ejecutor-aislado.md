# CR-2 · Ejecutor aislado de la reserva holdout (diseño)

Estado: **diseño para aprobación; sin aprovisionar ni implementar** (rama `dev/itostack-0.2.0`, 2026-11-19).

**Decisión del operador:** la arquitectura objetivo es una máquina virtual o un ejecutor de CI aislados, preferentemente Linux, con permisos independientes del agente constructor. La opción «cuenta de Windows + WSL» (O3 en `cr2-modelo-amenazas.md`) no es la solución definitiva. El modelo de amenazas de ese documento (secciones 2 a 4) sigue vigente.

Restricciones de este diseño:
- ningún paso pide, guarda ni expone una contraseña o un token a un agente o a un script del lado del constructor;
- no se aprovisiona nada sin una autorización nueva;
- los casos holdout nuevos los preparan y aprueban personas, con control independiente del agente.

## 1. Dos dominios de confianza

| | Dominio constructor | Dominio ejecutor |
|---|---|---|
| Dónde | La máquina del operador, donde corre el agente que mejora las skills | Una VM Linux o un ejecutor de CI que el agente no puede alcanzar |
| Tiene | El repositorio del plugin (la candidata) y la clave **pública** del ejecutor | La reserva holdout, las credenciales del ejecutor (`claude`, `codex`), la clave **privada** de firma, el diario y las decisiones |
| No tiene | La reserva, las credenciales del ejecutor, la clave privada, permisos sobre el ejecutor | Acceso de escritura al repositorio del constructor |

**El canal entre los dominios es angosto y va en un solo sentido por paso:**
1. **Hacia el ejecutor:** solo el identificador de la candidata (un commit del repositorio del constructor) y su huella congelada. Del constructor no viaja ningún caso, resultado ni veredicto.
2. **Hacia el constructor:** solo el **manifiesto firmado** de CR-3, con:
   - huellas e identificadores opacos de casos (un hash del nombre, porque el nombre de un caso ya revela qué prueba);
   - la decisión;
   - la identidad del evaluador.

   Ningún contenido de los casos ni ninguna traza viaja de vuelta.

## 2. Variantes

| | **V1 · CI en un repositorio privado separado** (recomendada) | **V2 · VM Linux local con Hyper-V** |
|---|---|---|
| Aislamiento | Otra máquina, efímera. La reserva vive en un repositorio privado al que **ninguna credencial del constructor** tiene acceso | Otro sistema operativo. Administrar Hyper-V exige elevación, que el agente no puede aprobar |
| Aprobación humana | Un *environment* con **revisores obligatorios**: cada corrida la aprueba una persona en la interfaz web, fuera de la sesión del agente | El operador inicia la VM y lanza la corrida desde su consola |
| Credenciales | Secretos del *environment*, que el operador captura en la interfaz web | Solo dentro de la VM, capturadas por el operador en su consola |
| Riesgos propios | El token de `gh` del constructor no debe tener alcance sobre el repositorio de la reserva: hay que usar otra cuenta u organización, o un token de grano fino limitado al repositorio del constructor | **VirtualBox o VMware, que corren como el usuario, no sirven:** el agente podría leer el disco virtual. Carpetas compartidas desactivadas |
| Datos | Salen a GitHub la candidata y los casos, que son **sintéticos**, y a las API de Anthropic y OpenAI, como en cualquier evaluación. Privacidad-local no lo impide porque no hay datos jurídicos reales; el ejecutor exige la atestación de que no los hay (X9) | No sale nada fuera de las API de modelos |

## 3. Garantías estructurales

1. **Manifiesto firmado.** El ejecutor firma el manifiesto con su clave privada (`ssh-keygen -Y sign`, de OpenSSH: sin dependencias nuevas). El constructor lo verifica con la clave pública versionada (`ssh-keygen -Y verify`). Así la decisión queda atada de forma comprobable a la identidad del ejecutor, y un manifiesto escrito a mano no pasa.
2. **«Aislada» deja de ser una palabra en un JSON editable.** `evals/reserva.json` del constructor solo admite «aislada» si va acompañado de una **atestación firmada por el ejecutor** (huella de la reserva, fecha y revisores que aprobaron los casos). El hook de escritura ya impide editarlo a mano, y sin la firma la compuerta lo trata como contaminada.
3. **Una sola corrida por huella** en el diario del ejecutor, de solo anexar. Volver a correr la misma candidata se rechaza allí, donde el agente no llega.
4. **CR-3 dentro del ejecutor:** el orquestador del contrato de CR-3 (entorno construido desde cero, `--no-publish`, R1 a R8) corre en el ejecutor. Una falla de infraestructura nunca es una evaluación válida (R6).

## 4. Ciclo de vida de la reserva, bajo control humano independiente

- **Autoría:** el operador, u otra persona que él designe, escribe cada caso directamente en el dominio ejecutor. El agente constructor nunca participa ni ve los casos.
- **Aprobación:** cada caso entra a la reserva con una revisión aprobada por una persona distinta de su autor, si el operador cuenta con otra. El registro (quién, cuándo y la huella del caso) forma parte de la atestación.
- **Datos sintéticos:** cada caso declara que no contiene datos jurídicos reales; el ejecutor rechaza casos sin esa declaración.
- **Revelar y quemar:** revelar las trazas de una corrida es un acto explícito del operador que marca esos casos como quemados. Pasan a desarrollo en el repositorio del constructor y se reponen.
- **Casos contaminados actuales:** los `holdout-*` del repositorio del constructor se retiran de la reserva. Se mueven a desarrollo o se borran, a elección del operador, cuando exista la reserva nueva. Hasta entonces `evals/reserva.json` sigue «contaminada».

## 5. Criterios de aceptación

| ID | Propiedad verificable | Cómo se comprueba |
|---|---|---|
| X1 | El agente no puede leer la reserva | Con las credenciales del constructor, `gh api` sobre el repositorio de la reserva → 404 o 403 (V1); el disco de la VM no se puede montar sin elevación (V2). Búsqueda del centinela en todo lo legible por el constructor → 0 |
| X2 | El agente no puede lanzar ni alterar una corrida | `gh workflow run` con el token del constructor → 403; una corrida sin aprobación humana no arranca (V1). La VM no expone servicios al anfitrión (V2) |
| X3 | Ningún contenido de los casos sale del ejecutor | Centinela en cada caso; búsqueda en el manifiesto, los artefactos publicados y los registros de la corrida → 0 |
| X4 | Un manifiesto alterado o no firmado se rechaza | El constructor rechaza cualquier byte cambiado, una firma de otra clave o la falta de firma (pruebas con manifiestos manipulados) |
| X5 | Una falla de infraestructura nunca acepta | Corrida con credenciales inválidas → BLOCKED o REINTENTABLE, nunca ACEPTADA (contrato CR-3, R6) |
| X6 | Entorno reproducible | El manifiesto registra la huella de la imagen del ejecutor (contenedor o VM) y las versiones de `claude`, `codex` y `python`; otra imagen → BLOCKED |
| X7 | Un intento por candidata | Segunda corrida con la misma huella → rechazada por el diario del ejecutor |
| X8 | Solo casos aprobados por personas | Un caso sin registro de aprobación → el ejecutor se niega |
| X9 | Solo datos sintéticos | Un caso sin declaración de datos sintéticos → el ejecutor se niega |
| X10 | «Aislada» no se puede declarar a mano | Con `reserva.json` en «aislada» sin atestación firmada válida, la compuerta del constructor la trata como contaminada |

**Terminación de CR-2:** de X1 a X10 en PASS con su evidencia, más un holdout completo con una reserva nueva, aprobada por personas, cuyo manifiesto firmado verifique el constructor.

## 6. Qué haría falta del operador (sin aprovisionar todavía)

1. Elegir V1 (CI) o V2 (Hyper-V).
2. **V1:** una cuenta u organización de GitHub separada, o un token de grano fino para el constructor limitado a su repositorio. El repositorio privado de la reserva, su *environment* con revisores obligatorios y sus secretos los captura el operador en la interfaz web.
3. **V2:** activar Hyper-V (requiere administración), crear la VM Linux sin carpetas compartidas, e iniciar `claude` y `codex` dentro de ella.
4. Generar la clave de firma **dentro** del ejecutor y versionar solo la pública en el repositorio del constructor.
5. Designar quién escribe y quién aprueba los casos nuevos.

## 7. Cambios del lado del constructor (después de la aprobación)

- `compuerta_holdout.py importar <manifiesto> <firma>`: verifica la firma, el esquema y que la huella sea la congelada; registra la decisión. Sustituye a `reservar` y `holdout` locales.
- `reserva_bloqueada()` exige la atestación firmada para aceptar «aislada» (X10).
- Retiro de los `holdout-*` contaminados del repositorio del constructor.
