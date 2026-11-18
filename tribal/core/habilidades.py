"""
Habilidades: el conjunto de lo que un individuo sabe hacer (concepto §5).

El catálogo es el vocabulario cerrado de acciones que se pueden aprender y
sitúa cada una en su rama del árbol de conocimiento de concepto §8; la
progresión del árbol la define F1-002, aquí solo el nombre y la rama.

Las habilidades **no** se heredan por genoma: se aprenden viviendo (enseñando
o imitando, concepto §3). Por eso un individuo sin configurar empieza sin
ninguna, y la tribu arranca con `recolectar` para poder comer desde el tick 0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

#: Ramas del árbol de conocimiento (concepto §8).
Rama = Literal["litica", "fuego", "lenguaje", "roles", "simbolico"]


@dataclass(frozen=True, slots=True)
class Habilidad:
    nombre: str
    rama: Rama


CATALOGO: dict[str, Habilidad] = {
    habilidad.nombre: habilidad
    for habilidad in (
        Habilidad("cazar", "litica"),
        Habilidad("recolectar", "roles"),
        Habilidad("fabricar", "litica"),
        Habilidad("fuego", "fuego"),
        Habilidad("ensenar", "lenguaje"),
    )
}
#: Lo que sabe la tribu al empezar: sin recolectar no habría comida en el tick 0.
INICIALES = frozenset({"recolectar"})


@dataclass(slots=True)
class Habilidades:
    """Conjunto de habilidades conocidas. Mutable: se aprende durante la vida."""

    conocidas: set[str] = field(default_factory=set)

    @classmethod
    def iniciales(cls) -> Habilidades:
        """Las de un recién nacido de la tribu (no se heredan del genoma)."""
        return cls(set(INICIALES))

    def sabe(self, nombre: str) -> bool:
        return nombre in self.conocidas

    def aprender(self, nombre: str) -> bool:
        """Añade una habilidad del catálogo. False si ya la sabía o no existe."""
        if nombre not in CATALOGO:
            raise ValueError(f"habilidad desconocida: {nombre!r}")
        if nombre in self.conocidas:
            return False
        self.conocidas.add(nombre)
        return True
