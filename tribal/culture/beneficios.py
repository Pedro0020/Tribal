"""
Beneficios de las combinaciones activas (concepto §8b y §9b).

Una combinación no es un multiplicador fijo: es una técnica cuyo valor depende
del estado del mundo (hoja de ruta de refinamiento, eje 1). La utilidad de cada
nodo se compone de tres cosas, y ninguna es el temperamento:

- **Escasez del recurso que explota.** Con el recurso lleno la utilidad vale
  1.0 (no hay premio: lo que sobra no distingue a nadie); según se vacía, el
  efecto nominal de `EFECTOS` se recupera proporcionalmente. `escasez` es
  `1 - cantidad_total / capacidad_total`, acotada a [0, 1].
- **Densidad de portadores.** Si todo el grupo conoce la técnica, la ventaja de
  tenerla se diluye: `1 / (1 + 0.1 · portadores)`. No es una propiedad del
  rasgo ni de la técnica, es utilidad de oportunidad: lo que distingue a un
  portador es lo que los demás todavía no pueden hacer.
- **Estación/clima.** `Situacion.estacion` es el gancho, hoy siempre `None`:
  el mundo aún no tiene estaciones, así que no modula nada. Se conectará en
  AMB-001 sin cambiar esta interfaz.

El temperamento no entra en ninguna de las tres: dos individuos con la misma
habilidad reciben exactamente la misma utilidad, sea cual sea su divergencia.
Así la ventaja del descubridor viene de lo que hizo —aprender la técnica— y no
de lo que es. Si dos combinaciones mejoran lo mismo, se componen multiplicando.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tribal.core.habilidades import CATALOGO
from tribal.core.modelos import Mundo, TipoRecurso
from tribal.culture.combinaciones import COMBINACIONES
from tribal.culture.grafo import Grafo

#: Cuánto diluye la ventaja cada portador extra de la técnica.
ESCALA_DENSIDAD = 0.1


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


@dataclass(frozen=True, slots=True)
class Situacion:
    """Estado del mundo que modula la utilidad de las técnicas."""

    #: Escasez por tipo de recurso, en [0, 1]: 0 = lleno, 1 = agotado.
    escasez: dict[TipoRecurso, float]
    #: Estación o clima. Gancho de AMB-001: mientras no exista vale `None`.
    estacion: str | None = None

    def a_json(self) -> dict[str, Any]:
        escasez = {tipo.name.lower(): round(self.escasez.get(tipo, 0.0), 3) for tipo in TipoRecurso}
        return {"escasez": escasez, "estacion": self.estacion}


#: Efecto nominal de cada combinación, el que se cobra con el recurso agotado.
#: La tabla cubre el catálogo entero a propósito: una combinación sin efecto
#: sería un nodo decorativo.
EFECTOS: dict[str, Beneficios] = {
    "raedera": Beneficios(bayas=1.25),
    "cuchillo_al_fuego": Beneficios(caza=1.25),
    "turnos_de_vigilia": Beneficios(dano_depredador=0.5),
    "caceria_dirigida": Beneficios(caza=1.5),
    "canto_ritual": Beneficios(tasa_sed=0.9),
}

#: Recurso cuya escasez hace valiosa cada combinación. La raedera procesa
#: vegetales; el cuchillo y la cacería dirigida valen por la presa; la vigilia
#: protege al grupo que se dispersa cazando y el canto ahorra agua.
RECURSO_POR_COMBINACION: dict[str, TipoRecurso] = {
    "raedera": TipoRecurso.BAYAS,
    "cuchillo_al_fuego": TipoRecurso.CAZA,
    "turnos_de_vigilia": TipoRecurso.CAZA,
    "caceria_dirigida": TipoRecurso.CAZA,
    "canto_ritual": TipoRecurso.AGUA,
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
    if _nodo_id not in RECURSO_POR_COMBINACION:
        raise ValueError(f"la combinación {_nodo_id} no tiene recurso asociado")
for _nodo_id in EFECTOS:
    if _nodo_id not in COMBINACIONES:
        raise ValueError(f"beneficio de una combinación que no existe: {_nodo_id}")
for _nodo_id, _efecto in EFECTOS.items():
    # Cada nodo afecta a una sola dimensión: así su utilidad es un único
    # multiplicador y componer dos técnicas es multiplicar, no interpretar.
    _dimensiones = sum(
        1
        for _valor in (_efecto.bayas, _efecto.caza, _efecto.dano_depredador, _efecto.tasa_sed)
        if _valor != 1.0
    )
    if _dimensiones != 1:
        raise ValueError(f"{_nodo_id}: una combinación afecta a exactamente una dimensión")
for _habilidad in HABILIDAD_POR_COMBINACION.values():
    if _habilidad not in CATALOGO:
        raise ValueError(f"habilidad desconocida en los beneficios: {_habilidad}")
del _nodo_id, _habilidad, _efecto, _dimensiones


def escasez_de(mundo: Mundo, tipo: TipoRecurso) -> float:
    """`1 - cantidad_total / capacidad_total`, en [0, 1]; 0 si no hay fuentes."""
    capacidad = sum(recurso.capacidad for recurso in mundo.recursos if recurso.tipo == tipo)
    if capacidad <= 0:
        return 0.0
    cantidad = sum(recurso.cantidad for recurso in mundo.recursos if recurso.tipo == tipo)
    return min(1.0, max(0.0, 1.0 - cantidad / capacidad))


def situacion(mundo: Mundo, *, estacion: str | None = None) -> Situacion:
    """Foto del estado del mundo en este tick. `estacion` queda para AMB-001."""
    return Situacion(
        escasez={tipo: escasez_de(mundo, tipo) for tipo in TipoRecurso},
        estacion=estacion,
    )


def portadores(mundo: Mundo, nodo_id: str) -> int:
    """Vivos que saben la habilidad de la combinación."""
    habilidad = HABILIDAD_POR_COMBINACION[nodo_id]
    return sum(1 for individuo in mundo.individuos if individuo.habilidades.sabe(habilidad))


def utilidad(nodo_id: str, situacion: Situacion, portadores: int) -> float:
    """Multiplicador de `nodo_id` ajustado al mundo; 1.0 si el recurso sobra.

    Con la escasez a 1 y un solo portador vale el efecto nominal de `EFECTOS`
    (por ejemplo 1.25 para la raedera); con el recurso lleno vale 1.0. La
    densidad de portadores solo diluye la ventaja, nunca la vuelve negativa.
    """
    efecto = _ventaja(EFECTOS[nodo_id])
    escasez = situacion.escasez.get(RECURSO_POR_COMBINACION[nodo_id], 0.0)
    densidad = 1.0 / (1.0 + ESCALA_DENSIDAD * max(0, portadores))
    return 1.0 + efecto * escasez * densidad


def utilidades(grafo: Grafo, mundo: Mundo, situacion: Situacion) -> dict[str, float]:
    """Utilidad de cada combinación activa este tick, en orden de catálogo."""
    return {
        nodo_id: utilidad(nodo_id, situacion, portadores(mundo, nodo_id))
        for nodo_id in EFECTOS
        if grafo.activo(nodo_id)
    }


def activos(grafo: Grafo, mundo: Mundo, estado: Situacion | None = None) -> Beneficios:
    """Multiplicadores de todas las combinaciones activas, en orden de catálogo."""
    if estado is None:
        estado = situacion(mundo)
    return _componer(utilidades(grafo, mundo, estado))


def conocidos(grafo: Grafo, habilidades: set[str], utilidades_tick: dict[str, float]) -> Beneficios:
    """Multiplicadores que disfruta quien sabe la habilidad de cada combinación.

    `habilidades` es el conjunto de un individuo (`Habilidades.conocidas`) y
    `utilidades_tick` el mapa nodo→utilidad que devuelve `utilidades`. El
    temperamento no aparece por ningún lado: dos individuos con las mismas
    habilidades reciben lo mismo, tenga la divergencia que tengan.
    """
    return _componer(
        {
            nodo_id: utilidades_tick[nodo_id]
            for nodo_id in EFECTOS
            if grafo.activo(nodo_id) and HABILIDAD_POR_COMBINACION[nodo_id] in habilidades
        }
    )


def _ventaja(efecto: Beneficios) -> float:
    """Cuánto se aparta del neutro el efecto nominal: +0.25, -0.5, -0.1…"""
    for valor in (efecto.bayas, efecto.caza, efecto.dano_depredador, efecto.tasa_sed):
        if valor != 1.0:
            return valor - 1.0
    return 0.0


def _componer(utilidades_tick: dict[str, float]) -> Beneficios:
    resultado = Beneficios()
    for nodo_id, valor in utilidades_tick.items():
        efecto = EFECTOS[nodo_id]
        resultado = Beneficios(
            bayas=resultado.bayas * (valor if efecto.bayas != 1.0 else 1.0),
            caza=resultado.caza * (valor if efecto.caza != 1.0 else 1.0),
            dano_depredador=(
                resultado.dano_depredador * (valor if efecto.dano_depredador != 1.0 else 1.0)
            ),
            tasa_sed=resultado.tasa_sed * (valor if efecto.tasa_sed != 1.0 else 1.0),
        )
    return resultado
