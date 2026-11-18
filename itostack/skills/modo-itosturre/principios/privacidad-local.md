# Privacidad local

**Regla.** Los datos legales nunca salen de la máquina. Procesamiento con modelos locales (Ollama), almacenamiento en SQLite local, consultas solo a portales oficiales. Toda acción hacia afuera (correo, Slack, publicación) pasa por la compuerta humana.

**Cómo.** El hook de Bash bloquea subidas y copias remotas; el lint IT004/IT005 bloquea envíos y LLM en la nube en código de producto; el hook de MCP pide aprobación para enviar.
