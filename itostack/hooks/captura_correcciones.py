#!/usr/bin/env python3
"""UserPromptSubmit: detecta correcciones humanas y las registra para elevarlas a reglas deterministas.

Una corrección aislada es un dato; repetida (≥2) es una regla que falta. Este hook solo registra y
recuerda: la elevación la hace /corregir, con aprobación del operador.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402

RE_CORRECCION = re.compile(
    r"^\s*(?:no[,.!\s]|nop\b)|\bte\s+dije\b|\bya\s+te\s+(?:dije|hab[ií]a\s+dicho)\b|\botra\s+vez\b|\bde\s+nuevo\b|"
    r"\beso\s+(?:est[áa]\s+mal|no\s+es)\b|\bincorrect[oa]\b|\bno\s+inventes\b|\bdeja\s+de\b|\bno\s+hagas\b|"
    r"\bnunca\s+(?:uses|hagas|pongas|escribas)\b|\bsiempre\s+(?:usa|haz|pon|escribe)\b|\bte\s+equivocaste\b",
    re.IGNORECASE,
)
VACIAS = {"no", "te", "dije", "que", "de", "la", "el", "los", "las", "un", "una", "y", "a", "en", "por", "para", "otra", "vez",
          "eso", "esta", "mal", "ya", "lo", "se", "es", "con", "del", "al", "nunca", "siempre", "deja", "hagas", "nuevo", "mas"}


def clave(texto: str) -> str:
    plano = unicodedata.normalize("NFD", texto.lower())
    plano = "".join(c for c in plano if unicodedata.category(c) != "Mn")
    palabras = [p for p in re.findall(r"[a-z0-9]+", plano) if p not in VACIAS and len(p) > 2]
    return "-".join(sorted(set(palabras[:8]))[:5]) or "sin-clave"


def principal() -> int:
    entrada = _comun.leer_entrada()
    prompt = entrada.get("prompt", "")
    if not prompt or not RE_CORRECCION.search(prompt) or not _comun.tiene_itostack(entrada):
        return 0
    registro = _comun.proyecto(entrada) / ".itostack" / "mejora" / "correcciones.tsv"
    registro.parent.mkdir(parents=True, exist_ok=True)
    if not registro.exists():
        registro.write_text("fecha\tsesion\tclave\textracto\n", encoding="utf-8")
    llave = clave(prompt)
    extracto = re.sub(r"\s+", " ", prompt)[:240].replace("\t", " ")
    with open(registro, "a", encoding="utf-8") as archivo:
        archivo.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}\t{entrada.get('session_id', '')}\t{llave}\t{extracto}\n")
    conteo = Counter(linea.split("\t")[2] for linea in registro.read_text(encoding="utf-8").splitlines()[1:] if linea.count("\t") >= 3)
    if conteo[llave] >= 2:
        aviso = (
            f"[itostack] Esta corrección se repite ({conteo[llave]} veces, clave «{llave}»). Aplica la corrección y, al terminar, "
            "propón con /corregir elevarla al nivel más fuerte posible (tipo/API → lint/hook → prueba/eval → prosa)."
        )
    else:
        aviso = "[itostack] Corrección registrada. Aplícala; si vuelve a ocurrir, se propondrá elevarla a una regla determinista."
    _comun.contexto("UserPromptSubmit", aviso)
    return 0


if __name__ == "__main__":
    sys.exit(_comun.ejecutar(principal, "UserPromptSubmit", "abierto"))
