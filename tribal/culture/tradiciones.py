"""
Tradiciones: los nodos de nivel 2 de concepto §8b.

Una tradición no la inventa nadie: nace cuando una práctica que ya existe se
copia lo suficiente. La condición es social, no individual —varios
conformistas distintos imitando el mismo nodo, o suficientes imitaciones
seguidas—, y por eso su `origen` es `interaccion` y no `arbol`.

El nodo queda en el grafo con el autor y el tick del momento en que se alcanzó
el umbral. Su `requisito` es el nodo imitado, así que la tradición se apaga
sola si el original desapareciera (hoy no hay apagado: es el mismo grafo que
persiste mientras viva la partida).
"""

from __future__ import annotations

from tribal.core.habilidades import Rama
from tribal.culture.arbol import Nodo
from tribal.culture.grafo import Grafo

#: Prefijo de los ids de tradición: `tradicion_<nodo imitado>`.
PREFIJO = "tradicion_"
#: Umbral social. Tres imitadores distintos ya son grupo; cinco imitaciones
#: seguidas (aunque sean del mismo) ya son costumbre.
IMITADORES_MINIMOS = 3
IMITACIONES_MINIMAS = 5
#: Ventana en ticks para contar las imitaciones seguidas.
VENTANA_IMITACIONES = 600
#: Una técnica heredada del árbol se convierte en oficio; lo demás, en símbolo.
RAMAS_TECNICAS: frozenset[Rama] = frozenset({"litica", "fuego"})


def id_tradicion(nodo_id: str) -> str:
    """Id de la tradición que nacería de `nodo_id`."""
    return f"{PREFIJO}{nodo_id}"


def evaluar(grafo: Grafo, tick: int) -> Nodo | None:
    """Crea como mucho una tradición por tick y la devuelve; None si no toca.

    Recorre los nodos en orden de id para que, con la misma partida, la
    tradición que nace primero no dependa del orden de un diccionario.
    """
    for nodo_id in sorted(grafo.nodos):
        original = grafo.nodos[nodo_id]
        if nodo_id.startswith(PREFIJO) or original.estado != "activo":
            continue
        if id_tradicion(nodo_id) in grafo.nodos:
            continue
        imitadores = len(grafo.imitadores.get(nodo_id, ()))
        en_ventana = grafo.imitaciones_en_ventana(nodo_id, tick, VENTANA_IMITACIONES)
        if imitadores < IMITADORES_MINIMOS and en_ventana < IMITACIONES_MINIMAS:
            continue
        autor = grafo.ultimo_imitador.get(nodo_id, original.autor)
        return grafo.agregar(_nueva_tradicion(original, autor=autor, tick=tick))
    return None


def _nueva_tradicion(original: Nodo, autor: int, tick: int) -> Nodo:
    rama: Rama = "roles" if original.rama in RAMAS_TECNICAS else "simbolico"
    titulo = f"Tradición de {original.titulo.lower()}"
    return Nodo(
        id=id_tradicion(original.id),
        rama=rama,
        nivel=original.nivel + 1,
        titulo=titulo,
        contenido=(
            f"El grupo repite {original.titulo.lower()} sin que nadie lo mande: "
            "lo que era un gesto suelto ya es costumbre."
        ),
        requisitos=(original.id,),
        origen="interaccion",
        autor=autor,
        tick=tick,
    )
