# Fase 6 · Paso 1 — captura de correcciones del operador

El plan pide «dos correcciones iguales» para disparar el aviso del hook y ver dos filas en `.itostack/mejora/correcciones.tsv`. El operador dio dos correcciones. **Solo una se registró**, y eso destapó dos defectos del pilar 3.

## Las dos correcciones

| # | Texto del operador | ¿Hook la registró? | Clave |
|---|---|---|---|
| 1 | «No, te dije que en tus tablas de cierre uses rutas relativas a la raíz del repo, no rutas absolutas de C:\Users.» | **Sí** · aviso «Corrección registrada» | `cierre-raiz-relativas-repo-rutas` |
| 2 | «Una precisión de método: las correcciones aplican hacia adelante. Si un registro ya está cerrado, no lo reescribas; agrégale una nota fechada que diga qué cambió y por qué.» | **No** · sin aviso, sin fila | — |

Estado del registro tras ambas: **1 fila, 1 clave distinta, ninguna con n ≥ 2**. El umbral de elevación (`inicio_sesion.py`, `n >= 2`) no se alcanzó.

## Ambas correcciones fueron aplicadas

1. Las tablas de cierre usan rutas relativas a la raíz del repositorio desde este punto.
2. Los dos registros ya cerrados que había reescrito (`pruebas-manuales/fase0/resultado-011.md` y `pruebas-manuales/fase2/resultado.md`) fueron **restaurados a su contenido original**, y en su lugar llevan una nota fechada al pie que explica qué cambió y por qué.

La segunda corrección señaló una inconsistencia real: en la fase 5 me negué a reescribir una fila de la bitácora por ser registro de auditoría, y poco después reescribí dos registros de fase cerrados. El criterio ahora es uniforme: un registro cerrado no se reescribe, se le anexa nota fechada.

---

# D-13 · Alta — el detector de correcciones solo reconoce el registro confrontativo

`captura_correcciones.py:21-26` exige que el mensaje contenga uno de estos marcadores: un «no» al **inicio** de la frase, «te dije», «ya te dije / ya te había dicho», «otra vez», «de nuevo», «eso está mal», «eso no es», «incorrecto», «no inventes», «deja de», «no hagas», «nunca uses/hagas/pongas/escribas», «siempre usa/haz/pon/escribe», «te equivocaste».

Una corrección redactada con calma no contiene ninguno. Medido con el propio módulo del hook:

```
1a corrección («No, te dije que…»)      detectada=True   clave=cierre-raiz-relativas-repo-rutas
2a corrección («Una precisión de método: … no lo reescribas…»)   detectada=False
```

La segunda **sí** contiene «no lo reescribas», pero el patrón exige «no» al inicio de la frase o las formas fijas «no hagas» / «nunca escribas»; «no lo reescribas» no encaja en ninguna.

**Por qué importa.** El pilar 3 convierte correcciones repetidas en reglas deterministas. Si el detector solo ve las correcciones impacientes, el operador que corrige con educación —que es el registro normal de un operador atento— trabaja con el bucle de mejora apagado: su corrección nunca entra al registro, nunca cuenta para el umbral, y `/corregir` nunca la propone para elevar. El sesgo es perverso: **se capturan mejor las correcciones del operador molesto que las del operador cuidadoso**.

**Propuesta (sin aplicar).** Nivel 1 · diseño: ampliar el detector a la forma imperativa correctiva en general (imperativo negado de cualquier verbo: «no lo reescribas», «no uses», «no pongas»), a los marcadores de rectificación («en realidad», «más bien», «precisión», «corrección», «aclaración», «para la próxima», «de aquí en adelante») y a la forma condicional normativa («si X, haz Y»). Nivel 4 · prosa: documentar que el operador puede forzar el registro con una frase disparadora si el hook no reacciona.

# D-14 · Media — la clave agrupa por palabras del mensaje, así que la misma corrección dicha de otro modo nunca alcanza el umbral

`clave()` (`captura_correcciones.py:33-38`) construye la clave con las cinco primeras palabras de contenido ordenadas alfabéticamente. Dos formulaciones de la **misma** corrección producen claves distintas. Medido con cuatro paráfrasis, todas con disparador válido:

| Mensaje | Clave |
|---|---|
| «No, te dije que uses rutas relativas a la raíz del repo en las tablas de cierre.» | `cierre-raiz-relativas-repo-rutas` |
| «Otra vez pusiste rutas absolutas; las tablas de cierre van con rutas relativas al repositorio.» | `absolutas-cierre-pusiste-relativas-rutas` |
| «Eso está mal: en las tablas finales quiero rutas relativas, no de C:\Users.» | `finales-quiero-relativas-rutas-tablas` |
| «Nunca escribas rutas absolutas en las tablas de cierre; relativas a la raíz.» | `absolutas-cierre-escribas-raiz-relativas` |

**4 claves distintas de 4.** Las cuatro dicen lo mismo y ninguna llegaría a n ≥ 2.

**Por qué importa.** El umbral de elevación es alcanzable en la práctica solo si el operador repite su corrección **casi palabra por palabra**. Un operador que la reformula —lo natural cuando la primera vez no surtió efecto— mantiene el contador en 1 para siempre. Combinado con D-13, el camino de `correcciones.tsv` a `/corregir` es mucho más estrecho de lo que el diseño supone.

**Propuesta (sin aplicar).** Nivel 1 · diseño: agrupar por similitud en vez de por igualdad exacta de clave — por ejemplo, considerar repetida una corrección cuyo conjunto de palabras de contenido solape por encima de un umbral (Jaccard ≳ 0.5) con otra ya registrada, y reutilizar su clave. Alternativa más simple y robusta: que `/corregir` agrupe por similitud al leer el TSV, dejando el hook como mero registrador.

## Nota sobre el alcance de esta medición

Ambos defectos se midieron ejecutando el módulo real del hook (`RE_CORRECCION` y `clave()` importados de `captura_correcciones.py`), no por lectura del código. La corrección 2 del operador es evidencia en vivo de D-13: llegó, se aplicó, y el harness no la vio.
