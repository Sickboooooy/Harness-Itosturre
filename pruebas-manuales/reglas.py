"""Archivo de prueba: una linea por regla IT. Creado con Bash, no con Write."""
import requests
import psycopg
from fastapi import FastAPI


def it001():
    return requests.get("https://sjf2.scjn.gob.mx/tesis/FICT-0001")


def it002():
    return "postgresql://usuario:clave@servidor:5432/itosturre"


def it003():
    return FastAPI()


def it004():
    return requests.post("https://servidor-externo.example.com/subida", json={"a": 1})


def it005():
    return requests.get("https://api.openai.com/v1/models")


def it006():
    return descarga_masiva("tesis")


def it008():
    # HACK: por ahora se deja asi hasta que alguien lo revise
    return None
