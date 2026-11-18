"""Almacén de evidencia forense (SQLite, solo anexar).

No es una base de jurisprudencia: guarda un registro por cada verificación ejecutada
(qué se consultó, qué se vio, cuándo y con qué huella SHA-256). Las filas son inmutables.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import normalizacion as norm

ESQUEMA = """
CREATE TABLE IF NOT EXISTS verificaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL CHECK (tipo IN ('tesis', 'url', 'app')),
    identificador TEXT NOT NULL,
    clave_normalizada TEXT,
    veredicto TEXT NOT NULL CHECK (veredicto IN ('PASS', 'FAIL', 'BLOCKED')),
    motivo TEXT NOT NULL,
    modo_fuente TEXT NOT NULL CHECK (modo_fuente IN ('real', 'fixture')),
    datos_citados TEXT NOT NULL,
    datos_oficiales TEXT NOT NULL,
    advertencias TEXT NOT NULL,
    evidencia TEXT NOT NULL,
    sha256_resultado TEXT NOT NULL,
    ruta_resultado TEXT NOT NULL,
    creado_en TEXT NOT NULL,
    herramienta TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_verificaciones_busqueda ON verificaciones (tipo, identificador, creado_en);
CREATE INDEX IF NOT EXISTS idx_verificaciones_clave ON verificaciones (clave_normalizada);
CREATE TRIGGER IF NOT EXISTS verificaciones_sin_actualizar BEFORE UPDATE ON verificaciones
BEGIN SELECT RAISE(ABORT, 'registro de evidencia inmutable: no se actualiza'); END;
CREATE TRIGGER IF NOT EXISTS verificaciones_sin_borrar BEFORE DELETE ON verificaciones
BEGIN SELECT RAISE(ABORT, 'registro de evidencia inmutable: no se borra'); END;
"""


def sha256_archivo(ruta: Path) -> str:
    resumen = hashlib.sha256()
    with open(ruta, "rb") as manejador:
        for bloque in iter(lambda: manejador.read(65536), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def json_canonico(datos: dict) -> str:
    return json.dumps(datos, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_resultado(resultado: dict) -> str:
    sin_huella = {k: v for k, v in resultado.items() if k != "sha256_resultado"}
    return hashlib.sha256(json_canonico(sin_huella).encode("utf-8")).hexdigest()


class AlmacenEvidencia:
    def __init__(self, ruta_db: Path) -> None:
        self.ruta_db = Path(ruta_db)

    def _conexion(self) -> sqlite3.Connection:
        self.ruta_db.parent.mkdir(parents=True, exist_ok=True)
        conexion = sqlite3.connect(self.ruta_db)
        conexion.row_factory = sqlite3.Row
        return conexion

    def inicializar(self) -> None:
        with self._conexion() as conexion:
            conexion.executescript(ESQUEMA)

    def registrar(self, resultado: dict, ruta_resultado: Path) -> int:
        self.inicializar()
        oficial = resultado.get("datos_oficiales") or {}
        clave = norm.normalizar_clave(oficial.get("clave")) or None
        archivos = [a for v in resultado.get("visitas", []) for a in v.get("archivos", [])]
        fila = (
            resultado["tipo"],
            norm.normalizar_registro(resultado["identificador"]) if resultado["tipo"] == "tesis" else resultado["identificador"],
            clave,
            resultado["veredicto"],
            resultado["motivo"],
            resultado.get("modo_fuente", "real"),
            json_canonico(resultado.get("datos_citados") or {}),
            json_canonico(oficial),
            json.dumps(resultado.get("advertencias") or [], ensure_ascii=False),
            json.dumps(archivos, ensure_ascii=False),
            resultado["sha256_resultado"],
            str(ruta_resultado),
            resultado["marca_tiempo"],
            resultado.get("herramienta", ""),
        )
        with self._conexion() as conexion:
            cursor = conexion.execute(
                "INSERT INTO verificaciones (tipo, identificador, clave_normalizada, veredicto, motivo, modo_fuente, "
                "datos_citados, datos_oficiales, advertencias, evidencia, sha256_resultado, ruta_resultado, creado_en, herramienta) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                fila,
            )
            return int(cursor.lastrowid)

    def _filas(self, consulta: str, parametros: tuple) -> list[dict]:
        if not self.ruta_db.is_file():
            return []
        with self._conexion() as conexion:
            return [dict(fila) for fila in conexion.execute(consulta, parametros).fetchall()]

    def ultimo(self, tipo: str, identificador: str, modos: tuple[str, ...] = ("real",)) -> dict | None:
        ident = norm.normalizar_registro(identificador) if tipo == "tesis" else identificador
        marcadores = ",".join("?" for _ in modos)
        filas = self._filas(
            f"SELECT * FROM verificaciones WHERE tipo = ? AND identificador = ? AND modo_fuente IN ({marcadores}) "
            "ORDER BY creado_en DESC, id DESC LIMIT 1",
            (tipo, ident, *modos),
        )
        return filas[0] if filas else None

    def vigente(self, tipo: str, identificador: str, dias: int, modos: tuple[str, ...] = ("real",)) -> dict | None:
        """Último PASS dentro de la vigencia y con evidencia íntegra; None en cualquier otro caso."""
        fila = self.ultimo(tipo, identificador, modos)
        if not fila or fila["veredicto"] != "PASS":
            return None
        creado = datetime.fromisoformat(fila["creado_en"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) - creado > timedelta(days=dias):
            return None
        if self.problemas_de_integridad(fila):
            return None
        return fila

    def vigente_por_clave(self, clave: str, dias: int, modos: tuple[str, ...] = ("real",)) -> dict | None:
        marcadores = ",".join("?" for _ in modos)
        filas = self._filas(
            f"SELECT identificador FROM verificaciones WHERE clave_normalizada = ? AND modo_fuente IN ({marcadores}) "
            "ORDER BY creado_en DESC LIMIT 1",
            (norm.normalizar_clave(clave), *modos),
        )
        return self.vigente("tesis", filas[0]["identificador"], dias, modos) if filas else None

    @staticmethod
    def problemas_de_integridad(fila: dict) -> list[str]:
        problemas: list[str] = []
        for archivo in json.loads(fila["evidencia"]):
            ruta = Path(archivo["ruta"])
            if not ruta.is_file():
                problemas.append(f"falta {ruta}")
            elif sha256_archivo(ruta) != archivo["sha256"]:
                problemas.append(f"huella alterada {ruta}")
        ruta_resultado = Path(fila["ruta_resultado"])
        if ruta_resultado.is_file():
            guardado = json.loads(ruta_resultado.read_text(encoding="utf-8"))
            if sha256_resultado(guardado) != fila["sha256_resultado"]:
                problemas.append(f"resultado alterado {ruta_resultado}")
        else:
            problemas.append(f"falta {ruta_resultado}")
        return problemas

    def auditar(self) -> list[tuple[int, list[str]]]:
        return [
            (fila["id"], problemas)
            for fila in self._filas("SELECT * FROM verificaciones ORDER BY id", ())
            if (problemas := self.problemas_de_integridad(fila))
        ]

    def recientes(self, limite: int = 20) -> list[dict]:
        return self._filas(
            "SELECT id, tipo, identificador, veredicto, modo_fuente, creado_en, motivo FROM verificaciones "
            "ORDER BY id DESC LIMIT ?",
            (limite,),
        )
