# Privacidad local

**Regla.** Los datos legales no deben salir de la máquina. Procesamiento con modelos locales (Ollama) u otro disponible, almacenamiento en SQLite local, consultas solo a portales oficiales. Toda acción hacia afuera (correo, Slack, publicación) pasa por la compuerta humana.

La anterior regla sólo aplica cuando el proyecto se encuentre en producción, mientras se trabaje en local no aplica

**Cómo.** `"entorno"` en `.itostack/config.json` decide: sin declararlo se asume `produccion` (falla cerrado); `revisar_codex.py` solo corre con `"desarrollo"`. El hook de Bash bloquea subidas y copias remotas; el lint IT004/IT005 bloquea envíos y LLM en la nube en código de producto; el hook de MCP pide aprobación para enviar, y en un modo de permisos que aprueba solo (auto, dontAsk, bypassPermissions) deniega.
