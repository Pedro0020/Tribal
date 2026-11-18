"""
El depredador: persigue a la presa viva más cercana y la muerde al alcanzarla.

Es una regla del mundo, no una decisión de agente: no pregunta, no duda y no
se mete en el agua. Como la presa puede huir más rápido en un sprint corto
(ver `tribal.core.acciones.huir`), la persecución no es una condena: quien
reacciona a tiempo se salva.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from tribal.core.acciones import PASO
from tribal.core.modelos import Depredador, Individuo, Mundo

#: Multiplicador del daño de un mordisco: fijo o calculado por presa.
FactorDano = Callable[[Individuo], float] | float

#: Algo más rápido que el individuo medio (velocidad 1.0) y más lento que una huida.
VELOCIDAD = 1.1
#: Distancia a la que muerde y daño por mordisco; el cooldown evita matar en un tick.
ALCANCE = 0.6
DANO = 30.0
COOLDOWN = 80


def mover(mundo: Mundo, factor_dano: FactorDano = 1.0) -> None:
    """Un tick de cada depredador. El orden de la lista es estable.

    `factor_dano` lo aportan las combinaciones activas: los turnos de vigilia
    dejan al depredador mordiendo a la mitad (concepto §8b). Puede ser un
    número fijo o una función que lo calcule por presa (quien sabe la técnica
    se protege; quien no, no).
    """
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
            _morder(depredador, presa, _factor(factor_dano, presa))
        elif distancia > 0.0:
            _acercarse(mundo, depredador, presa, distancia)


def _factor(factor_dano: FactorDano, presa: Individuo) -> float:
    return factor_dano(presa) if callable(factor_dano) else factor_dano


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


def _morder(depredador: Depredador, presa: Individuo, factor_dano: float = 1.0) -> None:
    salud_antes = presa.necesidades.salud
    presa.necesidades.salud = max(0.0, salud_antes - DANO * factor_dano)
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
