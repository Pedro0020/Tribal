"""
Beneficios de las combinaciones y tradiciones activas (concepto §8b y §9b).

Una combinación no es un multiplicador fijo: es una técnica cuyo valor depende
del estado del mundo (hoja de ruta de refinamiento, eje 1). La utilidad de cada
nodo se compone de tres cosas, y ninguna es el temperamento:

- **Escasez del recurso que explota.** Con el recurso lleno la utilidad vale
  1.0 (no hay premio: lo que sobra no distingue a nadie); según se vacía, el
  efecto nominal se recupera proporcionalmente. `escasez` es
  `1 - cantidad_total / capacidad_total`, acotada a [0, 1].
- **Densidad de portadores.** Si todo el grupo conoce la técnica, la ventaja de
  tenerla se diluye: `1 / (1 + 0.1 · portadores)`. No es una propiedad del
  rasgo ni de la técnica, es utilidad de oportunidad: lo que distingue a un
  portador es lo que los demás todavía no pueden hacer.
- **Estación/clima.** `Situacion.estacion` modula el efecto de las técnicas que
  explotan un recurso estacional: en invierno la vegetación y la presa escasean
  más, así que la misma técnica vale un 25 % más. El agua no se toca: un lago
  no se vuelve invierno. Con `estacion=None` (sin estaciones) nada cambia.

El temperamento no entra en ninguna de las tres: dos individuos con la misma
habilidad reciben exactamente la misma utilidad, sea cual sea su divergencia.
Así la ventaja del descubridor viene de lo que hizo —aprender la técnica— y no
de lo que es. Las cinco combinaciones curadas se componen multiplicando si
mejoran lo mismo.

Desde F3-006 hay dos clases de nodo con efecto, además del catálogo curado:

- **combinación dinámica** (`origen="combinacion"`): nace de dos nodos activos
  de la misma rama o de ramas adyacentes. Su efecto es un −1 % o −2 % de sed
  cuya magnitud sale de los dos ids. No toca bayas ni caza: veinte cruces
  multiplicando comida desestabilizaban la ecología de 8000 ticks. Las
  variantes de una misma rama no se apilan: `_agrupar` deja la mejor, no
  `1.01^20`.
- **tradición** (`origen="interaccion"`): su efecto es **cultural**, no un
  multiplicador de recursos: cuando la rama descubre un nodo, la costumbre
  suma peso narrativo (`saliencia.SUBIDA["tradicion_practica"]`). Diez
  tradiciones y veinte combinaciones multiplicando comida a la vez
  desestabilizaban la ecología; una costumbre cambia quién protagoniza la
  práctica, no cuánto come la tribu. La tradición apunta a la práctica con una
  arista, pero no es una copia 1:1: tiene id, contenido y efecto propios, y se
  apaga si el grupo deja de imitarla.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tribal.core.habilidades import CATALOGO, Rama
from tribal.core.modelos import Mundo, TipoRecurso
from tribal.culture.arbol import Nodo
from tribal.culture.combinaciones import COMBINACIONES
from tribal.culture.grafo import Grafo

#: Cuánto diluye la ventaja cada portador extra de la técnica.
ESCALA_DENSIDAD = 0.1
#: En invierno el recurso estacional escasea más: la técnica que lo exprime vale
#: esta fracción extra. El agua no entra: un lago no cambia de estación.
BONUS_INVIERNO = 0.25
RECURSOS_ESTACIONALES = (TipoRecurso.BAYAS, TipoRecurso.CAZA)
#: Habilidad de una combinación dinámica, según la rama propuesta.
HABILIDAD_POR_RAMA: dict[Rama, str] = {
    "litica": "fabricar",
    "fuego": "fuego",
    "lenguaje": "ensenar",
    "roles": "cazar",
    "simbolico": "ensenar",
}


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
class Perfil:
    """Efecto, recurso y habilidad de un nodo que cambia el mundo."""

    efecto: Beneficios
    recurso: TipoRecurso
    habilidad: str


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


#: Efecto nominal de cada combinación del catálogo, el que se cobra con el
#: recurso agotado. La tabla cubre el catálogo entero a propósito: una
#: combinación sin efecto sería un nodo decorativo.
EFECTOS: dict[str, Beneficios] = {
    "raedera": Beneficios(bayas=1.25),
    "cuchillo_al_fuego": Beneficios(caza=1.25),
    "turnos_de_vigilia": Beneficios(dano_depredador=0.5),
    "caceria_dirigida": Beneficios(caza=1.5),
    "canto_ritual": Beneficios(tasa_sed=0.9),
}

#: Recurso cuya escasez hace valiosa cada combinación del catálogo. La raedera
#: procesa vegetales; el cuchillo y la cacería dirigida valen por la presa; la
#: vigilia protege al grupo que se dispersa cazando y el canto ahorra agua.
RECURSO_POR_COMBINACION: dict[str, TipoRecurso] = {
    "raedera": TipoRecurso.BAYAS,
    "cuchillo_al_fuego": TipoRecurso.CAZA,
    "turnos_de_vigilia": TipoRecurso.CAZA,
    "caceria_dirigida": TipoRecurso.CAZA,
    "canto_ritual": TipoRecurso.AGUA,
}

#: Habilidad que hay que saber para disfrutar el efecto de cada combinación
#: curada. Descubrir el cruce enseña esta habilidad al autor; los demás la
#: copian enseñando o imitando, como cualquier otra técnica (concepto §3 y §5).
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


def perfil_de(nodo: Nodo, grafo: Grafo) -> Perfil | None:
    """Efecto, recurso y habilidad de `nodo`; None si no cambia el mundo.

    El catálogo curado manda. Una tradición toma el efecto pequeño de su rama.
    Una combinación dinámica deriva recurso y efecto de las ramas de sus dos
    requisitos, y la habilidad de la rama que propuso el modelo. Los nodos del
    árbol y los que no tienen efecto devuelven None.
    """
    if nodo.id in EFECTOS:
        return Perfil(
            EFECTOS[nodo.id],
            RECURSO_POR_COMBINACION[nodo.id],
            HABILIDAD_POR_COMBINACION[nodo.id],
        )
    if nodo.origen == "combinacion":
        return _perfil_combinacion(nodo, grafo)
    return None


def _perfil_combinacion(nodo: Nodo, grafo: Grafo) -> Perfil | None:
    """Deriva el efecto de la pareja: las dos ramas eligen la magnitud.

    No toca la comida: diecisiete combinaciones multiplicando bayas o caza
    desestabilizan la ecología de 8000 ticks. Ahorra sed (−1 % o −2 %) y la
    magnitud sale de los dos requisitos, no de una tabla fija.
    """
    if len(nodo.requisitos) != 2:
        return None
    requisitos = [grafo.nodos.get(requisito) for requisito in nodo.requisitos]
    if any(requisito is None for requisito in requisitos):
        return None
    semilla = sum(sum(ord(caracter) for caracter in requisito) for requisito in nodo.requisitos)
    tasa = 0.99 if semilla % 2 == 0 else 0.98
    return Perfil(
        Beneficios(tasa_sed=tasa),
        TipoRecurso.AGUA,
        HABILIDAD_POR_RAMA[nodo.rama],
    )


def escasez_de(mundo: Mundo, tipo: TipoRecurso) -> float:
    """`1 - cantidad_total / capacidad_total`, en [0, 1]; 0 si no hay fuentes."""
    capacidad = sum(recurso.capacidad for recurso in mundo.recursos if recurso.tipo == tipo)
    if capacidad <= 0:
        return 0.0
    cantidad = sum(recurso.cantidad for recurso in mundo.recursos if recurso.tipo == tipo)
    return min(1.0, max(0.0, 1.0 - cantidad / capacidad))


def situacion(mundo: Mundo, *, estacion: str | None = None) -> Situacion:
    """Foto del estado del mundo en este tick, con la estación en curso."""
    return Situacion(
        escasez={tipo: escasez_de(mundo, tipo) for tipo in TipoRecurso},
        estacion=estacion,
    )


def portadores(mundo: Mundo, nodo_id: str) -> int:
    """Vivos que saben la habilidad de una combinación del catálogo."""
    return portadores_de(mundo, HABILIDAD_POR_COMBINACION[nodo_id])


def portadores_de(mundo: Mundo, habilidad: str) -> int:
    """Vivos que saben `habilidad`."""
    return sum(1 for individuo in mundo.individuos if individuo.habilidades.sabe(habilidad))


def utilidad(nodo_id: str, situacion: Situacion, portadores: int) -> float:
    """Multiplicador de una combinación del catálogo; 1.0 si el recurso sobra.

    Con la escasez a 1 y un solo portador vale el efecto nominal de `EFECTOS`
    (por ejemplo 1.25 para la raedera); con el recurso lleno vale 1.0. La
    densidad de portadores solo diluye la ventaja, nunca la vuelve negativa.
    En invierno el efecto de las técnicas estacionales sube un 25 %.
    """
    perfil = Perfil(
        EFECTOS[nodo_id],
        RECURSO_POR_COMBINACION[nodo_id],
        HABILIDAD_POR_COMBINACION[nodo_id],
    )
    return _utilidad_perfil(perfil, situacion, portadores)


def utilidad_de(nodo: Nodo, grafo: Grafo, situacion: Situacion, portadores: int) -> float:
    """Multiplicador de cualquier nodo con efecto (catálogo, dinámica o tradición)."""
    perfil = perfil_de(nodo, grafo)
    if perfil is None:
        return 1.0
    return _utilidad_perfil(perfil, situacion, portadores)


def _utilidad_perfil(perfil: Perfil, situacion: Situacion, portadores: int) -> float:
    efecto = _ventaja(perfil.efecto)
    if situacion.estacion == "invierno" and perfil.recurso in RECURSOS_ESTACIONALES:
        efecto *= 1.0 + BONUS_INVIERNO
    escasez = situacion.escasez.get(perfil.recurso, 0.0)
    densidad = 1.0 / (1.0 + ESCALA_DENSIDAD * max(0, portadores))
    return 1.0 + efecto * escasez * densidad


def utilidades(grafo: Grafo, mundo: Mundo, situacion: Situacion) -> dict[str, float]:
    """Utilidad de cada nodo activo con efecto este tick, en orden de grafo."""
    utilidades_tick: dict[str, float] = {}
    for nodo in grafo.nodos.values():
        if nodo.estado != "activo":
            continue
        perfil = perfil_de(nodo, grafo)
        if perfil is None:
            continue
        utilidades_tick[nodo.id] = _utilidad_perfil(
            perfil, situacion, portadores_de(mundo, perfil.habilidad)
        )
    return utilidades_tick


def activos(grafo: Grafo, mundo: Mundo, estado: Situacion | None = None) -> Beneficios:
    """Multiplicadores de los nodos activos con efecto, sin apilar variantes.

    Las combinaciones dinámicas y las tradiciones de una misma rama comparten
    habilidad y dimensión; contar las 17 variantes a la vez convertiría un +5 %
    en un ×2.3. Se aplica la mejor de cada `(origen, rama)`; el catálogo curado
    sí se compone entero, porque son cinco técnicas distintas por diseño.
    """
    if estado is None:
        estado = situacion(mundo)
    return _componer(grafo, _agrupar(grafo, utilidades(grafo, mundo, estado)))


def conocidos(grafo: Grafo, habilidades: set[str], utilidades_tick: dict[str, float]) -> Beneficios:
    """Multiplicadores que disfruta quien sabe la habilidad de cada nodo.

    `habilidades` es el conjunto de un individuo (`Habilidades.conocidas`) y
    `utilidades_tick` el mapa nodo→utilidad que devuelve `utilidades`. El
    temperamento no aparece por ningún lado: dos individuos con las mismas
    habilidades reciben lo mismo, tenga la divergencia que tengan.
    """
    filtradas: dict[str, float] = {}
    for nodo_id, valor in utilidades_tick.items():
        nodo = grafo.nodos.get(nodo_id)
        if nodo is None or nodo.estado != "activo":
            continue
        perfil = perfil_de(nodo, grafo)
        if perfil is not None and perfil.habilidad in habilidades:
            filtradas[nodo_id] = valor
    return _componer(grafo, _agrupar(grafo, filtradas))


def _ventaja(efecto: Beneficios) -> float:
    """Cuánto se aparta del neutro el efecto nominal: +0.25, -0.5, -0.1…"""
    for valor in (efecto.bayas, efecto.caza, efecto.dano_depredador, efecto.tasa_sed):
        if valor != 1.0:
            return valor - 1.0
    return 0.0


def _agrupar(grafo: Grafo, utilidades_tick: dict[str, float]) -> dict[str, float]:
    """Catálogo entero y la mejor variante de cada `(origen, rama)` no curada.

    Evita que 17 combinaciones dinámicas de fuego, que comparten la habilidad
    `fuego`, se apilen como 1.05^17 sobre la caza del mismo portador.
    """
    elegidas: dict[str, float] = {}
    mejores: dict[tuple[str, str], tuple[float, str]] = {}
    for nodo_id, valor in utilidades_tick.items():
        if nodo_id in EFECTOS:
            elegidas[nodo_id] = valor
            continue
        nodo = grafo.nodos.get(nodo_id)
        if nodo is None:
            continue
        clave = (nodo.origen, nodo.rama)
        if clave not in mejores or valor > mejores[clave][0]:
            mejores[clave] = (valor, nodo_id)
    elegidas.update({nodo_id: valor for valor, nodo_id in mejores.values()})
    return elegidas


def _componer(grafo: Grafo, utilidades_tick: dict[str, float]) -> Beneficios:
    resultado = Beneficios()
    for nodo_id, valor in utilidades_tick.items():
        nodo = grafo.nodos.get(nodo_id)
        if nodo is None:
            continue
        perfil = perfil_de(nodo, grafo)
        if perfil is None:
            continue
        efecto = perfil.efecto
        resultado = Beneficios(
            bayas=resultado.bayas * (valor if efecto.bayas != 1.0 else 1.0),
            caza=resultado.caza * (valor if efecto.caza != 1.0 else 1.0),
            dano_depredador=(
                resultado.dano_depredador * (valor if efecto.dano_depredador != 1.0 else 1.0)
            ),
            tasa_sed=resultado.tasa_sed * (valor if efecto.tasa_sed != 1.0 else 1.0),
        )
    return resultado
