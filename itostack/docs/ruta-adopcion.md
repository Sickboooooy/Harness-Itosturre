# Ruta de adopción (de un agente a muchos)

La metodología de origen insiste: ir profundo con un agente antes de multiplicar hilos. Ruta propuesta para Itosturre:

| Semana | Paso | Criterio para avanzar |
|---|---|---|
| 1 | Instalar, `configurar-itostack`, prueba de humo con un registro real conocido; revisar la captura a mano y ajustar `config.json` si la estructura del SJF no se reconoce | Una verificación real PASS con captura correcta y una cita alterada en FAIL |
| 1 | Trabajar 3–4 días con un solo agente; el hook registra cada corrección en `correcciones.tsv` | Lista de correcciones repetidas |
| 2 | `/corregir` la más frecuente al nivel más alto (tipo, lint, hook) antes de tocar CLAUDE.md | Regla nueva con prueba |
| 2 | `crear-skill-verificacion` en `itosturre-validador`: mapa + una ruta real de punta a punta | Autoprueba de seis pasos en verde |
| 3 | Evals: `autoprueba.py` en verde; `claude plugin eval --tag desarrollo` en `verificar-cita` y `validar-documento`; compuerta holdout | Ambas skills ACEPTADAS |
| 4 | Bucle externo: cron de salud y auditoría; `agente-itosturre` en segundo plano con un worktree por escritor | Una semana sin supervisión constante y sin PASS falsos |

## Costos que hay que aceptar

- La verificación consume la mayor parte del presupuesto (el texto fuente reporta ~70 % en su equipo). Es la inversión correcta: un PASS falso en un escrito cuesta más.
- El modo completo es caro para erratas: el propio `modo-itosturre` dice cuándo no usarlo.
- Cada verificación real visita el portal: respeta su carga (una cita por llamada, sin descargas masivas, regla IT006).
