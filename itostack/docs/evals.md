# Agent Evals: pruebas unitarias para skills

## Capas

| Capa | Herramienta | Costo | Qué demuestra |
|---|---|---|---|
| Autoprueba | `evals/autoprueba.py` | Gratis | Cada caso es resoluble (referencia = 1.00) y discrimina (agente que no verifica < 1.00) |
| Desarrollo | `claude plugin eval --tag desarrollo` | Tokens | La skill guía al agente real; el brazo sin plugin mide su aporte |
| Holdout | `compuerta_holdout.py holdout` | Tokens, una vez | La skill generaliza a casos que no vio quien la mejoró |
| Juez de otra familia | `revisar_codex.py --rol juez` (desarrollo) o `revisar_ollama.py --rol juez` (local, producción) | Tokens de Codex / local | Calificación por criterio (`si`/`no`/`no_aplicable`) contra la rúbrica congelada; el puntaje lo calcula `nucleo/juez.py`. Requisito de la compuerta |
| Propiedades | `tests/test_propiedades.py` | Gratis | Invariantes del contrato en todo el espacio de estados |

## Casos incluidos (datos ficticios `FICT-####`)

| Skill | Desarrollo | Holdout |
|---|---|---|
| verificar-cita | pass-exacto, fail-rubro-alterado, fail-inexistente, fail-epoca-discrepante, blocked-portal-caido, blocked-sin-registro, pass-advertencia-sala | holdout-fail-clave, holdout-blocked-estructura, holdout-pass-normalizacion |
| validar-documento | dev-tres-citas | holdout-rubro-truncado |
| demuestra-que-funciona | dev-pass, dev-blocked-selector | holdout-fail-bug |
| reproducir-y-corregir | dev-bug-minusculas | — |
| redactar-con-citas | dev-ensamblado | — |
| corregir | dev-eleva-a-guardia | — |

## Protocolo de aceptación

1. `python3 evals/autoprueba.py --caso "<skill>/*"` → todos coherentes.
2. `claude plugin eval ./itostack --tag desarrollo --case "<skill>.*" --scaffold --allow-tools Bash Write Edit --judge-model sonnet --json dev.json` hasta 1.0 en todos los casos (iterar con `/loop` y `mejorar-skill`).
3. Califica los artefactos de desarrollo con el juez de otra familia: `python3 scripts/revisar_codex.py --rol juez --rubrica evals/rubricas/<rúbrica>.md --archivo <artefacto> > juez-dev.json` (exit 0 = aprobado).
4. `python3 evals/compuerta_holdout.py congelar --skill <skill> --resultados dev.json --juez juez-dev.json` (fija la huella de skill + scripts + hooks + agentes + rúbricas + fixtures + casos de desarrollo, la huella de la reserva y la identidad del juez). Sin juez, solo con `--sin-juez-externo "motivo"`, que queda en el historial.
5. Holdout: `python3 evals/compuerta_holdout.py reservar --skill <skill>` consume el único intento ANTES de correr nada (también si después se interrumpe). Luego corre `claude plugin eval --tag holdout --case "<skill>.*" --runs 1 --scaffold --json h.json` (sin `ITOSTACK_PROYECTO` ni `ITOSTACK_MODO` en el entorno: redirigirían los casos a otro proyecto), califica el artefacto de CADA caso holdout con el MISMO juez (`revisar_codex.py --rol juez --caso <skill>.<caso> …`, uno por caso) y registra: `python3 evals/compuerta_holdout.py holdout --skill <skill> --resultados h.json --juez juez-holdout.json`. Un veredicto ilegible, fuera del contrato del juez o incompleto (sin puntaje) es BLOCKED: la compuerta no decide y el intento sigue reservado hasta registrar veredictos válidos. Resultados y veredictos deben ser posteriores a la reserva; un veredicto que califica artefactos de desarrollo no vale, y un artefacto que el juez ya reprobó en otra corrida (bitácora `.itostack/bitacora/juez.tsv`) cuenta como reprobado. Si falla, RECHAZADA y esa huella no puede reintentar. Cambiar de juez o de reserva después de congelar se rechaza, y una candidata congelada no se vuelve a congelar. Sin juez externo, la aceptación queda como «ACEPTADA SIN JUEZ EXTERNO».
6. Conserva las trazas (`evals/results/…/report.html`) y los veredictos del juez para auditoría humana. 10/10 no es certificación de producción.

## Requisitos de `claude plugin eval`

- Sesión de Claude Code autenticada (cada corrida es un `claude` hijo con tus credenciales).
- Para casos con Bash, sandbox: `sudo apt install bubblewrap socat`. Solo existe en Linux/macOS: en Windows nativo corre la autoprueba (funciona con Git Bash) y deja los evals nativos para WSL.
- Los scripts bash de los casos eligen intérprete con `_comun/python.sh` (`PY`): en Windows evitan el alias `python3` de la Store.
- `--scaffold` ejecuta los `preparar.sh` de los casos (son tuyos; revísalos). La primera corrida pide confiar en el plugin.
- Solo variables `EVAL_*` pueden definirse en `case.yaml`; por eso el andamiaje escribe `.itostack/config.json` en modo fixture.
- Banderas de regex con `flags:` (motor JavaScript): `(?i)` no funciona.
- Los graders negativos (`not_contains`) pasan aunque el agente no haga nada: cada caso combina graders negativos con positivos de mayor peso.

## Lo que la autoprueba ya atrapó

En la primera corrida, el caso `validar-documento/dev-tres-citas` salió incoherente: el grader «no-generaliza-exito» estaba invertido (exigía la frase que debía prohibir). La referencia correcta obtenía 0.88. Se corrigió antes de gastar un solo token en agentes.
