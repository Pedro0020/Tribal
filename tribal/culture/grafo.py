"""
El grafo de cultura: nodos descubiertos, aristas y el KPI de emergencia.

`Grafo` es el guardián del árbol (concepto §8): un nodo solo nace si todos sus
requisitos están activos, y nace ya con su `origen` (concepto §8b), que es un
dato de nacimiento. `Nodo` es `frozen`, así que no hay setter que lo reescriba
después; volver a descubrir el mismo nodo es idempotente y devuelve el que ya
existía, con su autor y su tick originales.

`pct_fuera_arbol` es el KPI de `objetivo.md` §3.2: porcentaje de nodos activos
de origen `combinacion` o `interaccion` — los niveles 1 y 2 de concepto §8b —
sobre **todos** los activos. `arbol` no es emergencia y `llm` tampoco cuenta
como fuera del árbol en esa métrica. En Fase 1 el motor recorre el árbol
entero y, en crisis, descubre combinaciones; las tradiciones añaden nodos de
interacción, así que el KPI ya no vale 0.0. Subirlo por encima del 50 % sigue
siendo el trabajo de la Fase 3.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from tribal.core.habilidades import Rama
from tribal.culture.arbol import ARBOL, NIVEL_ORIGEN, ORIGENES, RAMAS, Nodo, Origen
from tribal.culture.combinaciones import COMBINACIONES


class PrerequisitoFaltante(ValueError):
    """Se intentó descubrir un nodo cuyos requisitos no están activos."""

    def __init__(self, nodo_id: str, faltan: tuple[str, ...]) -> None:
        self.nodo_id = nodo_id
        self.faltan = faltan
        super().__init__(f"{nodo_id}: faltan prerrequisitos {', '.join(faltan)}")


@dataclass(frozen=True, slots=True)
class Arista:
    """Prerrequisito → nodo descubierto."""

    origen: str
    destino: str


class Grafo:
    """Lo que la tribu ha descubierto, en RAM. La persistencia es de `store`."""

    def __init__(self) -> None:
        self.nodos: dict[str, Nodo] = {}
        self.aristas: list[Arista] = []
        #: Cuántas veces se ha practicado cada nodo del árbol.
        self.veces_usado: dict[str, int] = {}
        #: Cuántas de esas veces las usó un conformista que no lo descubrió.
        self.imitado: dict[str, int] = {}
        #: Quiénes imitaron cada nodo y cuándo; de aquí salen las tradiciones.
        self.imitadores: dict[str, set[int]] = {}
        self.ultimo_imitador: dict[str, int] = {}
        self.imitaciones_tick: dict[str, list[int]] = {}

    def activo(self, nodo_id: str) -> bool:
        nodo = self.nodos.get(nodo_id)
        return nodo is not None and nodo.estado == "activo"

    def ultimo_activo(self, rama: Rama) -> Nodo | None:
        """Nodo del árbol más avanzado de `rama`; None si la rama no ha empezado.

        Las combinaciones no cuentan: no son la técnica que practica el
        instinto, sino un cruce que solo nace cuando alguien lo intenta.
        """
        activos = [
            nodo
            for nodo in self.nodos.values()
            if nodo.rama == rama and nodo.estado == "activo" and nodo.id in ARBOL
        ]
        return max(activos, key=lambda nodo: (nodo.nivel, nodo.id)) if activos else None

    def registrar_uso(
        self, nodo_id: str, usuario: int, es_conformista: bool, tick: int = 0
    ) -> bool:
        """Suma un uso del nodo. True si además cuenta como imitación.

        La cultura es colectiva y no se guarda por individuo: la transmisión se
        mide con el contador `imitado` del nodo. Un conformista que usa una
        técnica que no descubrió está copiando lo que vio funcionar (§9b).
        `imitadores` y `imitaciones_tick` guardan quién y cuándo porque de ahí
        nace una tradición (nivel 2 de §8b).
        """
        nodo = self.nodos.get(nodo_id)
        if nodo is None:
            return False
        self.veces_usado[nodo_id] = self.veces_usado.get(nodo_id, 0) + 1
        if not es_conformista or nodo.autor == usuario:
            return False
        self.imitado[nodo_id] = self.imitado.get(nodo_id, 0) + 1
        self.imitadores.setdefault(nodo_id, set()).add(usuario)
        self.ultimo_imitador[nodo_id] = usuario
        self.imitaciones_tick.setdefault(nodo_id, []).append(tick)
        return True

    def imitaciones_en_ventana(self, nodo_id: str, tick: int, ventana: int) -> int:
        """Imitaciones del nodo en los últimos `ventana` ticks (incluye el actual)."""
        return sum(
            1 for momento in self.imitaciones_tick.get(nodo_id, ()) if tick - momento <= ventana
        )

    def descubrir(self, nodo_id: str, autor: int, tick: int, origen: Origen = "arbol") -> Nodo:
        """Crea el nodo si se puede; `PrerequisitoFaltante` si le falta alguno.

        Idempotente: si el nodo ya existe se devuelve tal cual, sin tocar su
        origen, su autor ni su tick.
        """
        existente = self.nodos.get(nodo_id)
        if existente is not None:
            return existente
        plantilla = ARBOL.get(nodo_id) or COMBINACIONES.get(nodo_id)
        if plantilla is None:
            raise ValueError(f"nodo desconocido: {nodo_id!r}")
        faltan = tuple(
            requisito for requisito in plantilla.requisitos if not self.activo(requisito)
        )
        if faltan:
            raise PrerequisitoFaltante(nodo_id, faltan)

        if nodo_id in COMBINACIONES:
            origen = "combinacion"
        nodo = replace(plantilla, autor=autor, tick=tick, origen=origen)
        self.nodos[nodo_id] = nodo
        self.aristas.extend(Arista(requisito, nodo_id) for requisito in plantilla.requisitos)
        return nodo

    def agregar(self, nodo: Nodo) -> Nodo:
        """Inserta un nodo ya construido (tradiciones) validando sus requisitos.

        `descubrir` solo conoce el árbol y las combinaciones; una tradición no
        está en ninguno de los dos catálogos porque su plantilla nace de la
        dinámica social. Idempotente, como el resto de descubrimientos.
        """
        existente = self.nodos.get(nodo.id)
        if existente is not None:
            return existente
        faltan = tuple(requisito for requisito in nodo.requisitos if not self.activo(requisito))
        if faltan:
            raise PrerequisitoFaltante(nodo.id, faltan)
        self.nodos[nodo.id] = nodo
        self.aristas.extend(Arista(requisito, nodo.id) for requisito in nodo.requisitos)
        return nodo

    def avanzar(self, rama: Rama, autor: int, tick: int) -> Nodo | None:
        """Descubre el primer nodo no descubierto de `rama` cuyos requisitos se cumplen.

        `None` si la rama ya está entera o su siguiente escalón aún no tiene base.
        """
        for nodo_id in ARBOL:
            plantilla = ARBOL[nodo_id]
            if plantilla.rama != rama or nodo_id in self.nodos:
                continue
            if all(self.activo(requisito) for requisito in plantilla.requisitos):
                return self.descubrir(nodo_id, autor=autor, tick=tick)
        return None

    def pct_fuera_arbol(self) -> float:
        """KPI de `objetivo.md` §3.2: % de nodos activos de origen `combinacion` o `interaccion`.

        Son los niveles 1 y 2 de concepto §8b. `arbol` no es emergencia y `llm`
        no cuenta como fuera del árbol, igual que el SQL de `objetivo.md` §3.2.
        """
        activos = [nodo for nodo in self.nodos.values() if nodo.estado == "activo"]
        if not activos:
            return 0.0
        fuera = sum(1 for nodo in activos if nodo.origen in ("combinacion", "interaccion"))
        return round(100.0 * fuera / len(activos), 1)

    def nodos_por_origen(self) -> dict[str, int]:
        """Cuántos nodos activos hay de cada nivel de emergencia (los cuatro, con ceros)."""
        activos = [nodo for nodo in self.nodos.values() if nodo.estado == "activo"]
        return {origen: sum(1 for nodo in activos if nodo.origen == origen) for origen in ORIGENES}

    def a_json(self) -> dict[str, Any]:
        """Dict serializable y determinista: nodos por rama y nivel, aristas y KPI."""
        nodos = sorted(
            self.nodos.values(), key=lambda nodo: (RAMAS.index(nodo.rama), nodo.nivel, nodo.id)
        )
        return {
            "nodos": [_nodo_a_json(nodo) for nodo in nodos],
            "aristas": [
                {"origen": arista.origen, "destino": arista.destino} for arista in self.aristas
            ],
            "pct_fuera_arbol": self.pct_fuera_arbol(),
            "nodos_por_origen": self.nodos_por_origen(),
            "nivel_max": max((NIVEL_ORIGEN[nodo.origen] for nodo in nodos), default=0),
        }


def _nodo_a_json(nodo: Nodo) -> dict[str, Any]:
    return {
        "id": nodo.id,
        "rama": nodo.rama,
        "nivel": nodo.nivel,
        "titulo": nodo.titulo,
        "origen": nodo.origen,
        "autor": nodo.autor,
        "tick": nodo.tick,
    }
