---
name: muestra-tu-trabajo
description: Bitácora auditable de decisiones tomadas sin supervisión (qué se decidió, por qué, alternativas y si es reversible), en archivos TSV por día. Úsala en tareas largas o desatendidas, al elegir entre interpretaciones razonables, al omitir un paso de un playbook, o antes de cualquier acción irreversible.
---

# Muestra tu trabajo

Raíz del plugin: `R=$(cat .itostack/raiz_plugin)`.

Registra cada decisión no trivial en el momento:

```bash
python3 "$R/scripts/bitacora.py" registrar --tarea "<id o nombre>" \
  --decision "<qué>" --razon "<por qué>" --alternativas "<qué se descartó>" --reversible si
```

- `--reversible no` devuelve código 3 y significa: **prepara, documenta y detente**. Pide confirmación al operador antes de ejecutar.
- Al cerrar una tarea desatendida, incluye `python3 "$R/scripts/bitacora.py" ver` en el resumen para que el operador audite.
- Registra también los pasos marcados `skip:` en la lista de tareas y su razón.
