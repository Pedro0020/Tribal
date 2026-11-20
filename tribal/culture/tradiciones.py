"""
Tradiciones: los nodos de nivel 2 de concepto §8b.

Una tradición no la inventa nadie: nace cuando una práctica que ya existe se
copia lo suficiente. La condición es social, no individual —varios
conformistas distintos imitando la misma práctica, o suficientes imitaciones
seguidas— y por eso su `origen` es `interaccion` y no `arbol`.

F3-006 corrigió el mecanismo: antes se creaba un nodo `tradicion_<nodo>` por
cada nodo imitado, así que el KPI subía duplicando el grafo. Ahora una tradición
es una **variante social con identidad propia**:

- no nace de un nodo `llm` (el KPI excluye `llm` a propósito; copiarlo sería
  lavar el numerador);
- hay como mucho `MAX_POR_RAMA` por rama, con título, contenido y efecto
  propios: mientras la costumbre vive, un descubrimiento de esa rama gana
  `saliencia.SUBIDA["tradicion_practica"]` (peso narrativo, no un multiplicador
  de comida que desestabilice la ecología);
- apunta a la práctica imitada con una arista, pero no la copia 1:1;
- persiste solo mientras el grupo la siga imitando: si pasan
  `TICKS_SIN_IMITACION` ticks sin una imitación, `sostener` la apaga con
  `Grafo.apagar`, igual que cualquier técnica perdida.

La tradición es de la tribu: sigue activa aunque muera el último que la imitó,
pero no sobrevive al olvido del grupo.
"""

from __future__ import annotations

from tribal.core.habilidades import Rama
from tribal.culture.arbol import RAMAS, Nodo
from tribal.culture.grafo import Grafo

#: Prefijo de los ids de tradición. El id no depende de un nodo concreto: la
#: tradición tiene identidad propia (`tradicion_<rama>_<n>`).
PREFIJO = "tradicion_"
#: Tope de tradiciones por rama. Una basta para que la costumbre exista sin
#: convertir el grafo en un espejo del árbol; una segunda variante sería sabor.
MAX_POR_RAMA = 1
#: Ticks sin una imitación antes de apagar la tradición (concepto §8b: el
#: nivel 2 persiste *porque el grupo lo copia*).
TICKS_SIN_IMITACION = 1200
#: Motivo con el que `sostener` apaga una tradición que dejó de copiarse.
MOTIVO_SIN_IMITACION = "sin imitaciones"

#: Título y contenido propios de cada variante. El texto dice qué práctica se
#: copia y qué efecto pequeño tiene; no es la plantilla de un alias.
_VARIANTES: dict[Rama, tuple[tuple[str, str], ...]] = {
    "litica": (
        (
            "Cantera del grupo",
            "El grupo elige la piedra en voz alta y repite el gesto: cada hallazgo "
            "de la talla se cuenta y pesa más en la memoria.",
        ),
    ),
    "fuego": (
        (
            "Vigilia del fuego",
            "Nadie deja las brasas solo: el turno se repite y el hallazgo junto al "
            "fuego se recuerda más.",
        ),
    ),
    "lenguaje": (
        (
            "Decires del grupo",
            "Las mismas palabras vuelven en el mismo orden: lo que se descubre "
            "hablando se cuenta más.",
        ),
    ),
    "roles": (
        (
            "Reparto aprendido",
            "Cada cual sabe a quién seguir y el reparto se repite: el hallazgo del "
            "oficio se recuerda más.",
        ),
    ),
    "simbolico": (
        (
            "Rito heredado",
            "El mismo gesto en el mismo orden calma al grupo: el hallazgo del rito "
            "se cuenta y pesa más.",
        ),
    ),
}


def _tradiciones_de(grafo: Grafo, rama: Rama) -> list[Nodo]:
    return [
        nodo for nodo in grafo.nodos.values() if nodo.id.startswith(PREFIJO) and nodo.rama == rama
    ]


def activa_en(grafo: Grafo, rama: Rama) -> bool:
    """True si la rama tiene al menos una tradición viva."""
    return any(nodo.estado == "activo" for nodo in _tradiciones_de(grafo, rama))


def evaluar(grafo: Grafo, tick: int) -> Nodo | None:
    """Crea como mucho una tradición por tick y la devuelve; None si no toca.

    Recorre las ramas en orden y, dentro de cada una, los nodos en orden de id
    para que la tradición que nace primero no dependa del orden de un
    diccionario. El tope cuenta también las apagadas: una costumbre perdida no
    se sustituye por otra en la misma rama.
    """
    for rama in RAMAS:
        if len(_tradiciones_de(grafo, rama)) >= MAX_POR_RAMA:
            continue
        for nodo_id in sorted(grafo.nodos):
            original = grafo.nodos[nodo_id]
            if nodo_id.startswith(PREFIJO) or original.estado != "activo":
                continue
            if original.rama != rama or original.origen == "llm":
                continue
            imitadores = len(grafo.imitadores.get(nodo_id, ()))
            en_ventana = grafo.imitaciones_en_ventana(nodo_id, tick, 600)
            if imitadores < 3 and en_ventana < 5:
                continue
            ordinal = len(_tradiciones_de(grafo, rama))
            autor = grafo.ultimo_imitador.get(nodo_id, original.autor)
            return grafo.agregar(_nueva_tradicion(original, rama, ordinal, autor=autor, tick=tick))
    return None


def sostener(grafo: Grafo, tick: int) -> list[tuple[str, int]]:
    """Apaga las tradiciones que llevan `TICKS_SIN_IMITACION` ticks sin copiarse.

    Devuelve las apagadas en este tick como `(id, tick_apagado)`, en orden de
    id. El reloj de una tradición recién nacida es su propio `tick` de
    nacimiento: si nadie la imita en la ventana, se apaga.
    """
    apagadas: list[tuple[str, int]] = []
    for nodo_id in sorted(grafo.nodos):
        nodo = grafo.nodos[nodo_id]
        if not nodo_id.startswith(PREFIJO) or nodo.estado != "activo":
            continue
        imitaciones = grafo.imitaciones_tick.get(nodo_id, ())
        ultima = max(imitaciones, default=nodo.tick)
        if tick - ultima < TICKS_SIN_IMITACION:
            continue
        if grafo.apagar(nodo_id, tick, MOTIVO_SIN_IMITACION) is not None:
            apagadas.append((nodo_id, tick))
    return apagadas


def _nueva_tradicion(original: Nodo, rama: Rama, ordinal: int, *, autor: int, tick: int) -> Nodo:
    """La variante social `ordinal` de `rama`, con identidad propia."""
    titulo, contenido = _VARIANTES[rama][ordinal]
    return Nodo(
        id=f"{PREFIJO}{rama}_{ordinal + 1}",
        rama=rama,
        nivel=original.nivel + 1,
        titulo=titulo,
        contenido=contenido,
        requisitos=(original.id,),
        origen="interaccion",
        autor=autor,
        tick=tick,
    )
