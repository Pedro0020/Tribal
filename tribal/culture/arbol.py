"""
El árbol de plausibilidad (concepto §8) y el nodo del grafo de cultura (§8b).

Cada rama es una escalera de niveles: los de nivel 0 no exigen nada y el resto
pide los anteriores de su rama. Dos nodos cruzan ramas, y por el mismo motivo:
sin lo que aporta la otra rama el paso no sería cultura sino un guion —

- `mito` pide `proto_palabras` + `ritual`: un relato compartido sin palabras ni
  ceremonia que lo repita sería una anécdota, no un mito.
- `lider` pide `anciano` + `caza_cooperativa`: la autoridad aparece cuando hay
  una caza coordinada que necesita a alguien que decida en voz alta.

`Nodo` es `frozen` a propósito: `origen` se escribe al nacer (concepto §8b) y
no se reescribe después, porque es el dato con el que se mide la emergencia.
`ARBOL` guarda la plantilla de cada nodo (`origen` `arbol`, `autor` y `tick` a
0); quien lo crea de verdad es `tribal.culture.grafo.Grafo.descubrir`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from tribal.core.habilidades import Rama

#: Ramas del árbol, en el orden en que se leen los informes.
RAMAS: tuple[Rama, ...] = ("litica", "fuego", "lenguaje", "roles", "simbolico")
#: Orígenes de un nodo. Concepto §8b define tres niveles —0 `arbol`, 1
#: `combinacion`, 2 `interaccion`—; `llm` no es un nivel, es el origen de una
#: propuesta del modelo, y el KPI de `objetivo.md` §3.2 no lo cuenta como fuera
#: del árbol. `nodos_por_origen` los recorre todos.
ORIGENES: tuple[str, ...] = ("arbol", "combinacion", "interaccion", "llm")

Origen = Literal["arbol", "combinacion", "interaccion", "llm"]
#: Un nodo `apagado` no se borra: la técnica perdida es parte del experimento.
Estado = Literal["activo", "apagado"]


@dataclass(frozen=True, slots=True)
class Nodo:
    """Un paso del grafo de cultura. Congelado: el origen no se reescribe."""

    id: str
    rama: Rama
    nivel: int
    titulo: str
    contenido: str
    #: Ids que tienen que estar activos para que el nodo pueda nacer.
    requisitos: tuple[str, ...] = ()
    origen: Origen = "arbol"
    estado: Estado = "activo"
    #: Individuo que lo descubrió y tick en que nació; 0 = plantilla del árbol.
    autor: int = 0
    tick: int = 0


_CATALOGO: tuple[Nodo, ...] = (
    # Lítica: del canto rodado a la caza en grupo.
    Nodo(
        "guijarro",
        "litica",
        0,
        "Guijarro",
        "Un canto rodado con filo de golpe: corta y raspa.",
    ),
    Nodo(
        "lasca",
        "litica",
        1,
        "Lasca",
        "Al golpear el guijarro sale una lasca afilada, pensada de antemano.",
        ("guijarro",),
    ),
    Nodo(
        "bifaz",
        "litica",
        2,
        "Bifaz",
        "Dos caras talladas en simetría: un útil que se puede volver a afilar.",
        ("lasca",),
    ),
    Nodo(
        "punta_de_lanza",
        "litica",
        3,
        "Punta de lanza",
        "La lasca atada a un palo alcanza a la presa antes de que huya.",
        ("bifaz",),
    ),
    Nodo(
        "caza_cooperativa",
        "litica",
        4,
        "Caza cooperativa",
        "Varios cazadores la cercan: la punta sola no trae caza mayor.",
        ("punta_de_lanza",),
    ),
    # Fuego: verlo, conservarlo, hacerlo y usarlo.
    Nodo(
        "observar_rayo",
        "fuego",
        0,
        "Observar el rayo",
        "El fuego que nace del cielo se deja ver, pero todavía no se toca.",
    ),
    Nodo(
        "conservar_brasas",
        "fuego",
        1,
        "Conservar brasas",
        "Un fuego que no se apaga se vuelve un bien que hay que cuidar.",
        ("observar_rayo",),
    ),
    Nodo(
        "friccion",
        "fuego",
        2,
        "Fricción",
        "El palo que gira sobre la madera saca fuego cuando el cielo no lo da.",
        ("conservar_brasas",),
    ),
    Nodo(
        "cocinar",
        "fuego",
        3,
        "Cocinar",
        "La carne al fuego ablanda y rinde más.",
        ("friccion",),
    ),
    Nodo(
        "ahuyentar_depredadores",
        "fuego",
        4,
        "Ahuyentar depredadores",
        "Una tea encendida entre la presa y el acechador.",
        ("cocinar",),
    ),
    # Lenguaje: del cuerpo a la transmisión de lo que no está delante.
    Nodo(
        "gestos",
        "lenguaje",
        0,
        "Gestos y gruñidos",
        "Señalar, empujar, gruñir: lo que el cuerpo dice sin palabras.",
    ),
    Nodo(
        "proto_palabras",
        "lenguaje",
        1,
        "Proto-palabras",
        "Un sonido concreto para una cosa concreta, repetido por convención.",
        ("gestos",),
    ),
    Nodo(
        "vocabulario",
        "lenguaje",
        2,
        "Vocabulario",
        "Las palabras se combinan y se puede decir lo que no está delante.",
        ("proto_palabras",),
    ),
    Nodo(
        "transmision_eficaz",
        "lenguaje",
        3,
        "Transmisión eficaz",
        "Contar un procedimiento a quien no lo ha visto acelera todo lo demás.",
        ("vocabulario",),
    ),
    # Roles: los dos oficios de base, el que recuerda y quien decide.
    Nodo(
        "cazador",
        "roles",
        0,
        "Cazador",
        "Quien va a por la presa con el arma hecha.",
    ),
    Nodo(
        "recolectora",
        "roles",
        0,
        "Recolectora",
        "Quien sabe dónde y cuándo hay fruto.",
    ),
    Nodo(
        "anciano",
        "roles",
        1,
        "Anciano",
        "Ya no caza ni recolecta, pero recuerda: el relevo de ambos oficios.",
        ("cazador", "recolectora"),
    ),
    Nodo(
        "chaman",
        "roles",
        2,
        "Chamán",
        "El anciano al que el grupo deja hablar con lo que no se ve.",
        ("anciano",),
    ),
    Nodo(
        "lider",
        "roles",
        2,
        "Líder",
        "La caza coordinada necesita a alguien que decida en voz alta.",
        ("anciano", "caza_cooperativa"),
    ),
    # Simbólico: pintar, repetir, contar y distinguirse.
    Nodo(
        "arte_rupestre",
        "simbolico",
        0,
        "Arte rupestre",
        "Pintar en la pared deja el gesto fuera del cuerpo.",
    ),
    Nodo(
        "ritual",
        "simbolico",
        1,
        "Ritual",
        "Los mismos gestos, en el mismo orden, repetidos por el grupo.",
        ("arte_rupestre",),
    ),
    Nodo(
        "mito",
        "simbolico",
        2,
        "Mito",
        "Un relato que explica el ritual; sin palabras ni ceremonia sería una anécdota.",
        ("proto_palabras", "ritual"),
    ),
    Nodo(
        "identidad_grupo",
        "simbolico",
        3,
        "Identidad del grupo",
        "El mito distingue a esta banda de la de enfrente.",
        ("mito",),
    ),
)

#: Catálogo por id. Se construye a mano para que un id repetido falle al importar.
ARBOL: dict[str, Nodo] = {}
for _nodo in _CATALOGO:
    if _nodo.id in ARBOL:
        raise ValueError(f"nodo duplicado en el árbol: {_nodo.id}")
    ARBOL[_nodo.id] = _nodo
del _nodo
