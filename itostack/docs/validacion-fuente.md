# Validación forense del texto fuente

El harness se diseñó a partir de un texto pegado por el operador sobre la metodología de Lauren Tan. Antes de usarlo como especificación se cotejó con fuentes públicas (17-XI-2026). Se aplica el mismo criterio que a una cita: lo que no se pudo confirmar no se trata como hecho.

## Confirmado en fuentes públicas

| Afirmación | Fuente |
|---|---|
| pstack existe, es de Lauren Tan (@poteto) y se publicó como plugin de Cursor (`cursor/plugins/pstack`), con `/poteto-mode`, playbooks, principios, `/setup-pstack`, `poteto-agent` y Comment Sicko | github.com/cursor/plugins (vía flaviocopes.com/pstack.md, everydev.ai/tools/pstack) |
| La autora presentó pstack como ingeniera de Cursor («skills used 10,000 times last week») | cursor.com/cn/lp-team/lauren |
| SpaceX adquirió xAI el 2-II-2026; Cursor anunció en agosto de 2026 que pasaba a formar parte de SpaceX y su equipo se unía a SpaceXAI (Grok, Grok Build, Grok Bot, Cursor) | latent.space/wiki/spacexai |
| Perfiles de terceros describen a Tan como ingeniera del equipo central de Grok Bot (SpaceXSI) y reseñan su charla «11,000 Agent PRs a Month, 0.5% Reverted» | teamday.ai/ai/people/lauren-tan |
| La tesis «cada corrección debe convertirse en un chequeo determinista (lint, tipo, API) y no en prosa» | teamday.ai/ai/people/lauren-tan |
| Existe un ejemplo público de skill de verificación | github.com/poteto/verification-skill-example (citado en scrapbox.io/ohbarye/pstack) |

## No confirmado (⚠) o con discrepancias

- Cifras de productividad (2,000–2,500 PRs personales, 600 PRs de saneamiento, 11,000 PRs y 0.5 % de reversión, ~70 % del gasto en verificación, >200 agentes simultáneos): reportes propios o de terceros, sin auditoría independiente. El propio texto lo advierte.
- Conteos de pstack v0.15.9 (26 skills, 24 principios, 23 playbooks): ports comunitarios reportan otras cifras para v0.15.0 (p. ej. 47 skills, 23 playbooks, 23 principios). No se usaron como requisito.
- Guía interna de Lingxi Li, nombres de bots (Baltata, Shaoruru, Hogan, Craig, Quill, Jenny), horarios de dr eggbot y auditorías de 3:00/5:00: no verificados; se tomaron solo como inspiración de diseño (horarios de cron desfasados, un trabajo por bot).
- El video referido (canal ConquerAI) no se revisó.

## Observación sobre las herramientas del operador

La skill `scjn-api` del operador cataloga la «Undécima Época (vigente)», mientras su marco declara la Duodécima Época desde el 1-IX-2025 (AG 7/2025 (12a.)). Conviene actualizar ese catálogo; itostack reconoce «Duodécima» al normalizar épocas.

## Decisiones de diseño derivadas

- Lo transferible es el método (verificación observable, evals con reserva, correcciones convertidas en reglas, pirámide de guardias), no las cifras.
- Las reglas específicas de Dune (vetar `useEffect`, prohibir el 99 % de comentarios) no se copiaron: se sustituyeron por las reglas del stack y de la política de datos de Itosturre.
- La verificación formal (TLA+, Lean, Bombadil) se tradujo a pruebas por propiedades y exploración exhaustiva del contrato de veredictos, proporcionales al riesgo del dominio.
