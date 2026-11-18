# Agent Evals: pruebas unitarias para skills

## Capas

| Capa | Herramienta | Costo | Qué demuestra |
|---|---|---|---|
| Autoprueba | `evals/autoprueba.py` | Gratis | Cada caso es resoluble (referencia = 1.00) y discrimina (agente que no verifica < 1.00) |
| Desarrollo | `claude plugin eval --tag desarrollo` | Tokens | La skill guía al agente real; el brazo sin plugin mide su aporte |
| Holdout | `compuerta_holdout.py holdout` | Tokens, una vez | La skill generaliza a casos que no vio quien la mejoró |
| Juez local | `revisar_ollama.py --rol juez` | Local | Segunda calificación de otra familia de modelos contra rúbrica congelada |
| Propiedades | `tests/test_propiedades.py` | Gratis | Invariantes del contrato en todo el espacio de estados |

## Casos incluidos (datos ficticios `FICT-####`)

| Skill | Desarrollo | Holdout |
|---|---|---|
| verificar-cita | pass-exacto, fail-rubro-alterado, fail-inexistente, blocked-portal-caido, blocked-sin-registro, pass-advertencia-sala | holdout-fail-clave, holdout-blocked-estructura, holdout-pass-normalizacion |
| validar-documento | dev-tres-citas | holdout-rubro-truncado |
| demuestra-que-funciona | dev-pass, dev-blocked-selector | holdout-fail-bug |
| reproducir-y-corregir | dev-bug-minusculas | — |
| redactar-con-citas | dev-ensamblado | — |
| corregir | dev-eleva-a-guardia | — |

## Protocolo de aceptación

1. `python3 evals/autoprueba.py --caso "<skill>/*"` → todos coherentes.
2. `claude plugin eval ./itostack --tag desarrollo --case "<skill>.*" --scaffold --allow-tools Bash Write Edit --judge-model sonnet --json dev.json` hasta 1.0 en todos los casos (iterar con `/loop` y `mejorar-skill`).
3. `python3 evals/compuerta_holdout.py congelar --skill <skill> --resultados dev.json` (fija la huella de skill + scripts + hooks + casos de desarrollo).
4. `python3 evals/compuerta_holdout.py holdout --skill <skill>` → una sola corrida; si falla, RECHAZADA y esa huella no puede reintentar.
5. Conserva las trazas (`evals/results/…/report.html`) para auditoría humana. 10/10 no es certificación de producción.

## Requisitos de `claude plugin eval`

- Sesión de Claude Code autenticada (cada corrida es un `claude` hijo con tus credenciales).
- Para casos con Bash, sandbox: `sudo apt install bubblewrap socat`.
- `--scaffold` ejecuta los `preparar.sh` de los casos (son tuyos; revísalos). La primera corrida pide confiar en el plugin.
- Solo variables `EVAL_*` pueden definirse en `case.yaml`; por eso el andamiaje escribe `.itostack/config.json` en modo fixture.
- Banderas de regex con `flags:` (motor JavaScript): `(?i)` no funciona.
- Los graders negativos (`not_contains`) pasan aunque el agente no haga nada: cada caso combina graders negativos con positivos de mayor peso.

## Lo que la autoprueba ya atrapó

En la primera corrida, el caso `validar-documento/dev-tres-citas` salió incoherente: el grader «no-generaliza-exito» estaba invertido (exigía la frase que debía prohibir). La referencia correcta obtenía 0.88. Se corrigió antes de gastar un solo token en agentes.
