# itostack · Harness de Itosturre

Plugin de Claude Code que convierte la metodología de ingeniería de agentes de Lauren Tan (pstack / Grok Bot) en un harness especializado para **trabajo jurídico mexicano** y para **el desarrollo de Itosturre**. La tesis es la misma: el cuello de botella no es generar, sino la **confianza verificable**. Aquí esa confianza se apoya en evidencia forense (captura + SHA-256), evals con reserva holdout, mejora continua de skills y guardias deterministas.

## Los cuatro pilares

| Pilar | Qué hace en itostack | Piezas |
|---|---|---|
| **1 · Feedback Loop** | Nada funciona hasta verlo funcionar: citas contra el portal oficial y funcionalidades contra la app en ejecución, con veredicto PASS/FAIL/BLOCKED | `scripts/verificar.py`, `scripts/lib/navegador_forense.ts`, `verificador_fuente.ts`, `evidencia_web.ts`, `arrancar_app.py`, skills `verificar-cita`, `validar-documento`, `demuestra-que-funciona`, `reproducir-y-corregir` |
| **2 · Agent Evals** | Pruebas unitarias para skills sobre `claude plugin eval`, con soluciones de referencia y rotas, compuerta holdout de un solo intento y juez de otra familia | `evals/*/*/case.yaml`, `evals/autoprueba.py`, `evals/compuerta_holdout.py`, `scripts/revisar_ollama.py`, `tests/test_propiedades.py` |
| **3 · Mejora de skills** | Cada corrección repetida se registra y se eleva a una regla; chequeos de salud de transcripciones y tokens; palancas deterministas | hook `captura_correcciones.py`, `registrar_correccion.py`, `salud_transcripciones.py`, `salud_rutinas.py`, skills `corregir`, `mejorar-skill`, `construir-palanca`, `revision-salud` |
| **4 · Guardrails** | Pirámide invertida: diseño → lint/hooks → verificación → prosa | `[[CITA:]]` + `ensamblar_documento.py` (capa 1), `guardias/lint_itosturre.py` IT001–IT008 y `hooks/*` (capa 2), verificación y evals (capa 3), `CLAUDE.itostack.md` mínimo (capa 4) |

Detalle en [`docs/arquitectura.md`](docs/arquitectura.md).

## Instalación

Requisitos: Claude Code reciente, Python ≥ 3.10, Node ≥ 22.6, Git. Para correr evals nativos con Bash: `sudo apt install bubblewrap socat` (sandbox).

```bash
# 1. Desde Claude Code
/plugin marketplace add Sickboooooy/Harness-Itosturre
/plugin install itostack@itosturre

# 2. En cada proyecto, dentro de una sesión
/itostack:configurar-itostack
```

La skill inicializa `.itostack/` y, si falta, instala el navegador forense. Equivalente manual (la raíz del plugin la anuncia el hook de inicio de sesión):

```bash
python3 <raíz>/scripts/inicializar.py --proyecto . --perfil ambos
cd <raíz>/scripts && npm install && npx playwright install chromium   # una vez por máquina
echo "@.itostack/CLAUDE.itostack.md" >> CLAUDE.md
```

Para desarrollo local del plugin: `claude --plugin-dir ./itostack`.

## Uso diario

| Quiero… | Pide / ejecuta |
|---|---|
| Trabajar una tarea completa con método | `/itostack:modo-itosturre <meta> — terminado cuando <prueba>` |
| Saber si una tesis existe y está bien citada | `/itostack:verificar-cita` o `verificar.py tesis --registro … --rubro "…"` |
| Auditar las citas de un dictamen de otra IA | `/itostack:validar-documento` → `salidas/informe-vvca.md` |
| Redactar con citas que no se pueden inventar | `/itostack:redactar-con-citas` (marcadores `[[CITA:registro]]`) |
| Demostrar que algo funciona en la app | `/itostack:demuestra-que-funciona` |
| Reproducir y corregir un error | `/itostack:reproducir-y-corregir` |
| Que una corrección no se repita | `/itostack:corregir` |
| Medir una skill | `python3 evals/autoprueba.py` y `claude plugin eval ./itostack --tag desarrollo --scaffold` |

## Contrato de veredictos

`PASS` = evidencia observable y todo coincide · `FAIL` = evidencia positiva de discrepancia o inexistencia · `BLOCKED` = no se pudo comprobar. Falla cerrado: ante la duda, BLOCKED. Ver [`docs/contrato-veredictos.md`](docs/contrato-veredictos.md).

## Reglas Itosturre que el harness hace cumplir

- Consulta en tiempo real con Playwright; **no hay base masiva de jurisprudencia** (solo un registro de evidencia por consulta, inmutable). Regla IT006.
- Toda visita a la SCJN deja captura forense (IT001 + hook de Bash).
- Los datos legales no salen de la máquina (IT004, IT005, hook de Bash, compuerta MCP).
- Flask y SQLite para el MVP (IT002, IT003).
- Commits descriptivos en español; PRs de agente solo en borrador.

## Estructura

```
itostack/
├── .claude-plugin/plugin.json
├── skills/          21 skills (modo-itosturre trae 11 playbooks y 13 principios)
├── agents/          6 subagentes con un solo trabajo y anti-trabajos
├── hooks/           hooks.json + 6 guardias en Python estándar
├── guardias/        lint_itosturre.py (IT001–IT008)
├── scripts/         núcleo Python + observadores TypeScript (Playwright)
├── evals/           17 casos nativos (12 desarrollo, 5 holdout), fixtures ficticios, autoprueba, compuerta
├── plantillas/      CLAUDE.itostack.md, mapa, skill de verificación, modelos, cron
├── docs/            arquitectura, contrato, pirámide, evals, adopción, validación de la fuente
└── tests/           pytest (unidad, hooks, propiedades, flujos con navegador)
```

## Pruebas

```bash
cd itostack && python3 -m pytest tests -q      # requiere hypothesis y pyyaml para todo el set
python3 evals/autoprueba.py                    # la eval de la eval: referencias en 1.00, rotas < 1.00
claude plugin validate .
```

⚠ Las rutas del SJF (`/detalle/tesis/{registro}` y el microservicio público de tesis) vienen de la skill scjn-api del operador y se probaron solo contra fixtures. La primera verificación real debe revisarse a mano con su captura; si la estructura no se reconoce, el veredicto será BLOCKED (nunca PASS).
