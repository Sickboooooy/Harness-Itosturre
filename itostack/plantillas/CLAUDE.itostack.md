# itostack (importado desde CLAUDE.md con @.itostack/CLAUDE.itostack.md)

La prosa es la capa más débil de la pirámide: aquí solo va lo que todavía no es una guardia.

- Tareas no triviales: skill `modo-itosturre`. Veredictos: PASS / FAIL / BLOCKED; sin evidencia no hay PASS.
- Citas jurídicas: `/verificar-cita` antes de usarlas; en escritos, borrador con marcadores (`[[CITA:…]]`, `[[CITA_AJENA:…|…]]`, `[[NO_VERIFICADO:…]]`) + `ensamblar_documento.py`. Los entregables no se escriben a mano.
- En el chat, lo no verificado se marca ⚠ NO VERIFICADO; lo inexistente o discrepante, ❌. En archivos, esas marcas las pone el ensamblador.
- Comportamiento de la app: `/demuestra-que-funciona`, nunca «debería funcionar».
- Corrección repetida → `/corregir` (se eleva a lint, hook o prueba).
- Datos legales: nunca salen de la máquina.
- Commits descriptivos en español; PRs de agente solo en borrador.
- Intérprete de Python: el que anuncia el hook de inicio (en Windows, no `python3`).
