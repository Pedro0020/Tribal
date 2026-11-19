"""
Modelos de datos del motor de reglas.

Solo stdlib: la Fase 0 no necesita validación de esquema ni serialización, así
que Pydantic sería una dependencia que aún no paga lo que cuesta. Los valores
inmutables (genoma) son `frozen`; lo que el tick muta (`Necesidades`,
`Individuo`, `Recurso`, `Mundo`) es un dataclass normal.

`Genoma` vive en `tribal.core.genoma` y se reexporta aquí para que los imports
de Fase 0 (`from tribal.core.modelos import Genoma`) sigan valiendo.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Literal

from tribal.core.genoma import Genoma
from tribal.core.habilidades import Habilidades

#: Rejilla del mundo: 60x34 tiles de 8 px -> ventana de 480x272 px.
ANCHO_TILES = 60
ALTO_TILES = 34
TILE_PX = 8

#: Ticks que tarda una cría en ser adulta y ticks que vive un adulto medio.
MADUREZ_TICKS = 300
LONGEVIDAD_TICKS = 3000


class TipoTile(IntEnum):
    HIERBA = 0
    AGUA = 1
    BOSQUE = 2


class TipoRecurso(IntEnum):
    AGUA = 0
    BAYAS = 1
    CAZA = 2


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
    #: Ticks vividos; `madurez` es la edad mínima para reproducirse.
    edad: int = 0
    madurez: int = MADUREZ_TICKS
    #: Ticks que le quedan antes de poder volver a tener cría (0 = disponible).
    cooldown_reproduccion: int = 0
    #: True mientras la última decisión fue huir de un depredador.
    huyendo: bool = False
    #: Lo que sabe hacer; se aprende enseñando o imitando, nunca por genoma.
    habilidades: Habilidades = field(default_factory=Habilidades)
    #: Destino del paseo ocioso. Se recuerda para que el deambular tenga
    #: dirección: el radio del paseo depende del temperamento, no del tick.
    paseo: tuple[float, float] | None = None
    #: Último parche de comida visto (o usado) dentro del radio de percepción.
    #: Es memoria de conducta: no cambia lo que rinde comer, solo a dónde ir
    #: cuando el recurso local se agota.
    ultimo_recurso: tuple[float, float] | None = None
    #: Parche del que salió esa memoria y su `tick_migracion` al recordarla.
    #: Si el parche migra, la memoria queda obsoleta; si no, sigue siendo cierta
    #: aunque el consumo lo deje temporalmente vacío.
    ultimo_parche: int | None = None
    ultimo_parche_migracion: int = -1
    #: Intención forzada por el LLM: `(acción, tick en que caduca)`. Se consume
    #: al usarse; si el tick ya pasó, el instinto manda (ventana de §3).
    intencion_llm: tuple[str, int] | None = None
    #: Peso narrativo ganado por hitos (concepto §10b); no se hereda y no
    #: depende del genoma. Sube en `tribal.agents.saliencia` y decae por tick.
    saliencia: float = 0.0


@dataclass(slots=True)
class Parche:
    """Zona donde vive un tipo de recurso: centro, radio y las fuentes que lo forman.

    Un parche de comida se agota **localmente** (sus fuentes se vacían) y, tras
    un cooldown, migra a otra zona conservando tipo y capacidad. Es el gradiente
    ambiental de la hoja de ruta (eje 3): convierte «dónde estás» en una
    decisión. El agua no migra porque es terreno.
    """

    id: int
    tipo: TipoRecurso
    x: float
    y: float
    radio: float
    #: Ids de las fuentes de `Mundo.recursos` que pertenecen al parche.
    fuentes: list[int]
    #: Cuántas veces se ha reubicado y en qué tick lo hizo por última vez.
    migraciones: int = 0
    tick_migracion: int = 0


@dataclass(slots=True)
class Depredador:
    """Acechador: persigue a la presa viva más cercana y la muerde al alcanzarla."""

    x: float
    y: float
    cooldown: int = 0
    ataques: int = 0
    #: Presas que quedaron sin salud por un mordisco (la muerte se cobra ese tick).
    muertes: int = 0


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
    depredadores: list[Depredador] = field(default_factory=list)
    #: Parches que agrupan las fuentes de recurso (los rellena `recursos.sembrar`).
    parches: list[Parche] = field(default_factory=list)
    #: Estación en curso; `None` mientras no haya estaciones (`ticks_por_estacion=0`).
    estacion: str | None = None

    def pisable(self, x: float, y: float) -> bool:
        """Un tile es pisable si está dentro del mapa y no es agua."""
        tile_x = int(x)
        tile_y = int(y)
        if not (0 <= tile_x < self.ancho and 0 <= tile_y < self.alto):
            return False
        return self.tiles[tile_y][tile_x] != TipoTile.AGUA
