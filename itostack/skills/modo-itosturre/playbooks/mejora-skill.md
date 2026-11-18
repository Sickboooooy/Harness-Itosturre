# Playbook · Mejora de skill

1. Tratar el desvío (skill ignorada, equivocada o a medias) como defecto de software; describir el fallo observado con su traza.
2. Reproducirlo con un caso de eval de desarrollo (/crear-eval) que hoy falle.
3. Corregir en el nivel más fuerte: script determinista, guardia o, en último caso, texto de la skill.
4. Iterar con /correr-evals sobre desarrollo hasta 1.0 en todos los casos (sin tocar holdout).
5. Congelar y correr el holdout una sola vez con `compuerta_holdout.py`; si falla, rediseñar y volver al paso 2.
