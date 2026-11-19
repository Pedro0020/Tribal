"""
El criterio de hecho de `objetivo.md` §3, medido sobre una partida guardada.

Una partida está hecha cuando su grafo de cultura contiene al menos un nodo
activo de cada uno de los **cuatro hitos** (§3.1) y el **50 %** de los nodos
activos nació fuera del árbol (§3.2). Este módulo no simula ni escribe: abre la
base con `Repositorio`, reconstruye el grafo y publica el veredicto.

La métrica es la del SQL de `objetivo.md` §3.2, sin interpretaciones:

```sql
SELECT ROUND(100.0 * SUM(CASE WHEN origen IN ('combinacion','interaccion')
                         THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_fuera_arbol
FROM nodos
WHERE estado = 'activo';
```

`llm` queda **fuera del numerador** a propósito: el KPI mide emergencia desde el
árbol (niveles 1 y 2 de concepto §8b), no que el modelo haya inventado un nodo.
El denominador son todos los nodos activos, incluidos los de nivel 0; excluirlos
daría 100 % por construcción y no mediría nada. `tests/test_kpi.py` ejecuta esa
consulta literal sobre la misma base y compara con `evaluar`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tribal.store.repositorio import Repositorio

#: Umbral de `objetivo.md` §3.2: porcentaje mínimo de nodos activos fuera del árbol.
UMBRAL_PCT = 50.0
#: Orígenes que el KPI cuenta como fuera del árbol: niveles 1 y 2 de concepto §8b.
ORIGENES_FUERA: tuple[str, ...] = ("combinacion", "interaccion")


@dataclass(frozen=True, slots=True)
class Hitos:
    """Los cuatro hitos de `objetivo.md` §3.1, uno por uno y sin promedios."""

    fuego: bool
    herramienta_compuesta: bool
    proto_lenguaje: bool
    mito: bool

    def todos(self) -> bool:
        """True solo si están los cuatro; tres de cuatro no es el criterio."""
        return self.fuego and self.herramienta_compuesta and self.proto_lenguaje and self.mito

    def a_json(self) -> dict[str, bool]:
        return {
            "fuego": self.fuego,
            "herramienta_compuesta": self.herramienta_compuesta,
            "proto_lenguaje": self.proto_lenguaje,
            "mito": self.mito,
        }


@dataclass(frozen=True, slots=True)
class KPI:
    """Los hitos, el porcentaje fuera del árbol y el veredicto global."""

    hitos: Hitos
    pct_fuera_arbol: float
    fuera_arbol: int
    activos: int

    @property
    def veredicto(self) -> bool:
        """Los cuatro hitos **y** el umbral: lo que `objetivo.md` §3 llama hecho."""
        return self.hitos.todos() and self.pct_fuera_arbol >= UMBRAL_PCT

    def a_json(self) -> dict[str, Any]:
        return {
            "hitos": self.hitos.a_json(),
            "pct_fuera_arbol": self.pct_fuera_arbol,
            "fuera_arbol": self.fuera_arbol,
            "activos": self.activos,
            "umbral": UMBRAL_PCT,
            "veredicto": self.veredicto,
        }

    def texto(self, db: Path) -> str:
        """Tabla de texto del informe: hitos, porcentaje y veredicto."""
        lineas = [f"db {db}"]
        for nombre, cumplido in self.hitos.a_json().items():
            lineas.append(f"  {nombre:<22} {'si' if cumplido else 'no'}")
        lineas.append(
            f"  pct_fuera_arbol        {self.pct_fuera_arbol:5.1f} % "
            f"({self.fuera_arbol}/{self.activos}, umbral {UMBRAL_PCT:.1f} %)"
        )
        lineas.append(f"  veredicto              {self.veredicto}")
        return "\n".join(lineas)


def evaluar(db: str | Path) -> KPI:
    """Mide `objetivo.md` §3 sobre la partida guardada en `db`; no simula.

    Lanza `BaseInvalida` si el fichero no es una partida de la tribu.
    """
    repositorio = Repositorio(db, crear=False)
    try:
        grafo = repositorio.cargar().grafo
    finally:
        repositorio.cerrar()

    activos = [nodo for nodo in grafo.nodos.values() if nodo.estado == "activo"]
    entrantes: dict[str, int] = {}
    for arista in grafo.aristas:
        entrantes[arista.destino] = entrantes.get(arista.destino, 0) + 1

    hitos = Hitos(
        # Nodo activo de la rama fuego, que es lo que mira la tabla de §3.1.
        fuego=any(nodo.rama == "fuego" for nodo in activos),
        # Útil construido a partir de dos o más nodos previos.
        herramienta_compuesta=any(
            nodo.rama == "litica" and entrantes.get(nodo.id, 0) >= 2 for nodo in activos
        ),
        # Un paso de lenguaje posterior a gestos/grunidos.
        proto_lenguaje=any(nodo.rama == "lenguaje" and nodo.nivel > 0 for nodo in activos),
        # El esquema no guarda un `tipo` aparte de la rama: el mito es el nodo
        # `mito` del árbol (rama simbolico) y exige palabras + ritual.
        mito=any(nodo.rama == "simbolico" and nodo.id == "mito" for nodo in activos),
    )
    fuera = sum(1 for nodo in activos if nodo.origen in ORIGENES_FUERA)
    pct = round(100.0 * fuera / len(activos), 1) if activos else 0.0
    return KPI(hitos=hitos, pct_fuera_arbol=pct, fuera_arbol=fuera, activos=len(activos))
