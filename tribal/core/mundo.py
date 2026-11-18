"""
El mundo: rejilla de tiles, reloj y generación determinista del terreno.

Todo lo aleatorio sale de `Mundo.azar`, un único `random.Random(seed)`, para
que una partida se pueda repetir. Los individuos se guardan en una lista
ordenada por `id`: el orden de resolución no puede depender de un `set`.
"""

from __future__ import annotations

import random

from tribal.config import SimConfig
from tribal.core import recursos
from tribal.core.modelos import (
    MADUREZ_TICKS,
    Depredador,
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


def crear(seed: int, individuos: int = 12, *, config: SimConfig | None = None) -> Mundo:
    """Genera un mapa nuevo con `individuos` habitantes. Determinista por semilla.

    Las dimensiones y las tasas salen de `config`; sin ella se usan los defaults
    de Fase 0, que es lo que esperan los tests y el camino de la CLI sin fichero.
    """
    if config is None:
        config = SimConfig(seed=seed, individuos=individuos)

    azar = random.Random(seed)
    tiles = [[TipoTile.HIERBA for _ in range(config.ancho)] for _ in range(config.alto)]
    for _ in range(N_LAGOS):
        _mancha(tiles, azar, RADIO_LAGO, TipoTile.AGUA, config.ancho, config.alto)
    for _ in range(N_BOSQUES):
        _mancha(
            tiles,
            azar,
            RADIO_BOSQUE,
            TipoTile.BOSQUE,
            config.ancho,
            config.alto,
            respetar=TipoTile.AGUA,
        )

    mundo = Mundo(
        ancho=config.ancho,
        alto=config.alto,
        tiles=tiles,
        recursos=[],
        individuos=[],
        azar=azar,
        seed=seed,
    )
    recursos.sembrar(mundo)
    _poblar(mundo, individuos)
    if config.depredador_activo and config.depredadores > 0:
        _sembrar_depredadores(mundo, config.depredadores)
    return mundo


def _mancha(
    tiles: list[list[TipoTile]],
    azar: random.Random,
    radio: int,
    tipo: TipoTile,
    ancho: int,
    alto: int,
    respetar: TipoTile | None = None,
) -> None:
    """Dibuja una mancha romboidal del tipo pedido en un punto al azar."""
    centro_x = azar.randint(radio + 2, ancho - radio - 3)
    centro_y = azar.randint(radio + 2, alto - radio - 3)
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
                    longevidad=mundo.azar.uniform(0.85, 1.20),
                ),
                necesidades=Necesidades(
                    energia=mundo.azar.uniform(80.0, 100.0),
                    sed=mundo.azar.uniform(0.0, 15.0),
                ),
                x=float(x),
                y=float(y),
                # La generación fundadora llega adulta, pero con un periodo de
                # asentamiento: la partida no empieza con un baby boom.
                edad=mundo.azar.randint(MADUREZ_TICKS, MADUREZ_TICKS + 600),
                cooldown_reproduccion=MADUREZ_TICKS,
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


def _sembrar_depredadores(mundo: Mundo, cuantos: int) -> None:
    """Coloca los depredadores lejos de la tribu para que la partida empiece en calma."""
    libres = [
        (x, y)
        for y, fila in enumerate(mundo.tiles)
        for x, tipo in enumerate(fila)
        if tipo != TipoTile.AGUA
    ]
    for _ in range(cuantos):
        lejanas = [
            (x, y)
            for x, y in libres
            if all(
                abs(x - individuo.x) + abs(y - individuo.y) >= 12 for individuo in mundo.individuos
            )
        ]
        x, y = mundo.azar.choice(lejanas or libres)
        mundo.depredadores.append(Depredador(x=float(x), y=float(y)))
