"""
Combinaciones plausibles: los nodos de nivel 1 de concepto §8b.

Una combinación es una técnica que no está en el árbol porque no es el
siguiente escalón de una rama, sino el cruce de dos técnicas que ya existen.
El motor solo las crea cuando un **divergente** las intenta (concepto §9b), así
que su `origen` es siempre `combinacion` y nunca se descubren recorriendo
`ARBOL`.

Cada cruce se justifica con lo que ya sabe hacer la tribu:

- `raedera`: la lasca ancha raspada con el filo del bifaz sirve para limpiar
  pieles sin agujerearlas; es el uso más obvio de dos lascas a la vez.
- `cuchillo_al_fuego`: una lasca metida en las brasas se endurece y corta
  mejor; el fuego conservado y la lasca ya existen por separado.
- `canto_ritual`: las proto-palabras puestas en el orden fijo del ritual
  convierten la ceremonia en algo que se puede repetir cantando.
- `caceria_dirigida`: la caza cooperativa con un líder que decide en voz alta
  reparte los papeles y persigue a la presa en una dirección, no en círculos.
- `turnos_de_vigilia`: ahuyentar depredadores con tea y cazar en grupo se
  combinan en turnos de guardia: alguien vigila mientras el resto duerme.

Los ids y los requisitos se validan al importar: un cruce mal escrito falla
antes de que la partida lo intente, no cuando ya lleva 5000 ticks.
"""

from __future__ import annotations

from tribal.culture.arbol import ARBOL, Nodo

_COMBINACIONES: tuple[Nodo, ...] = (
    Nodo(
        "raedera",
        "litica",
        3,
        "Raedera",
        "La lasca ancha raspada con el filo del bifaz limpia la piel sin agujerearla.",
        ("lasca", "bifaz"),
        origen="combinacion",
    ),
    Nodo(
        "cuchillo_al_fuego",
        "litica",
        2,
        "Cuchillo al fuego",
        "La lasca metida en las brasas se endurece y corta mejor.",
        ("lasca", "conservar_brasas"),
        origen="combinacion",
    ),
    Nodo(
        "canto_ritual",
        "simbolico",
        2,
        "Canto ritual",
        "Las proto-palabras puestas en el orden del ritual: el grupo canta lo que hace.",
        ("proto_palabras", "ritual"),
        origen="combinacion",
    ),
    Nodo(
        "caceria_dirigida",
        "roles",
        5,
        "Cacería dirigida",
        "El líder reparte los papeles y la caza cooperativa persigue en una dirección.",
        ("caza_cooperativa", "lider"),
        origen="combinacion",
    ),
    Nodo(
        "turnos_de_vigilia",
        "roles",
        5,
        "Turnos de vigilia",
        "La tea que ahuyenta y la caza en grupo se reparten: alguien vigila mientras el resto duerme.",
        ("ahuyentar_depredadores", "caza_cooperativa"),
        origen="combinacion",
    ),
)

#: Catálogo por id. Se construye a mano para que un id repetido falle al importar.
COMBINACIONES: dict[str, Nodo] = {}
for _nodo in _COMBINACIONES:
    if _nodo.id in ARBOL:
        raise ValueError(f"combinación que ya está en el árbol: {_nodo.id}")
    if _nodo.id in COMBINACIONES:
        raise ValueError(f"combinación duplicada: {_nodo.id}")
    if len(_nodo.requisitos) != 2:
        raise ValueError(f"la combinación {_nodo.id} no cruza exactamente dos nodos")
    for _requisito in _nodo.requisitos:
        if _requisito not in ARBOL:
            raise ValueError(f"la combinación {_nodo.id} exige un nodo que no existe: {_requisito}")
    COMBINACIONES[_nodo.id] = _nodo
del _nodo, _requisito
