"""
Vocabulario de acciones de Fase 0.

Cada acción **valida y aplica**: comprueba que hay un recurso al alcance o que
el destino es pisable y, si no, devuelve False sin tocar el estado. Quién elige
la acción es `tribal.agents.instinto`; el motor no decide nada por su cuenta.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from tribal.core import recursos
from tribal.core.modelos import Individuo, Mundo, TipoRecurso

NombreAccion = Literal["beber", "comer", "descansar", "moverse", "huir"]

#: Agua que calma una sed entera, y energía que aporta cada tipo de comida.
SED_SACIADA = 70.0
ENERGIA_BAYAS = 40.0
ENERGIA_CAZA = 60.0
ENERGIA_DESCANSO = 0.5
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


def beber(individuo: Individuo, mundo: Mundo) -> bool:
    """Bebe de la fuente de agua más próxima si está al alcance."""
    fuente = recursos.mas_cercano(mundo, individuo, (TipoRecurso.AGUA,))
    if fuente is None or not recursos.en_alcance(individuo, fuente):
        return False
    if not recursos.consumir(fuente):
        return False
    individuo.necesidades.sed = max(0.0, individuo.necesidades.sed - SED_SACIADA)
    return True


def comer(individuo: Individuo, mundo: Mundo) -> bool:
    """Come bayas o caza al alcance; la caza aporta más energía."""
    comida = recursos.mas_cercano(mundo, individuo, (TipoRecurso.BAYAS, TipoRecurso.CAZA))
    if comida is None or not recursos.en_alcance(individuo, comida):
        return False
    if not recursos.consumir(comida):
        return False
    aporte = ENERGIA_CAZA if comida.tipo == TipoRecurso.CAZA else ENERGIA_BAYAS
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


def aplicar(individuo: Individuo, mundo: Mundo, accion: Accion) -> bool:
    """Despacha la acción al verbo que toca. False si no se pudo aplicar."""
    if accion.nombre == "beber":
        return beber(individuo, mundo)
    if accion.nombre == "comer":
        return comer(individuo, mundo)
    if accion.nombre == "descansar":
        return descansar(individuo, mundo)
    if accion.nombre == "moverse":
        if accion.destino is None:
            raise ValueError("la accion moverse necesita destino")
        return moverse(individuo, mundo, accion.destino)
    if accion.amenaza is None:
        raise ValueError("la accion huir necesita amenaza")
    return huir(individuo, mundo, accion.amenaza)
