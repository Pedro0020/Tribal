"""
El depredador: persigue a la presa viva más cercana y la muerde al alcanzarla.

Es una regla del mundo, no una decisión de agente: no pregunta, no duda y no
se mete en el agua. Como la presa puede huir más rápido en un sprint corto
(ver `tribal.core.acciones.huir`), la persecución no es una condena: quien
reacciona a tiempo se salva.
"""

from __future__ import annotations

import math

from tribal.core.acciones import PASO
from tribal.core.modelos import Depredador, Individuo, Mundo

#: Algo más rápido que el individuo medio (velocidad 1.0) y más lento que una huida.
VELOCIDAD = 1.1
#: Distancia a la que muerde y daño por mordisco; el cooldown evita matar en un tick.
ALCANCE = 0.6
DANO = 30.0
COOLDOWN = 80


def mover(mundo: Mundo) -> None:
    """Un tick de cada depredador. El orden de la lista es estable."""
    for depredador in mundo.depredadores:
        # Digestión: tras morder se queda quieto; así la presa puede escapar.
        if depredador.cooldown > 0:
            depredador.cooldown -= 1
            continue
        presa = _presa_mas_cercana(mundo, depredador)
        if presa is None:
            continue
        distancia = math.hypot(presa.x - depredador.x, presa.y - depredador.y)
        if distancia <= ALCANCE:
            _morder(depredador, presa)
        elif distancia > 0.0:
            _acercarse(mundo, depredador, presa, distancia)


def _presa_mas_cercana(mundo: Mundo, depredador: Depredador) -> Individuo | None:
    if not mundo.individuos:
        return None
    return min(
        mundo.individuos,
        key=lambda individuo: (
            math.hypot(individuo.x - depredador.x, individuo.y - depredador.y),
            individuo.id,
        ),
    )


def _morder(depredador: Depredador, presa: Individuo) -> None:
    salud_antes = presa.necesidades.salud
    presa.necesidades.salud = max(0.0, salud_antes - DANO)
    depredador.cooldown = COOLDOWN
    depredador.ataques += 1
    # La muerte se comprueba en el mismo tick, tras la ronda del depredador:
    # aquí solo se anota la causa para el resumen.
    if salud_antes > 0.0 and presa.necesidades.salud <= 0.0:
        depredador.muertes += 1


def _acercarse(mundo: Mundo, depredador: Depredador, presa: Individuo, distancia: float) -> None:
    paso = PASO * VELOCIDAD
    nx = depredador.x + paso * (presa.x - depredador.x) / distancia
    ny = depredador.y + paso * (presa.y - depredador.y) / distancia
    if mundo.pisable(nx, ny):
        depredador.x, depredador.y = nx, ny
