import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app  # noqa: E402


def test_registro_en_mayusculas_se_valida():
    cliente = app.test_client()
    respuesta = cliente.post("/validar", data={"registro": "FICT-0001"})
    assert "VERIFICADO" in respuesta.get_data(as_text=True)
