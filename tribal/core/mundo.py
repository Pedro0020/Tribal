"""
El mundo: rejilla de tiles, reloj y generación determinista del terreno.

Todo lo aleatorio sale de `Mundo.azar`, un único `random.Random(seed)`, para
que una partida se pueda repetir. Los individuos se guardan en una lista
ordenada por `id`: el orden de resolución no puede depender de un `set`.
"""

from __future__ import annotations

import random

from tribal.core import recursos
from tribal.core.modelos import (
    ALTO_TILES,
    ANCHO_TILES,
    Genoma,
    Individuo,
    Mundo,
    Necesidades,
    TipoTile,
)

#: Lagos y manchas de bosque por mapa; el resto es hierba.
N_LAGOS = 3
N_BOSQUES = 6
RADIO_LAGO = 2
RADIO_BOSQUE = 2


def crear(seed: int, individuos: int = 12) -> Mundo:
    """Genera un mapa nuevo con `individuos` habitantes. Determinista por semilla."""
    azar = random.Random(seed)
    tiles = [[TipoTile.HIERBA for _ in range(ANCHO_TILES)] for _ in range(ALTO_TILES)]
    for _ in range(N_LAGOS):
        _mancha(tiles, azar, RADIO_LAGO, TipoTile.AGUA)
    for _ in range(N_BOSQUES):
        _mancha(tiles, azar, RADIO_BOSQUE, TipoTile.BOSQUE, respetar=TipoTile.AGUA)

    mundo = Mundo(
        ancho=ANCHO_TILES,
        alto=ALTO_TILES,
        tiles=tiles,
        recursos=[],
        individuos=[],
        azar=azar,
        seed=seed,
    )
    recursos.sembrar(mundo)
    _poblar(mundo, individuos)
    return mundo


def _mancha(
    tiles: list[list[TipoTile]],
    azar: random.Random,
    radio: int,
    tipo: TipoTile,
    respetar: TipoTile | None = None,
) -> None:
    """Dibuja una mancha romboidal del tipo pedido en un punto al azar."""
    centro_x = azar.randint(radio + 2, ANCHO_TILES - radio - 3)
    centro_y = azar.randint(radio + 2, ALTO_TILES - radio - 3)
    for dy in range(-radio, radio + 1):
        for dx in range(-radio, radio + 1):
            if abs(dx) + abs(dy) > radio:
                continue
            x = centro_x + dx
            y = centro_y + dy
            if respetar is not None and tiles[y][x] == respetar:
                continue
            tiles[y][x] = tipo


def _poblar(mundo: Mundo, cuantos: int) -> None:
    libres = [
        (x, y)
        for y, fila in enumerate(mundo.tiles)
        for x, tipo in enumerate(fila)
        if tipo != TipoTile.AGUA
    ]
    if len(libres) < cuantos:
        raise ValueError("el mapa no tiene casillas libres para tanta gente")

    usados: list[tuple[int, int]] = []
    for id_ in range(1, cuantos + 1):
        x, y = _casilla_libre(mundo.azar, libres, usados)
        usados.append((x, y))
        mundo.individuos.append(
            Individuo(
                id=id_,
                sexo="m" if id_ % 2 else "f",
                genoma=Genoma(
                    velocidad=mundo.azar.uniform(0.85, 1.15),
                    metabolismo=mundo.azar.uniform(0.85, 1.20),
                ),
                necesidades=Necesidades(
                    energia=mundo.azar.uniform(80.0, 100.0),
                    sed=mundo.azar.uniform(0.0, 15.0),
                ),
                x=float(x),
                y=float(y),
            )
        )
    mundo.individuos.sort(key=lambda individuo: individuo.id)


def _casilla_libre(
    azar: random.Random, libres: list[tuple[int, int]], usados: list[tuple[int, int]]
) -> tuple[int, int]:
    """Casilla pisable y a dos tiles como mínimo de las ya ocupadas."""
    for _ in range(200):
        x, y = azar.choice(libres)
        if all(abs(x - ux) + abs(y - uy) >= 2 for ux, uy in usados):
            return x, y
    return azar.choice(libres)
