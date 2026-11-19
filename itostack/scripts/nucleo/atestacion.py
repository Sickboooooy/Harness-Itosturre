"""Firma y verificación de atestaciones del ejecutor aislado (CR-2) con OpenSSH (`ssh-keygen -Y`), sin dependencias.

El ejecutor firma el manifiesto del holdout (y la atestación de que la reserva está aislada) con su clave PRIVADA, que
vive solo en él. El constructor verifica con la clave PÚBLICA versionada en un archivo de firmantes permitidos
(formato allowed_signers de OpenSSH). Falla cerrado: sin ssh-keygen, sin firma o con cualquier byte distinto, no vale.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ESPACIO = "itostack-holdout"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _ssh_keygen(ruta: str | None = None) -> str | None:
    return ruta or shutil.which("ssh-keygen")


def firmar(datos: bytes, clave_privada: Path, espacio: str = ESPACIO, ssh_keygen: str | None = None) -> bytes:
    """Firma `datos` (uso: el ejecutor y las pruebas con claves efímeras). Devuelve la firma armada de OpenSSH."""
    programa = _ssh_keygen(ssh_keygen)
    if not programa:
        raise RuntimeError("ssh-keygen no está disponible")
    with tempfile.TemporaryDirectory() as tmp:
        archivo = Path(tmp) / "datos"
        archivo.write_bytes(datos)
        subprocess.run([programa, "-Y", "sign", "-f", str(clave_privada), "-n", espacio, str(archivo)], check=True, capture_output=True, timeout=60)
        return (Path(tmp) / "datos.sig").read_bytes()


def verificar(datos: bytes, firma: bytes, firmantes: Path, identidad: str, espacio: str = ESPACIO, ssh_keygen: str | None = None) -> list[str]:
    """Problemas de la firma; vacío = válida para esa identidad, ese espacio de nombres y exactamente esos bytes."""
    programa = _ssh_keygen(ssh_keygen)
    if not programa:
        return ["ssh-keygen no está disponible: no se puede verificar la firma"]
    if not firmantes.is_file():
        return ["no hay archivo de firmantes permitidos (clave pública del ejecutor)"]
    if not firma.strip().startswith(b"-----BEGIN SSH SIGNATURE-----"):
        return ["la firma no es una firma de OpenSSH"]
    with tempfile.TemporaryDirectory() as tmp:
        ruta_firma = Path(tmp) / "firma.sig"
        ruta_firma.write_bytes(firma)
        try:
            salida = subprocess.run([programa, "-Y", "verify", "-f", str(firmantes), "-I", identidad, "-n", espacio, "-s", str(ruta_firma)],
                                    input=datos, capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as error:
            return [f"no se pudo ejecutar ssh-keygen ({error})"]
    if salida.returncode != 0:
        return [f"firma inválida para «{identidad}»: {(salida.stderr or salida.stdout).decode('utf-8', 'replace').strip()[:200]}"]
    return []


def verificar_atestacion_reserva(atestacion: bytes, firma: bytes, firmantes: Path, identidad: str, huella_reserva: str) -> list[str]:
    """X10: «aislada» solo vale con una atestación firmada por el ejecutor sobre ESTA reserva (huella), con las
    aprobaciones humanas de sus casos. Sin firma válida, la reserva se trata como contaminada."""
    problemas = verificar(atestacion, firma, firmantes, identidad)
    if problemas:
        return problemas
    try:
        datos = json.loads(atestacion.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return ["la atestación no es JSON"]
    if not isinstance(datos, dict) or datos.get("estado") != "aislada":
        return ["la atestación no declara la reserva aislada"]
    if not isinstance(datos.get("huella_reserva"), str) or not _HEX64.match(datos["huella_reserva"]) or datos["huella_reserva"] != huella_reserva:
        return ["la atestación es de otra reserva (huella distinta)"]
    aprobaciones = datos.get("aprobaciones")
    if not isinstance(aprobaciones, list) or not aprobaciones:
        return ["la atestación no trae las aprobaciones humanas de los casos"]
    return []
