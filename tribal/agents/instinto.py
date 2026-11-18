"""
Instinto: la política por defecto, determinista y sin LLM.

Decide qué verbo del vocabulario de `tribal.core.acciones` toca este tick
según la urgencia de las necesidades. Primero se cubre la sed, luego el
hambre; pero lo que ya está al alcance se aprovecha siempre, porque un
individuo que pasa junto a unas bayas con el estómago vacío no tiene motivo
para no comer. Si no hay nada urgente, deambula hacia un punto cercano.

La decisión no aplica nada: eso lo hace el motor.
"""

from __future__ import annotations

from tribal.agents import necesidades as nec
from tribal.core import acciones, recursos
from tribal.core.acciones import Accion
from tribal.core.modelos import Depredador, Individuo, Mundo, Recurso, TipoRecurso

#: Radio en el que el depredador deja de ser paisaje y pasa a ser urgencia.
UMBRAL_HUIDA = 4.0


def elegir(individuo: Individuo, mundo: Mundo) -> Accion:
    """Acción que corresponde a este individuo en este tick."""
    amenaza = _depredador_cercano(individuo, mundo)
    if amenaza is not None and not nec.agotado(individuo.necesidades):
        return Accion("huir", amenaza=(amenaza.x, amenaza.y))

    agua = recursos.mas_cercano(mundo, individuo, (TipoRecurso.AGUA,))
    comida = recursos.mas_cercano(mundo, individuo, (TipoRecurso.BAYAS, TipoRecurso.CAZA))

    if nec.sed_critica(individuo.necesidades) and _al_alcance(individuo, agua):
        return Accion("beber")

    if nec.energia_baja(individuo.necesidades) and _al_alcance(individuo, comida):
        return Accion("comer")

    if nec.sed_critica(individuo.necesidades) and agua is not None:
        return Accion("moverse", destino=(float(agua.x), float(agua.y)))

    if nec.agotado(individuo.necesidades):
        return Accion("descansar")

    if nec.energia_baja(individuo.necesidades) and comida is not None:
        return Accion("moverse", destino=(float(comida.x), float(comida.y)))

    # Con la salud por los suelos y las necesidades cubiertas, se aparta del grupo.
    if nec.salud_critica(individuo.necesidades):
        vecino = _mas_cercano(mundo, individuo)
        if vecino is not None:
            return Accion("huir", amenaza=(vecino.x, vecino.y))

    # Sin nada urgente, el adulto que sabe algo se lo enseña a quien no lo sabe.
    aprendiz = acciones.candidato_a_ensenar(individuo, mundo)
    if aprendiz is not None:
        return Accion("ensenar", objetivo=aprendiz.id)

    return deambular(individuo, mundo)


def deambular(individuo: Individuo, mundo: Mundo) -> Accion:
    """Un paso hacia un punto cercano; el descanso activo de la política."""
    return Accion("moverse", destino=_punto_errante(individuo, mundo))


def _al_alcance(individuo: Individuo, recurso: Recurso | None) -> bool:
    return recurso is not None and recursos.en_alcance(individuo, recurso)


def _depredador_cercano(individuo: Individuo, mundo: Mundo) -> Depredador | None:
    """El depredador más próximo, si está dentro del radio de huida."""
    if not mundo.depredadores:
        return None
    cercano = min(
        mundo.depredadores,
        key=lambda depredador: recursos.distancia(
            individuo.x, individuo.y, depredador.x, depredador.y
        ),
    )
    distancia = recursos.distancia(individuo.x, individuo.y, cercano.x, cercano.y)
    return cercano if distancia <= UMBRAL_HUIDA else None


def _mas_cercano(mundo: Mundo, individuo: Individuo) -> Individuo | None:
    otros = [otro for otro in mundo.individuos if otro.id != individuo.id]
    if not otros:
        return None
    return min(
        otros,
        key=lambda otro: (recursos.distancia(individuo.x, individuo.y, otro.x, otro.y), otro.id),
    )


def _punto_errante(individuo: Individuo, mundo: Mundo) -> tuple[float, float]:
    """Destino aleatorio a unos tiles de distancia, dentro del mapa."""
    x = individuo.x + mundo.azar.uniform(-5.0, 5.0)
    y = individuo.y + mundo.azar.uniform(-5.0, 5.0)
    return (
        min(max(x, 0.0), float(mundo.ancho - 1)),
        min(max(y, 0.0), float(mundo.alto - 1)),
    )
