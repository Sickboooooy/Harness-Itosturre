---
name: configurar-itostack
description: Configura el harness itostack en un proyecto (carpeta .itostack con configuración, almacén de evidencia, mapa de funcionalidades, plantilla de CLAUDE.md y modelos por rol) e instala el navegador forense. Úsala la primera vez que se trabaje con itostack en un repositorio, cuando falte .itostack/, o cuando el usuario pida configurar, instalar o preparar el harness.
---

# Configurar itostack

La raíz del plugin está dos niveles arriba de esta skill (`../..`); el hook de inicio la anuncia en el contexto.

## Procedimiento

1. Pregunta el perfil si no es obvio: `juridico` (citas, escritos), `desarrollo` (app Flask/scraper) o `ambos`.
2. Inicializa:

   ```bash
   python3 <raíz>/scripts/inicializar.py --proyecto . --perfil ambos
   ```

3. Si el script avisa que falta Playwright, instala (una vez por máquina):

   ```bash
   cd <raíz>/scripts && npm install && npx playwright install chromium
   ```

4. Agrega `@.itostack/CLAUDE.itostack.md` al `CLAUDE.md` del proyecto (pide confirmación antes de editarlo).
5. Revisa con el operador `.itostack/config.json`: `salidas_juridicas`, `vigencia_dias`, rutas del SJF. ⚠ Las rutas del SJF vienen de la skill scjn-api del operador: la primera verificación real debe revisarse a mano (captura incluida).
6. Revisa `.itostack/modelos.json` (modelo por rol, revisor local de Ollama).
7. Prueba de humo: `python3 <raíz>/scripts/verificar.py tesis --registro <un registro real que el operador conozca> --modo existencia` y abre la captura.
8. Perfil desarrollo: ejecuta /crear-skill-verificacion para generar el mapa y la skill de verificación del proyecto.

## Programación del bucle externo (opcional)

Las rutinas de salud pueden programarse con cron (ver `plantillas/cron-itostack.txt`). En WSL, `sudo service cron start`.
