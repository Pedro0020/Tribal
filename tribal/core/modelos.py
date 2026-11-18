"""
Modelos de datos del motor de reglas.

Solo stdlib: la Fase 0 no necesita validación de esquema ni serialización, así
que Pydantic sería una dependencia que aún no paga lo que cuesta. Los valores
inmutables (genoma) son `frozen`; lo que el tick muta (`Necesidades`,
`Individuo`, `Recurso`, `Mundo`) es un dataclass normal.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import IntEnum
from typing import Literal

#: Rejilla del mundo: 60x34 tiles de 8 px -> ventana de 480x272 px.
ANCHO_TILES = 60
ALTO_TILES = 34
TILE_PX = 8


class TipoTile(IntEnum):
    HIERBA = 0
    AGUA = 1
    BOSQUE = 2


class TipoRecurso(IntEnum):
    AGUA = 0
    BAYAS = 1
    CAZA = 2


@dataclass(frozen=True, slots=True)
class Genoma:
    """Rasgos heredables. En Fase 0 solo modulan velocidad y metabolismo."""

    velocidad: float = 1.0
    metabolismo: float = 1.0


@dataclass(slots=True)
class Necesidades:
    """`sed` crece con el tiempo (0 saciado, 100 deshidratado); `salud` es la vida."""

    energia: float = 100.0
    sed: float = 0.0
    salud: float = 100.0


@dataclass(slots=True)
class Recurso:
    id: int
    tipo: TipoRecurso
    x: int
    y: int
    cantidad: int
    capacidad: int
    regeneracion: int
    #: Distancia máxima desde la que se puede usar (el agua se bebe desde la orilla).
    alcance: float


@dataclass(slots=True)
class Individuo:
    id: int
    sexo: Literal["m", "f"]
    genoma: Genoma
    necesidades: Necesidades
    x: float
    y: float
    vivo: bool = True
    movido: bool = False


@dataclass(slots=True)
class Mundo:
    ancho: int
    alto: int
    tiles: list[list[TipoTile]]
    recursos: list[Recurso]
    individuos: list[Individuo]
    azar: random.Random
    seed: int = 0
    tick: int = 0

    def pisable(self, x: float, y: float) -> bool:
        """Un tile es pisable si está dentro del mapa y no es agua."""
        tile_x = int(x)
        tile_y = int(y)
        if not (0 <= tile_x < self.ancho and 0 <= tile_y < self.alto):
            return False
        return self.tiles[tile_y][tile_x] != TipoTile.AGUA
