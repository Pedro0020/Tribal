"""
Genoma: los rasgos heredables de un individuo (concepto §3 y §5).

Los siete rasgos funcionales viven en [0.5, 1.5] con 1.0 como valor neutro: un
genoma por defecto no cambia ninguna regla del motor, así que la Fase 0 se
comporta igual que antes de existir este módulo. `divergencia` es el
temperamento de concepto §9b y vive en [0.0, 1.0]; aquí solo existe y se
hereda, quien decide con ella es la feature F1-003.

La herencia es la media de los dos progenitores más una mutación normal del
5 % acotada al rango del rasgo. Todo el azar sale de `Mundo.azar`, así que una
partida con la misma semilla produce exactamente los mismos genomas.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Literal

#: Mutación relativa máxima de un rasgo al heredar (5 % de la media).
MUTACION = 0.05
#: Un pelo por dentro del límite: justo en el borde, el redondeo binario deja
#: al hijo unas ulps por encima del 5 % que promete la herencia.
_MUTACION_MAXIMA = MUTACION * (1.0 - 1e-12)
#: Rango de los rasgos funcionales y valor neutro (1.0 no altera nada).
RASGO_MIN = 0.5
RASGO_MAX = 1.5
#: Rango del temperamento divergente (conformista 0.0 <-> divergente 1.0).
DIVERGENCIA_MIN = 0.0
DIVERGENCIA_MAX = 1.0
#: Fronteras del temperamento de concepto §9b: por encima experimenta, por
#: debajo imita, y en medio no destaca en ninguna de las dos cosas.
UMBRAL_DIVERGENTE = 0.6
UMBRAL_CONFORMISTA = 0.4

Temperamento = Literal["divergente", "neutro", "conformista"]

#: Los rasgos, en el orden en que se heredan y se resumen.
RASGOS: tuple[str, ...] = (
    "velocidad",
    "metabolismo",
    "longevidad",
    "fuerza",
    "resistencia",
    "inteligencia",
    "salud",
    "divergencia",
)


@dataclass(frozen=True, slots=True)
class Genoma:
    """Rasgos heredables. `velocidad`, `metabolismo` y `longevidad` ya actuaban en F0."""

    velocidad: float = 1.0
    metabolismo: float = 1.0
    longevidad: float = 1.0
    fuerza: float = 1.0
    resistencia: float = 1.0
    inteligencia: float = 1.0
    salud: float = 1.0
    divergencia: float = 0.5


def temperamento(genoma: Genoma) -> Temperamento:
    """Clasifica el rasgo `divergencia` de concepto §9b.

    El divergente es quien prueba combinaciones nuevas; el conformista, quien
    copia lo que ve funcionar. El neutro no destaca en ninguna de las dos cosas.
    """
    if genoma.divergencia > UMBRAL_DIVERGENTE:
        return "divergente"
    if genoma.divergencia < UMBRAL_CONFORMISTA:
        return "conformista"
    return "neutro"


def heredar(madre: Genoma, padre: Genoma, azar: random.Random) -> Genoma:
    """Media de los dos progenitores con una mutación pequeña y acotada."""
    return Genoma(
        velocidad=_heredar_rasgo(madre.velocidad, padre.velocidad, azar, RASGO_MIN, RASGO_MAX),
        metabolismo=_heredar_rasgo(
            madre.metabolismo, padre.metabolismo, azar, RASGO_MIN, RASGO_MAX
        ),
        longevidad=_heredar_rasgo(madre.longevidad, padre.longevidad, azar, RASGO_MIN, RASGO_MAX),
        fuerza=_heredar_rasgo(madre.fuerza, padre.fuerza, azar, RASGO_MIN, RASGO_MAX),
        resistencia=_heredar_rasgo(
            madre.resistencia, padre.resistencia, azar, RASGO_MIN, RASGO_MAX
        ),
        inteligencia=_heredar_rasgo(
            madre.inteligencia, padre.inteligencia, azar, RASGO_MIN, RASGO_MAX
        ),
        salud=_heredar_rasgo(madre.salud, padre.salud, azar, RASGO_MIN, RASGO_MAX),
        divergencia=_heredar_rasgo(
            madre.divergencia,
            padre.divergencia,
            azar,
            DIVERGENCIA_MIN,
            DIVERGENCIA_MAX,
        ),
    )


def _heredar_rasgo(
    de_madre: float, de_padre: float, azar: random.Random, minimo: float, maximo: float
) -> float:
    """Media de los progenitores * (1 + mutación), dentro de [minimo, maximo]."""
    media = (de_madre + de_padre) / 2.0
    mutacion = max(-_MUTACION_MAXIMA, min(_MUTACION_MAXIMA, azar.gauss(0.0, MUTACION)))
    return min(maximo, max(minimo, media * (1.0 + mutacion)))
