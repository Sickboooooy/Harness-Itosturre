"""App ficticia para evals del perfil desarrollo. Contiene un error deliberado (ver tests)."""

from flask import Flask, render_template, request

app = Flask(__name__)

CRITERIOS_FICTICIOS = {
    "FICT-0001": "VERIFICADO",
    "FICT-0404": "INEXISTENTE",
}


def consultar(registro: str) -> str:
    return CRITERIOS_FICTICIOS.get(registro, "NO ENCONTRADO")


@app.route("/")
def inicio():
    return render_template("index.html", resultado=None, registro="")


@app.route("/validar", methods=["POST"])
def validar():
    registro = request.form.get("registro", "")
    return render_template("index.html", resultado=consultar(registro), registro=registro)
