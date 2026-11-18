"""
Vocabulario de acciones del motor.

Cada acción **valida y aplica**: comprueba que hay un recurso al alcance, que
la condición de la práctica se cumple (bosque, agua, un vecino) o que el
destino es pisable y, si no, devuelve False sin tocar el estado. Quién elige
la acción es `tribal.agents.instinto`; el motor no decide nada por su cuenta.

Los verbos ociosos (`tallar`, `frotar_madera`, `hablar`, `cuidar`, `pintar`)
son las prácticas que conectan las ramas del árbol de conocimiento con lo que
la tribu hace: no dan puntos, cuestan energía o el tick, y son la condición
que `tribal.sim` exige para que una rama avance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from tribal.core import recursos
from tribal.core.modelos import Individuo, Mundo, TipoRecurso, TipoTile

NombreAccion = Literal[
    "beber",
    "comer",
    "descansar",
    "moverse",
    "huir",
    "ensenar",
    "cuidar",
    "hablar",
    "tallar",
    "frotar_madera",
    "pintar",
]

#: Agua que calma una sed entera, y energía que aporta cada tipo de comida.
SED_SACIADA = 70.0
ENERGIA_BAYAS = 40.0
ENERGIA_CAZA = 60.0
ENERGIA_DESCANSO = 0.5
#: Rendimiento extra de quien domina la habilidad de la fuente (concepto §5).
BONUS_HABILIDAD = 0.5
#: Alcance de la enseñanza y de la imitación pasiva, en tiles.
DISTANCIA_ENSENANZA = 2.0
RADIO_IMITACION = 2.0
#: Distancia de una conversación y de un cuidado, en tiles.
DISTANCIA_SOCIAL = 2.0
#: Coste de energía de las prácticas ociosas: la técnica gasta al que la hace.
COSTE_TALLAR = 0.5
COSTE_FROTAR_MADERA = 1.0
COSTE_PINTAR = 0.2
COSTE_CUIDAR = 0.2
#: Salud que recupera quien recibe cuidados en un tick.
CUIDADO_SALUD = 0.5
#: Por debajo de esta salud el individuo cuenta como herido y admite cuidados.
#: A 100 el cuidado no tendría ganancia: solo gastaría al cuidador.
SALUD_PARA_CUIDAR = 100.0
#: Probabilidad base; la inteligencia del aprendiz y la cercanía la modulan.
PROB_ENSENANZA = 0.5
PROB_IMITACION = 0.4
#: Tiles por tick. A 60 fps son ~6 tiles/s: cruzar el mapa lleva unos 10 s.
PASO = 0.10
#: Distancia a la que se considera que ya se llegó al destino.
TOLERANCIA = 0.05
#: Direcciones de respaldo, normalizadas, cuando el paso directo está bloqueado.
_DIRECCIONES = (
    (1.0, 0.0),
    (0.0, 1.0),
    (-1.0, 0.0),
    (0.0, -1.0),
    (0.7071067811865476, 0.7071067811865476),
    (-0.7071067811865476, 0.7071067811865476),
    (0.7071067811865476, -0.7071067811865476),
    (-0.7071067811865476, -0.7071067811865476),
)


@dataclass(frozen=True, slots=True)
class Accion:
    nombre: NombreAccion
    destino: tuple[float, float] | None = None
    amenaza: tuple[float, float] | None = None
    #: Individuo al que se dirige una acción social (enseñar).
    objetivo: int | None = None


def beber(individuo: Individuo, mundo: Mundo) -> bool:
    """Bebe de la fuente de agua más próxima si está al alcance."""
    fuente = recursos.mas_cercano(mundo, individuo, (TipoRecurso.AGUA,))
    if fuente is None or not recursos.en_alcance(individuo, fuente):
        return False
    if not recursos.consumir(fuente):
        return False
    individuo.necesidades.sed = max(0.0, individuo.necesidades.sed - SED_SACIADA)
    return True


def comer(
    individuo: Individuo,
    mundo: Mundo,
    *,
    bonus_bayas: float = 1.0,
    bonus_caza: float = 1.0,
) -> bool:
    """Come bayas o caza al alcance; la caza aporta más energía.

    La habilidad de la fuente (recolectar para bayas, cazar para caza) suma un
    50 % de energía y, de paso, quien lo ve comer puede imitarla. Los bonus de
    las combinaciones activas llegan de `tribal.culture.beneficios`: quien
    sabe la técnica cobra más de la misma fuente, sea divergente o no.
    """
    comida = recursos.mas_cercano(mundo, individuo, (TipoRecurso.BAYAS, TipoRecurso.CAZA))
    if comida is None or not recursos.en_alcance(individuo, comida):
        return False
    if not recursos.consumir(comida):
        return False
    aporte = ENERGIA_CAZA if comida.tipo == TipoRecurso.CAZA else ENERGIA_BAYAS
    aporte *= bonus_caza if comida.tipo == TipoRecurso.CAZA else bonus_bayas
    habilidad = _habilidad_de(comida.tipo)
    if habilidad is not None and individuo.habilidades.sabe(habilidad):
        aporte *= 1.0 + BONUS_HABILIDAD
        _imitar(individuo, habilidad, mundo)
    individuo.necesidades.energia = min(100.0, individuo.necesidades.energia + aporte)
    return True


def descansar(individuo: Individuo, mundo: Mundo) -> bool:
    """Recupera energía despacio. Sin efecto si ya está al máximo."""
    if individuo.necesidades.energia >= 100.0:
        return False
    individuo.necesidades.energia = min(100.0, individuo.necesidades.energia + ENERGIA_DESCANSO)
    return True


def moverse(individuo: Individuo, mundo: Mundo, destino: tuple[float, float]) -> bool:
    """Un paso hacia `destino`; si el agua lo bloquea, rodea en tangente."""
    dx = destino[0] - individuo.x
    dy = destino[1] - individuo.y
    distancia = math.hypot(dx, dy)
    if distancia <= TOLERANCIA:
        return False
    paso = PASO * individuo.genoma.velocidad
    ux = dx / distancia
    uy = dy / distancia
    # Primero el paso directo, que es el único que da movimiento continuo.
    if _intentar(individuo, mundo, ux, uy, paso):
        return True
    # Bloqueado por una orilla: se avanza por la tangente izquierda ajustada a
    # la rejilla de 8 direcciones. Seguir siempre el mismo lado es lo que evita
    # el vaivén de elegir «la dirección más parecida al destino» en cada tick.
    izquierda = _tangente(ux, uy, 1.0)
    if _intentar(individuo, mundo, izquierda[0], izquierda[1], paso):
        return True
    # Esquina cerrada: el lado contrario, solo para este paso.
    derecha = _tangente(ux, uy, -1.0)
    return _intentar(individuo, mundo, derecha[0], derecha[1], paso)


def _tangente(ux: float, uy: float, signo: float) -> tuple[float, float]:
    """Dirección de la rejilla de 8 más parecida a girar 90° hacia `signo`."""
    tx = -uy * signo
    ty = ux * signo
    return max(_DIRECCIONES, key=lambda direccion: direccion[0] * tx + direccion[1] * ty)


def _intentar(individuo: Individuo, mundo: Mundo, ux: float, uy: float, paso: float) -> bool:
    nx = individuo.x + paso * ux
    ny = individuo.y + paso * uy
    if not mundo.pisable(nx, ny):
        return False
    individuo.x, individuo.y = nx, ny
    individuo.movido = True
    return True


def huir(individuo: Individuo, mundo: Mundo, amenaza: tuple[float, float]) -> bool:
    """Se aleja de `amenaza` en un sprint de dos pasos, en la dirección opuesta."""
    dx = individuo.x - amenaza[0]
    dy = individuo.y - amenaza[1]
    if dx == 0.0 and dy == 0.0:
        dx = 1.0
    destino = (individuo.x + 4 * dx, individuo.y + 4 * dy)
    primero = moverse(individuo, mundo, destino)
    segundo = moverse(individuo, mundo, destino)
    return primero or segundo


def candidato_a_ensenar(maestro: Individuo, mundo: Mundo) -> Individuo | None:
    """Aprendiz más cercano al que un adulto le pueda enseñar algo (concepto §3)."""
    if maestro.edad < maestro.madurez:
        return None
    mejor: Individuo | None = None
    mejor_clave = (math.inf, 0)
    for otro in mundo.individuos:
        if otro.id == maestro.id:
            continue
        if otro.habilidades.conocidas >= maestro.habilidades.conocidas:
            continue
        distancia = recursos.distancia(maestro.x, maestro.y, otro.x, otro.y)
        if distancia > DISTANCIA_ENSENANZA:
            continue
        clave = (distancia, otro.id)
        if clave < mejor_clave:
            mejor = otro
            mejor_clave = clave
    return mejor


def ensenar(maestro: Individuo, mundo: Mundo, aprendiz: Individuo) -> bool:
    """El adulto transmite una habilidad que el aprendiz todavía no tiene.

    La probabilidad crece con la inteligencia del aprendiz y con la cercanía,
    y sale de `Mundo.azar`: con la misma semilla el resultado se repite.
    """
    if maestro.edad < maestro.madurez:
        return False
    distancia = recursos.distancia(maestro.x, maestro.y, aprendiz.x, aprendiz.y)
    if distancia > DISTANCIA_ENSENANZA:
        return False
    pendiente = next(
        (
            habilidad
            for habilidad in sorted(maestro.habilidades.conocidas)
            if not aprendiz.habilidades.sabe(habilidad)
        ),
        None,
    )
    if pendiente is None:
        return False
    probabilidad = min(
        1.0,
        PROB_ENSENANZA * aprendiz.genoma.inteligencia * _cercania(distancia, DISTANCIA_ENSENANZA),
    )
    if mundo.azar.random() >= probabilidad:
        return False
    return aprendiz.habilidades.aprender(pendiente)


def junto_a(mundo: Mundo, individuo: Individuo, *tipos: TipoTile) -> bool:
    """True si la casilla del individuo o una de sus vecinas es de alguno de `tipos`.

    Es la condición de las prácticas que necesitan materia prima: tallar y
    frotar piden bosque, pintar admite bosque o agua. Se mira la rejilla, no
    los recursos, para que la condición no dependa de que queden bayas.
    """
    tile_x = int(individuo.x)
    tile_y = int(individuo.y)
    for y in range(max(0, tile_y - 1), min(mundo.alto, tile_y + 2)):
        for x in range(max(0, tile_x - 1), min(mundo.ancho, tile_x + 2)):
            if mundo.tiles[y][x] in tipos:
                return True
    return False


def vecino(individuo: Individuo, mundo: Mundo) -> Individuo | None:
    """Otro individuo a distancia social, el más cercano (desempata por id)."""
    mejor: Individuo | None = None
    mejor_clave = (math.inf, 0)
    for otro in mundo.individuos:
        if otro.id == individuo.id:
            continue
        distancia = recursos.distancia(individuo.x, individuo.y, otro.x, otro.y)
        if distancia > DISTANCIA_SOCIAL:
            continue
        clave = (distancia, otro.id)
        if clave < mejor_clave:
            mejor = otro
            mejor_clave = clave
    return mejor


def tallar(individuo: Individuo, mundo: Mundo) -> bool:
    """Talla madera o piedra junto al bosque: la técnica cuesta energía."""
    if not junto_a(mundo, individuo, TipoTile.BOSQUE):
        return False
    individuo.necesidades.energia = max(0.0, individuo.necesidades.energia - COSTE_TALLAR)
    return True


def frotar_madera(individuo: Individuo, mundo: Mundo) -> bool:
    """Frota un palo contra otro junto al bosque; el esfuerzo gasta energía."""
    if not junto_a(mundo, individuo, TipoTile.BOSQUE):
        return False
    individuo.necesidades.energia = max(0.0, individuo.necesidades.energia - COSTE_FROTAR_MADERA)
    return True


def pintar(individuo: Individuo, mundo: Mundo) -> bool:
    """Pinta en la pared o en la orilla: consume el tick y un poco de energía."""
    if not junto_a(mundo, individuo, TipoTile.BOSQUE, TipoTile.AGUA):
        return False
    individuo.necesidades.energia = max(0.0, individuo.necesidades.energia - COSTE_PINTAR)
    return True


def hablar(individuo: Individuo, mundo: Mundo) -> bool:
    """Charlar con el vecino: además de habilitar el nodo, puede transmitir."""
    interlocutor = vecino(individuo, mundo)
    if interlocutor is None:
        return False
    # La conversación es un canal de transmisión más lento que la enseñanza:
    # usa la misma probabilidad y no falla la acción si no prende nada.
    ensenar(individuo, mundo, interlocutor)
    return True


def candidato_a_cuidar(cuidador: Individuo, mundo: Mundo) -> Individuo | None:
    """Herido más cercano (salud < `SALUD_PARA_CUIDAR`) al que cuidar."""
    mejor: Individuo | None = None
    mejor_clave = (math.inf, 0)
    for otro in mundo.individuos:
        if otro.id == cuidador.id:
            continue
        if otro.necesidades.salud >= SALUD_PARA_CUIDAR:
            continue
        distancia = recursos.distancia(cuidador.x, cuidador.y, otro.x, otro.y)
        if distancia > DISTANCIA_SOCIAL:
            continue
        clave = (distancia, otro.id)
        if clave < mejor_clave:
            mejor = otro
            mejor_clave = clave
    return mejor


def cuidar(cuidador: Individuo, mundo: Mundo, atendido: Individuo) -> bool:
    """Acompaña a un herido: el otro recupera salud, el cuidador gasta."""
    if recursos.distancia(cuidador.x, cuidador.y, atendido.x, atendido.y) > DISTANCIA_SOCIAL:
        return False
    cuidador.necesidades.energia = max(0.0, cuidador.necesidades.energia - COSTE_CUIDAR)
    atendido.necesidades.salud = min(100.0, atendido.necesidades.salud + CUIDADO_SALUD)
    return True


def _imitar(modelo: Individuo, habilidad: str, mundo: Mundo) -> None:
    """Quien ve usar una habilidad puede copiarla (concepto §3)."""
    for observador in mundo.individuos:
        if observador.id == modelo.id or observador.habilidades.sabe(habilidad):
            continue
        distancia = recursos.distancia(observador.x, observador.y, modelo.x, modelo.y)
        if distancia > RADIO_IMITACION:
            continue
        probabilidad = min(
            1.0,
            PROB_IMITACION * observador.genoma.inteligencia * _cercania(distancia, RADIO_IMITACION),
        )
        if mundo.azar.random() < probabilidad:
            observador.habilidades.aprender(habilidad)


def _cercania(distancia: float, radio: float) -> float:
    """1.0 encima del modelo, 0.5 en el borde del radio de aprendizaje."""
    return 1.0 - 0.5 * distancia / radio


def _habilidad_de(tipo: TipoRecurso) -> str | None:
    """Habilidad que mejora el rendimiento de cada fuente de comida."""
    if tipo == TipoRecurso.BAYAS:
        return "recolectar"
    if tipo == TipoRecurso.CAZA:
        return "cazar"
    return None


def aplicar(
    individuo: Individuo,
    mundo: Mundo,
    accion: Accion,
    *,
    bonus_bayas: float = 1.0,
    bonus_caza: float = 1.0,
) -> bool:
    """Despacha la acción al verbo que toca. False si no se pudo aplicar."""
    if accion.nombre == "beber":
        return beber(individuo, mundo)
    if accion.nombre == "comer":
        return comer(individuo, mundo, bonus_bayas=bonus_bayas, bonus_caza=bonus_caza)
    if accion.nombre == "descansar":
        return descansar(individuo, mundo)
    if accion.nombre == "moverse":
        if accion.destino is None:
            raise ValueError("la accion moverse necesita destino")
        return moverse(individuo, mundo, accion.destino)
    if accion.nombre == "ensenar":
        if accion.objetivo is None:
            raise ValueError("la accion ensenar necesita objetivo")
        aprendiz = _por_id(mundo, accion.objetivo)
        return ensenar(individuo, mundo, aprendiz)
    if accion.nombre == "cuidar":
        if accion.objetivo is None:
            raise ValueError("la accion cuidar necesita objetivo")
        return cuidar(individuo, mundo, _por_id(mundo, accion.objetivo))
    if accion.nombre == "hablar":
        return hablar(individuo, mundo)
    if accion.nombre == "tallar":
        return tallar(individuo, mundo)
    if accion.nombre == "frotar_madera":
        return frotar_madera(individuo, mundo)
    if accion.nombre == "pintar":
        return pintar(individuo, mundo)
    if accion.amenaza is None:
        raise ValueError("la accion huir necesita amenaza")
    return huir(individuo, mundo, accion.amenaza)


def _por_id(mundo: Mundo, id_: int) -> Individuo:
    """Individuo con ese id; error si la acción social apunta a un fantasma."""
    for otro in mundo.individuos:
        if otro.id == id_:
            return otro
    raise ValueError(f"la accion social apunta a un id inexistente: {id_}")
