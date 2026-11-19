#!/usr/bin/env python3
"""SessionStart: contexto mínimo del harness (la prosa es la capa más débil; se mantiene corta)."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402


def pendientes_de_elevar(proyecto: Path) -> int:
    correcciones = proyecto / ".itostack" / "mejora" / "correcciones.tsv"
    elevaciones = proyecto / ".itostack" / "mejora" / "elevaciones.tsv"
    if not correcciones.is_file():
        return 0
    conteo = Counter(l.split("\t")[2] for l in correcciones.read_text(encoding="utf-8").splitlines()[1:] if l.count("\t") >= 3)
    elevadas = set()
    if elevaciones.is_file():
        elevadas = {l.split("\t")[1] for l in elevaciones.read_text(encoding="utf-8").splitlines()[1:] if l.count("\t") >= 2}
    return sum(1 for llave, n in conteo.items() if n >= 2 and llave not in elevadas)


def principal() -> int:
    entrada = _comun.leer_entrada()
    raiz = _comun.RAIZ_PLUGIN
    proyecto = _comun.proyecto(entrada)
    if not _comun.tiene_itostack(entrada):
        _comun.contexto(
            "SessionStart",
            f"[itostack] Plugin disponible (raíz: {raiz}). Este proyecto aún no tiene .itostack/: si se trabajará con citas o "
            "verificación, ejecuta la skill configurar-itostack.",
        )
        return 0
    (proyecto / ".itostack" / "raiz_plugin").write_text(str(raiz), encoding="utf-8")
    config = _comun.configuracion(entrada)
    pendientes = pendientes_de_elevar(proyecto)
    interprete = Path(sys.executable).as_posix()
    lineas = [
        f"[itostack] Harness activo · raíz del plugin: {raiz} · modo: {config['modo']}.",
        f"Intérprete de Python que funciona aquí: \"{interprete}\". Úsalo donde las skills dicen python3 (en Windows, python3 suele ser el alias de la Store).",
        f"Scripts: \"{interprete}\" {raiz}/scripts/verificar.py (tesis|url|app|lote) · ensamblar_documento.py · reporte_vvca.py.",
        "Veredictos: PASS / FAIL / BLOCKED. Sin evidencia observable no hay PASS; ante la duda, BLOCKED.",
        "Citas jurídicas: solo con evidencia vigente o como [[CITA:registro]]; lo no verificado se marca ⚠ NO VERIFICADO.",
    ]
    if config["modo"] == "fixture":
        lineas.append("MODO FIXTURE: la evidencia usa datos ficticios y no sirve para uso procesal.")
    if config.get("entorno") == "desarrollo":
        lineas.append("ENTORNO DESARROLLO: se permite el revisor y juez de otra familia en la nube (scripts/revisar_codex.py). En producción, solo revisar_ollama.py.")
    if pendientes:
        lineas.append(f"Hay {pendientes} corrección(es) repetida(s) sin elevar: proponer /corregir al cerrar la tarea.")
    _comun.contexto("SessionStart", "\n".join(lineas))
    return 0


if __name__ == "__main__":
    sys.exit(_comun.ejecutar(principal, "SessionStart", "abierto"))
