# Contrato de veredictos

Solo existen tres veredictos. Los produce un script, nunca el texto libre del agente.

| Veredicto | Etiqueta | Cuándo | Ejemplos |
|---|---|---|---|
| `PASS` | ✅ VERIFICADO | Hay captura con SHA-256 y todo lo cotejado coincide (o, en modo existencia, la fuente existe y su estructura se reconoce) | Rubro idéntico o con variaciones tipográficas; ruta del mapa recorrida sin errores |
| `FAIL` | ❌ NO VERIFICABLE — DISCREPANTE O INEXISTENTE | Hay evidencia **positiva** en contra | Rubro, clave, época u órgano discrepante; el portal responde «no encontrado»; la app no muestra lo esperado |
| `BLOCKED` | ⚠ NO VERIFICADO — BLOQUEADO | No se pudo comprobar | Portal caído o lento; estructura no reconocida; cita sin registro digital; selector ausente; app no arranca; falta Node/Playwright |

## Reglas de decisión (tesis)

1. No consultado (formato inválido, sin registro, observador falló) → BLOCKED.
2. Sin captura forense → BLOCKED.
3. Portal no disponible (error de red o HTTP ≥ 500) → BLOCKED.
4. El portal confirma inexistencia (HTTP 404 o cuerpo vacío) → FAIL.
5. Estructura no reconocida (sin rubro identificable) → BLOCKED.
6. El portal devuelve otro registro → FAIL.
7. Modo existencia → PASS (los datos se toman de la evidencia, no del agente).
8. Modo cotejo sin rubro ni clave → BLOCKED.
9. Cualquier campo discrepante → FAIL. Basta un rubro discrepante.
10. Rubro o clave citados que el portal no devuelve → BLOCKED; otros campos sin confirmar → advertencia.
11. En otro caso → PASS.

Normalización tolerada en el rubro: espacios, mayúsculas, comillas tipográficas, guiones, punto final y acentos (configurable con `comparacion.ignorar_acentos`). Cualquier cambio de palabra es discrepancia.

## VVCA

| Letra | Significado | Se marca verdadera cuando |
|---|---|---|
| V | Verificado | La fuente existe en el portal oficial |
| V | Validado | Los datos citados coinciden |
| C | Contextualizado | Se aplicaron reglas de corte temporal y obligatoriedad (solo tesis) |
| A | Auditable | Hay captura y huellas SHA-256 del resultado y los archivos |

## Códigos de salida

`verificar.py`: 0 PASS · 1 FAIL · 2 BLOCKED · 3 error de uso. `verificar.py lote`: 1 si hay algún FAIL, 2 si hay algún BLOCKED, 0 si todo es PASS.
