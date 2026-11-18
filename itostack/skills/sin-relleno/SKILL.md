---
name: sin-relleno
description: Poda muletillas y relleno típico de texto generado por IA en español (es importante destacar, cabe mencionar, sin lugar a dudas, juega un papel crucial, en resumen) en PRs, mensajes, informes y escritos, sin tocar fórmulas forenses legítimas. Úsala antes de entregar cualquier texto que vaya a leer una persona.
---

# Sin relleno

Raíz del plugin: `R=$(cat .itostack/raiz_plugin)`.

1. Detecta: `python3 "$R/scripts/detectar_relleno.py" <archivo>`.
2. Reescribe cada hallazgo diciendo el dato directamente; elimina cierres redundantes y adjetivos de folleto.
3. Conserva el registro forense: «en virtud de lo anterior», «por lo expuesto y fundado», «se tiene por recibido» no son relleno.
4. Repite hasta `LIMPIO`.
5. No cambies el sentido jurídico ni los datos de una cita al podar.
