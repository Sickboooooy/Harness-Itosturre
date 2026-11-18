"""Contrato de veredictos: PASS, FAIL, BLOCKED. Nada más.

- PASS: hay evidencia observable (captura + SHA-256) y todo lo cotejado coincide.
- FAIL: hay evidencia POSITIVA de discrepancia o inexistencia.
- BLOCKED: no se pudo comprobar (portal caído, estructura desconocida, falta dato o selector).

Falla cerrado: ante la duda, BLOCKED. Nunca se improvisa un PASS.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import normalizacion as norm

VEREDICTOS = ("PASS", "FAIL", "BLOCKED")
ETIQUETAS = {
    "PASS": "✅ VERIFICADO",
    "FAIL": "❌ NO VERIFICABLE — DISCREPANTE O INEXISTENTE",
    "BLOCKED": "⚠ NO VERIFICADO — BLOQUEADO",
}
CAMPOS_CITABLES = ("rubro", "clave", "epoca", "instancia", "tipo", "fecha_publicacion")


@dataclass
class Resultado:
    veredicto: str
    motivo: str
    cotejos: list[dict] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)
    vvca: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.veredicto not in VEREDICTOS:
            raise ValueError(f"veredicto inválido: {self.veredicto}")

    @property
    def etiqueta(self) -> str:
        return ETIQUETAS[self.veredicto]

    def como_dict(self) -> dict:
        return {
            "veredicto": self.veredicto,
            "etiqueta": self.etiqueta,
            "motivo": self.motivo,
            "cotejos": self.cotejos,
            "advertencias": self.advertencias,
            "vvca": self.vvca,
        }


def tiene_captura(captura: dict) -> bool:
    return any(
        archivo.get("tipo") == "captura" and archivo.get("sha256")
        for visita in captura.get("visitas", [])
        for archivo in visita.get("archivos", [])
    )


def _vvca(verificado: bool, validado: bool, auditable: bool) -> dict:
    return {"verificado": verificado, "validado": validado, "contextualizado": False, "auditable": auditable}


def _bloqueado(motivo: str, auditable: bool = False) -> Resultado:
    return Resultado("BLOCKED", motivo, vvca=_vvca(False, False, auditable))


def decidir_tesis(citado: dict, captura: dict, modo: str = "cotejo", ignorar_acentos: bool = True) -> Resultado:
    auditable = tiene_captura(captura)
    if not captura.get("consultado"):
        return _bloqueado(captura.get("motivo_no_consulta") or "no se consultó el portal")
    if not auditable:
        return _bloqueado("sin captura forense: no hay evidencia observable")
    if not captura.get("portal_disponible"):
        return _bloqueado(f"portal no disponible: {captura.get('error_portal') or 'sin respuesta'}", auditable)
    if captura.get("no_encontrado"):
        return Resultado(
            "FAIL",
            "registro inexistente en el SJF (respuesta oficial: no encontrado)",
            vvca=_vvca(False, False, auditable),
        )
    if not captura.get("estructura_reconocida"):
        return _bloqueado("estructura de respuesta no reconocida: calibrar la extracción antes de concluir", auditable)

    oficial = captura.get("datos_oficiales") or {}
    registro_citado = norm.normalizar_registro(citado.get("registro"))
    registro_oficial = norm.normalizar_registro(oficial.get("registro"))
    if registro_oficial and registro_citado and registro_oficial != registro_citado:
        return Resultado(
            "FAIL",
            f"el portal devolvió el registro {registro_oficial}, no {registro_citado}",
            vvca=_vvca(False, False, auditable),
        )

    if modo == "existencia":
        return Resultado(
            "PASS",
            "existencia verificada; usar exclusivamente los datos oficiales capturados",
            vvca=_vvca(True, True, auditable),
        )

    if not (citado.get("rubro") or citado.get("clave")):
        return _bloqueado("la cita no trae rubro ni clave: no hay nada que cotejar (usa modo existencia)", auditable)

    cotejos: list[norm.Cotejo] = []
    if citado.get("rubro"):
        cotejos.append(norm.cotejar_rubro(citado["rubro"], oficial.get("rubro"), ignorar_acentos))
    for campo, cotejador in norm.COTEJADORES.items():
        if citado.get(campo):
            cotejos.append(cotejador(str(citado[campo]), oficial.get(campo)))

    discrepantes = [c for c in cotejos if c.estado == "discrepante"]
    criticos_sin_confirmar = [c for c in cotejos if c.estado == "no_confirmado" and c.critico]
    advertencias = [f"{c.campo}: {c.detalle}" for c in cotejos if c.estado == "no_confirmado" and not c.critico]
    detalle = [c.como_dict() for c in cotejos]

    if discrepantes:
        motivo = "; ".join(f"{c.campo} discrepante ({c.detalle})" if c.detalle else f"{c.campo} discrepante" for c in discrepantes)
        return Resultado("FAIL", motivo, detalle, advertencias, _vvca(True, False, auditable))
    if criticos_sin_confirmar:
        motivo = "; ".join(f"{c.campo} sin confirmar ({c.detalle})" for c in criticos_sin_confirmar)
        return Resultado("BLOCKED", motivo, detalle, advertencias, _vvca(True, False, auditable))
    return Resultado("PASS", "existencia y datos citados confirmados en el portal oficial", detalle, advertencias, _vvca(True, True, auditable))


def decidir_url(contiene: list[str], captura: dict) -> Resultado:
    auditable = tiene_captura(captura)
    if not captura.get("consultado"):
        return _bloqueado(captura.get("motivo_no_consulta") or "no se consultó la URL")
    if not auditable:
        return _bloqueado("sin captura forense: no hay evidencia observable")
    estado = captura.get("estado_http")
    if estado == 404:
        return Resultado("FAIL", "la URL oficial respondió 404 (no existe)", vvca=_vvca(False, False, auditable))
    if not captura.get("portal_disponible") or (estado is not None and estado >= 400):
        return _bloqueado(f"portal no disponible (HTTP {estado}): {captura.get('error_portal') or ''}".strip(), auditable)
    texto = norm.normalizar_texto((captura.get("datos_oficiales") or {}).get("texto", ""))
    faltantes = [fragmento for fragmento in contiene if norm.normalizar_texto(fragmento) not in texto]
    cotejos = [
        {"campo": "texto", "citado": f, "oficial": None, "estado": "discrepante" if f in faltantes else "coincide", "detalle": "", "critico": True}
        for f in contiene
    ]
    if faltantes:
        return Resultado("FAIL", f"texto esperado ausente en la fuente oficial: {faltantes}", cotejos, vvca=_vvca(True, False, auditable))
    motivo = "contenido confirmado en la fuente oficial" if contiene else "existencia de la fuente oficial confirmada"
    return Resultado("PASS", motivo, cotejos, vvca=_vvca(True, True, auditable))


def decidir_app(captura: dict, fallar_con_consola: bool = True) -> Resultado:
    auditable = tiene_captura(captura)
    if not captura.get("app_alcanzable"):
        return _bloqueado(f"app no alcanzable en {captura.get('base')}: arráncala con arrancar_app.py", auditable)
    if not auditable:
        return _bloqueado("sin captura forense: no hay evidencia observable")
    for paso in captura.get("pasos", []):
        fallo = paso.get("fallo")
        if fallo == "selector_ausente":
            return _bloqueado(
                f"paso {paso.get('indice')}: selector ausente {paso.get('selector')!r}; actualiza el mapa de funcionalidades "
                "(mantener-skill-verificacion) o agrega data-testid",
                auditable,
            )
        if fallo in {"expectativa", "navegacion", "error"}:
            return Resultado(
                "FAIL",
                f"paso {paso.get('indice')} ({paso.get('accion')}): {paso.get('detalle') or fallo}",
                vvca=_vvca(True, False, auditable),
            )
    if captura.get("errores_pagina"):
        return Resultado("FAIL", f"excepciones no capturadas en la página: {captura['errores_pagina'][:3]}", vvca=_vvca(True, False, auditable))
    if fallar_con_consola and captura.get("errores_consola"):
        return Resultado("FAIL", f"errores de consola: {captura['errores_consola'][:3]}", vvca=_vvca(True, False, auditable))
    return Resultado("PASS", "la ruta del mapa se recorrió completa sobre la app en ejecución", vvca=_vvca(True, True, auditable))
