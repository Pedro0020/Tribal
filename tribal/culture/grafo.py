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
como fuera del árbol en esa métrica. En Fase 1 el motor solo descubre nodos del
árbol, así que vale 0.0 — y ese cero es el que la Fase 3 tiene que mover por
encima del 50 %.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from tribal.core.habilidades import Rama
from tribal.culture.arbol import ARBOL, ORIGENES, RAMAS, Nodo, Origen


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

    def activo(self, nodo_id: str) -> bool:
        nodo = self.nodos.get(nodo_id)
        return nodo is not None and nodo.estado == "activo"

    def descubrir(self, nodo_id: str, autor: int, tick: int, origen: Origen = "arbol") -> Nodo:
        """Crea el nodo si se puede; `PrerequisitoFaltante` si le falta alguno.

        Idempotente: si el nodo ya existe se devuelve tal cual, sin tocar su
        origen, su autor ni su tick.
        """
        existente = self.nodos.get(nodo_id)
        if existente is not None:
            return existente
        plantilla = ARBOL.get(nodo_id)
        if plantilla is None:
            raise ValueError(f"nodo desconocido: {nodo_id!r}")
        faltan = tuple(
            requisito for requisito in plantilla.requisitos if not self.activo(requisito)
        )
        if faltan:
            raise PrerequisitoFaltante(nodo_id, faltan)

        nodo = replace(plantilla, autor=autor, tick=tick, origen=origen)
        self.nodos[nodo_id] = nodo
        self.aristas.extend(Arista(requisito, nodo_id) for requisito in plantilla.requisitos)
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
