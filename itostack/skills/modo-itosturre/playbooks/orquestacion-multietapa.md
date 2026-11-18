# Playbook · Orquestación multietapa

1. Descomponer la meta en etapas, cada una con una compuerta verificable (comando y veredicto esperado).
2. Asignar a cada subagente un único trabajo y sus anti-trabajos explícitos (p. ej. «redacta, no envía»; «audita, no edita»).
3. Aislar escritores: un `git worktree` por agente que modifica archivos; los roles no son fronteras de credenciales.
4. Ejecutar etapa por etapa; ninguna avanza sin su compuerta en PASS.
5. Registrar decisiones en la bitácora (`muestra-tu-trabajo`).
6. Integrar y correr la verificación final completa (pruebas, lint, rutas del mapa o lote de citas).
