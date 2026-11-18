"""
Beneficios de las combinaciones activas (concepto §8b y §9b).

Una combinación no es solo un nodo más: es una técnica que cambia lo que quien
la conoce puede hacer. Cada una aporta un multiplicador concreto y determinista,
y solo se aplica mientras el nodo está activo **y** el individuo sabe la
habilidad que la técnica requiere. El temperamento no entra en la cuenta: un
conformista que aprendió la habilidad disfruta el mismo bonus que el divergente
que la descubrió. Así la ventaja del descubridor viene de lo que hizo —aprender
la técnica— y no de lo que es.

Si dos combinaciones mejoran lo mismo, se componen multiplicando.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from tribal.core.habilidades import CATALOGO
from tribal.culture.combinaciones import COMBINACIONES
from tribal.culture.grafo import Grafo


@dataclass(frozen=True, slots=True)
class Beneficios:
    """Multiplicadores activos. 1.0 = sin efecto, tal como la Fase 0."""

    bayas: float = 1.0
    caza: float = 1.0
    dano_depredador: float = 1.0
    tasa_sed: float = 1.0

    def a_json(self) -> dict[str, float]:
        return {
            "bayas": round(self.bayas, 4),
            "caza": round(self.caza, 4),
            "dano_depredador": round(self.dano_depredador, 4),
            "tasa_sed": round(self.tasa_sed, 4),
        }


#: Efecto de cada combinación. La tabla cubre el catálogo entero a propósito:
#: una combinación sin efecto sería un nodo decorativo.
EFECTOS: dict[str, Beneficios] = {
    "raedera": Beneficios(bayas=1.25),
    "cuchillo_al_fuego": Beneficios(caza=1.25),
    "turnos_de_vigilia": Beneficios(dano_depredador=0.5),
    "caceria_dirigida": Beneficios(caza=1.5),
    "canto_ritual": Beneficios(tasa_sed=0.9),
}

#: Habilidad que hay que saber para disfrutar el efecto de cada combinación.
#: Descubrir el cruce enseña esta habilidad al autor; los demás la copian
#: enseñando o imitando, como cualquier otra técnica (concepto §3 y §5).
HABILIDAD_POR_COMBINACION: dict[str, str] = {
    "raedera": "fabricar",
    "cuchillo_al_fuego": "fuego",
    "turnos_de_vigilia": "cazar",
    "caceria_dirigida": "cazar",
    "canto_ritual": "ensenar",
}

for _nodo_id in COMBINACIONES:
    if _nodo_id not in EFECTOS:
        raise ValueError(f"la combinación {_nodo_id} no tiene beneficio definido")
    if _nodo_id not in HABILIDAD_POR_COMBINACION:
        raise ValueError(f"la combinación {_nodo_id} no tiene habilidad asociada")
for _nodo_id in EFECTOS:
    if _nodo_id not in COMBINACIONES:
        raise ValueError(f"beneficio de una combinación que no existe: {_nodo_id}")
for _habilidad in HABILIDAD_POR_COMBINACION.values():
    if _habilidad not in CATALOGO:
        raise ValueError(f"habilidad desconocida en los beneficios: {_habilidad}")
del _nodo_id, _habilidad


def activos(grafo: Grafo) -> Beneficios:
    """Multiplicadores de todas las combinaciones activas, en orden de catálogo."""
    return _componer(nodo_id for nodo_id in EFECTOS if grafo.activo(nodo_id))


def conocidos(grafo: Grafo, habilidades: set[str]) -> Beneficios:
    """Multiplicadores que disfruta quien sabe la habilidad de cada combinación.

    `habilidades` es el conjunto de un individuo (`Habilidades.conocidas`). El
    grafo decide qué técnicas existen; el conjunto decide cuáles sabe usar este
    individuo. Dos individuos con las mismas habilidades reciben lo mismo, tenga
    la divergencia que tengan.
    """
    return _componer(
        nodo_id
        for nodo_id in EFECTOS
        if grafo.activo(nodo_id) and HABILIDAD_POR_COMBINACION[nodo_id] in habilidades
    )


def _componer(nodo_ids: Iterable[str]) -> Beneficios:
    resultado = Beneficios()
    for nodo_id in nodo_ids:
        efecto = EFECTOS[nodo_id]
        resultado = Beneficios(
            bayas=resultado.bayas * efecto.bayas,
            caza=resultado.caza * efecto.caza,
            dano_depredador=resultado.dano_depredador * efecto.dano_depredador,
            tasa_sed=resultado.tasa_sed * efecto.tasa_sed,
        )
    return resultado
