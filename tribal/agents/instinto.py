"""
Instinto: la política por defecto, determinista y sin LLM.

Decide qué verbo del vocabulario de `tribal.core.acciones` toca este tick
según la urgencia de las necesidades. Primero se cubre la sed, luego el
hambre; pero lo que ya está al alcance se aprovecha siempre, porque un
individuo que pasa junto a unas bayas con el estómago vacío no tiene motivo
para no comer. Si no hay nada urgente, deambula hacia un punto cercano o
practica lo que el lugar permite (enseñar, cuidar, hablar, pintar, tallar,
frotar madera): esa práctica es la que conecta las ramas del árbol con la
conducta que las hace avanzar.

El temperamento (`divergencia`) cambia **el paseo ocioso**, no la urgencia: el
divergente explora un radio grande y se aparta del vecino, el conformista se
queda cerca del grupo y tiende a él. Ese es el único efecto del rasgo en calma,
y es conducta: no toca comer, beber, criar ni el genoma.

La decisión no aplica nada: eso lo hace el motor.
"""

from __future__ import annotations

import math

from tribal.agents import necesidades as nec
from tribal.core import acciones, recursos
from tribal.core.acciones import Accion, NombreAccion
from tribal.core.modelos import Depredador, Individuo, Mundo, Recurso, TipoRecurso, TipoTile

#: Radio en el que el depredador deja de ser paisaje y pasa a ser urgencia.
UMBRAL_HUIDA = 4.0
#: Al deambular, 40 % de las veces se va hacia el vecino más cercano en vez de
#: a un punto al azar: sin esa cohesión el grupo se dispersa y la calma pierde
#: los encuentros que sostienen la reproducción. El sesgo es firmado: el
#: conformista lo cobra entero y el divergente lo cobra al revés (evita).
SESGO_COHESION = 0.4
#: Divergencia en la que el paseo no tiene preferencia: ni explora ni se pega.
DIVERGENCIA_NEUTRA = 0.5
#: Radio del paseo ocioso en cada tramo del temperamento, en tiles. El
#: divergente explora lejos; el conformista se queda en el entorno del grupo.
RADIO_DEAMBULAR_CONFORMISTA = 3.0
RADIO_DEAMBULAR_NEUTRO = 5.0
RADIO_DEAMBULAR_DIVERGENTE = 10.0
#: Se considera llegado el paseo a esta distancia del destino, en tiles.
TOLERANCIA_PASEO = 0.5


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

    # El tramo ocioso —sin sed, hambre, agotamiento ni heridas— es el único en
    # el que se practica: primero transmitir, luego cuidar y, si no hay nada de
    # eso, una práctica del lugar donde está.
    if not _urgente(individuo):
        aprendiz = acciones.candidato_a_ensenar(individuo, mundo)
        if aprendiz is not None:
            return Accion("ensenar", objetivo=aprendiz.id)

        atendido = acciones.candidato_a_cuidar(individuo, mundo)
        if atendido is not None:
            return Accion("cuidar", objetivo=atendido.id)

        disponibles = _practicas_disponibles(individuo, mundo)
        if disponibles:
            return Accion(disponibles[(individuo.id + mundo.tick) % len(disponibles)])

    return deambular(individuo, mundo)


def _urgente(individuo: Individuo) -> bool:
    """True si hay algo que atender antes de practicar."""
    return (
        nec.sed_critica(individuo.necesidades)
        or nec.energia_baja(individuo.necesidades)
        or nec.agotado(individuo.necesidades)
        or nec.salud_critica(individuo.necesidades)
    )


def _practicas_disponibles(individuo: Individuo, mundo: Mundo) -> tuple[NombreAccion, ...]:
    """Prácticas ociosas que la situación permite, en orden fijo.

    El llamador rota con `(id + tick)` para que un mismo individuo no repita
    siempre la primera y todas las ramas tengan ocasión de avanzar.
    """
    disponibles: list[NombreAccion] = []
    if acciones.vecino(individuo, mundo) is not None:
        disponibles.append("hablar")
    if acciones.junto_a(mundo, individuo, TipoTile.BOSQUE, TipoTile.AGUA):
        disponibles.append("pintar")
    if acciones.junto_a(mundo, individuo, TipoTile.BOSQUE):
        disponibles.extend(("tallar", "frotar_madera"))
    return tuple(disponibles)


def deambular(individuo: Individuo, mundo: Mundo) -> Accion:
    """Un paso hacia un punto cercano; el descanso activo de la política."""
    return Accion("moverse", destino=_punto_errante(individuo, mundo))


def radio_deambular(individuo: Individuo) -> float:
    """Radio del paseo ocioso, en tiles: crece con `divergencia`.

    Es conducta, no aptitud: el divergente explora lejos y el conformista se
    queda alrededor del grupo. La interpolación es lineal por tramos, con
    `DIVERGENCIA_NEUTRA` como bisagra, para que no haya saltos al cruzar los
    umbrales del temperamento.
    """
    divergencia = individuo.genoma.divergencia
    if divergencia <= DIVERGENCIA_NEUTRA:
        avance = divergencia / DIVERGENCIA_NEUTRA
        return RADIO_DEAMBULAR_CONFORMISTA + avance * (
            RADIO_DEAMBULAR_NEUTRO - RADIO_DEAMBULAR_CONFORMISTA
        )
    avance = (divergencia - DIVERGENCIA_NEUTRA) / (1.0 - DIVERGENCIA_NEUTRA)
    return RADIO_DEAMBULAR_NEUTRO + avance * (RADIO_DEAMBULAR_DIVERGENTE - RADIO_DEAMBULAR_NEUTRO)


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
    """Destino de un paso ocioso, con el sesgo de cohesión del temperamento.

    El paseo puro dispersa al grupo; el sesgo de cohesión lo mantiene cerca.
    Ese sesgo es firmado: el conformista tiende al vecino más cercano y el
    divergente se aparta de él. El conformista va al vecino en el acto —su
    paseo no acumula rumbo—; el resto recuerda el destino hasta llegar, así
    que un radio grande es un rumbo largo y no difusión. Dos individuos con la
    misma semilla no caminan igual según su `divergencia`.
    """
    vecino = _mas_cercano(mundo, individuo)
    sesgo = SESGO_COHESION * (1.0 - 2.0 * individuo.genoma.divergencia)
    if vecino is not None and sesgo > 0.0 and mundo.azar.random() < sesgo:
        individuo.paseo = None
        return vecino.x, vecino.y
    paseo = individuo.paseo
    if paseo is None or _distancia(individuo, paseo) <= TOLERANCIA_PASEO:
        paseo = _nuevo_destino(individuo, mundo, vecino, sesgo)
        if _distancia(individuo, paseo) <= TOLERANCIA_PASEO:
            # Un destino encima de uno mismo no es un rumbo: se pasea al azar.
            paseo = _paseo_al_azar(individuo, mundo)
        individuo.paseo = paseo
    return paseo


def _nuevo_destino(
    individuo: Individuo, mundo: Mundo, vecino: Individuo | None, sesgo: float
) -> tuple[float, float]:
    """Elige el próximo destino del paseo: lejos del vecino, o al azar."""
    radio = radio_deambular(individuo)
    if vecino is not None and sesgo < 0.0 and mundo.azar.random() < -sesgo:
        # Evitación: un punto al otro lado, a radio de paseo del vecino.
        dx = individuo.x - vecino.x
        dy = individuo.y - vecino.y
        norma = math.hypot(dx, dy) or 1.0
        return (
            min(max(individuo.x + radio * dx / norma, 0.0), float(mundo.ancho - 1)),
            min(max(individuo.y + radio * dy / norma, 0.0), float(mundo.alto - 1)),
        )
    return _paseo_al_azar(individuo, mundo)


def _paseo_al_azar(individuo: Individuo, mundo: Mundo) -> tuple[float, float]:
    """Un punto uniforme dentro del radio de paseo del individuo."""
    radio = radio_deambular(individuo)
    x = individuo.x + mundo.azar.uniform(-radio, radio)
    y = individuo.y + mundo.azar.uniform(-radio, radio)
    return (
        min(max(x, 0.0), float(mundo.ancho - 1)),
        min(max(y, 0.0), float(mundo.alto - 1)),
    )


def _distancia(individuo: Individuo, punto: tuple[float, float]) -> float:
    return recursos.distancia(individuo.x, individuo.y, punto[0], punto[1])
