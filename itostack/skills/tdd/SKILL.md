---
name: tdd
description: Desarrollo guiado por pruebas en Python (pytest) o TypeScript, escribiendo primero una prueba que falla por la razón correcta antes de cambiar código. Úsala antes de corregir un error o implementar una funcionalidad cuando exista un objetivo local barato de probar.
---

# TDD

1. Escribe la prueba más pequeña que exprese el comportamiento esperado, en el archivo de pruebas existente más cercano (nombres en español, como el resto del código).
2. Córrela y confirma que **falla por la razón correcta** (no por un import roto o un error de sintaxis). Guarda la salida.
3. Implementa el cambio mínimo.
4. Corre la prueba y la suite relacionada; muestra la salida con los aprobados.
5. Si la prueba replica la implementación línea por línea, no prueba nada: reescríbela sobre el comportamiento observable.

Omitir TDD es válido solo si el objetivo exige integración pesada (navegador, servicios externos); en ese caso, la evidencia la da /demuestra-que-funciona y la omisión se documenta.
