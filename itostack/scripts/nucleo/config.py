"""Configuración del proyecto: `.itostack/config.json` mezclado con los valores por defecto."""

from __future__ import annotations

import copy
import glob
import json
import os
import shutil
from pathlib import Path

try:
    import pwd
except ImportError:  # Windows: no existe el módulo pwd
    pwd = None

RAIZ_PLUGIN = Path(__file__).resolve().parents[2]
DIR_ITOSTACK = ".itostack"

CONFIG_DEFECTO: dict = {
    "version": 1,
    "modo": "real",
    # Principio privacidad-local: en "produccion" los datos no salen de la máquina. Solo con "desarrollo" se
    # permiten revisores en la nube (revisar_codex.py). Sin declararlo se asume producción: falla cerrado.
    "entorno": "produccion",
    "sjf": {
        "base": "https://sjf2.scjn.gob.mx",
        "ruta_detalle": "/detalle/tesis/{registro}",
        "ruta_api": "/services/sjftesismicroservice/api/public/tesis/{registro}",
        "fixture": None,
        "_nota": "Rutas tomadas de la skill scjn-api del operador. ⚠ Confirmar en el portal antes del primer uso real.",
    },
    "dominios_oficiales": [
        "sjf2.scjn.gob.mx",
        "sjf.scjn.gob.mx",
        "www.dof.gob.mx",
        "dof.gob.mx",
        "www.diputados.gob.mx",
        "diputados.gob.mx",
    ],
    "evidencia": {
        "directorio": ".itostack/evidencia",
        "base_datos": ".itostack/evidencia_forense.db",
        "vigencia_dias": 30,
    },
    "comparacion": {"ignorar_acentos": True},
    "salidas_juridicas": ["salidas/**", "escritos/**", "dictamenes/**", "**/*.juridico.md"],
    # Herramientas MCP que salen de la máquina sin pasar por la compuerta humana (patrones fnmatch sobre el nombre,
    # p. ej. "mcp__plugin_telegram_telegram__reply"). Vacío por omisión: toda salida pasa por la compuerta.
    "acciones_externas_permitidas": [],
    "modo_estricto_md": False,
    "navegador": {"ejecutable": None, "canal": None, "timeout_ms": 45000},
    "app": {"fallar_con_errores_consola": True, "timeout_ms": 8000},
    "cortes_temporales": [
        {
            "id": "reforma-judicial",
            "fecha": "2024-09-15",
            "mensaje": "Anterior a la reforma judicial (DOF 15-IX-2024): verificar si el criterio fue superado.",
        },
        {
            "id": "duodecima-epoca",
            "fecha": "2025-09-01",
            "mensaje": "Anterior a la Duodécima Época (AG 7/2025 (12a.), 1-IX-2025): verificar vigencia del criterio.",
        },
        {
            "id": "reforma-amparo",
            "fecha": "2025-10-17",
            "materias": ["comun", "amparo"],
            "mensaje": "Anterior a la reforma a la Ley de Amparo (DOF 16-X-2025, vigor 17-X-2025): verificar compatibilidad y transitorio 3°.",
        },
    ],
    "_fuente_cortes": "Marco vigente declarado por el operador (perfil Itosturre). ⚠ Verificar en DOF antes de uso procesal.",
}


def _mezclar(base: dict, encima: dict) -> dict:
    resultado = copy.deepcopy(base)
    for clave, valor in encima.items():
        if isinstance(valor, dict) and isinstance(resultado.get(clave), dict):
            resultado[clave] = _mezclar(resultado[clave], valor)
        else:
            resultado[clave] = valor
    return resultado


def raiz_proyecto(desde: str | os.PathLike | None = None) -> Path:
    """Sube desde `desde` hasta encontrar `.itostack/` o `.git/`; si no hay, usa `desde`."""
    explicita = os.environ.get("ITOSTACK_PROYECTO")
    if explicita:
        return Path(explicita).resolve()
    actual = Path(desde or os.getcwd()).resolve()
    for candidato in [actual, *actual.parents]:
        if (candidato / DIR_ITOSTACK).is_dir():
            return candidato
    for candidato in [actual, *actual.parents]:
        if (candidato / ".git").exists():
            return candidato
    return actual


def cargar(proyecto: Path | None = None) -> dict:
    proyecto = proyecto or raiz_proyecto()
    ruta = proyecto / DIR_ITOSTACK / "config.json"
    config = copy.deepcopy(CONFIG_DEFECTO)
    if ruta.is_file():
        config = _mezclar(config, json.loads(ruta.read_text(encoding="utf-8")))
    modo_entorno = os.environ.get("ITOSTACK_MODO")
    if modo_entorno in {"real", "fixture"}:
        config["modo"] = modo_entorno
    config["_proyecto"] = str(proyecto)
    return config


def ruta_en_proyecto(config: dict, relativa: str) -> Path:
    ruta = Path(relativa)
    return ruta if ruta.is_absolute() else Path(config["_proyecto"]) / ruta


def home_real() -> Path:
    """El HOME del usuario aunque el proceso corra con HOME aislado (p. ej. `claude plugin eval`)."""
    if pwd is not None:
        try:
            return Path(pwd.getpwuid(os.getuid()).pw_dir)
        except KeyError:
            pass
    perfil = os.environ.get("USERPROFILE")
    return Path(perfil) if perfil else Path.home()


def detectar_navegador(config: dict) -> str | None:
    """Ruta de un Chromium utilizable por Playwright; None deja que Playwright use el suyo."""
    candidatos: list[str] = []
    for valor in (config.get("navegador", {}).get("ejecutable"), os.environ.get("ITOSTACK_CHROME")):
        if valor:
            candidatos.append(valor)
    bases = [
        os.environ.get("PLAYWRIGHT_BROWSERS_PATH"),
        str(home_real() / ".cache" / "ms-playwright"),
        str(home_real() / "Library" / "Caches" / "ms-playwright"),
        os.path.join(os.environ["LOCALAPPDATA"], "ms-playwright") if os.environ.get("LOCALAPPDATA") else None,
        str(home_real() / "AppData" / "Local" / "ms-playwright"),
    ]
    patrones = (
        "chromium-*/chrome-linux*/chrome",
        "chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium",
        "chromium-*/chrome-win*/chrome.exe",
    )
    for base in filter(None, bases):
        for patron in patrones:
            candidatos.extend(sorted(glob.glob(os.path.join(base, patron)), reverse=True))
    for nombre in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        encontrado = shutil.which(nombre)
        if encontrado:
            candidatos.append(encontrado)
    for candidato in candidatos:
        if candidato and Path(candidato).is_file() and os.access(candidato, os.X_OK):
            return candidato
    return None
