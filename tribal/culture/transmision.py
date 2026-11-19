"""
Transmisión intergeneracional y nodos apagados (concepto §6 y §9).

Una técnica vive mientras alguien vivo pueda practicarla. `HABILIDAD_POR_NODO`
documenta el mapa nodo → habilidad con el que se cuenta eso: las combinaciones
exigen la habilidad que enseña su descubrimiento (`HABILIDAD_POR_COMBINACION`),
y el resto del árbol son prácticas situacionales —tallar, hablar, cuidar,
pintar— que puede ejercer cualquier vivo, así que su portador es cualquiera
que siga en la tribu. Un nodo sin portadores durante `TICKS_SIN_PORTADOR`
ticks se apaga con `Grafo.apagar`; nunca se borra, porque la técnica perdida es
parte del experimento.

La otra ruta de la transmisión, **enseñar**, la resuelve `core.acciones.ensenar`:
exige proximidad y que la tribu tenga lenguaje (`proto_palabras` activo). La
imitación pasiva de quien ve usar una habilidad no depende del lenguaje ni del
temperamento: los conformistas también copian.
"""

from __future__ import annotations

from tribal.core.modelos import Mundo
from tribal.culture.beneficios import HABILIDAD_POR_COMBINACION
from tribal.culture.grafo import Grafo

#: Ticks que un nodo puede quedarse sin portadores antes de apagarse. Una
#: generación larga en la simulación: la técnica no se pierde el tick en que
#: muere su último portador, pero tampoco espera para siempre.
TICKS_SIN_PORTADOR = 120
#: Motivo con el que `sostener` apaga un nodo cuando nadie queda que lo sepa.
MOTIVO_SIN_PORTADORES = "sin portadores"

#: Habilidad que exige cada nodo. Las combinaciones piden la que enseña su
#: descubrimiento; ausente = práctica situacional, la puede hacer cualquier vivo.
HABILIDAD_POR_NODO: dict[str, str] = dict(HABILIDAD_POR_COMBINACION)


def portadores(mundo: Mundo, nodo_id: str) -> int:
    """Vivos que pueden ejercer el nodo: los que saben su habilidad, o todos."""
    habilidad = HABILIDAD_POR_NODO.get(nodo_id)
    if habilidad is None:
        return len(mundo.individuos)
    return sum(1 for individuo in mundo.individuos if individuo.habilidades.sabe(habilidad))


def sostener(grafo: Grafo, mundo: Mundo, desde: dict[str, int], tick: int) -> list[tuple[str, int]]:
    """Apaga los nodos que llevan `TICKS_SIN_PORTADOR` ticks sin nadie que los sepa.

    `desde` es la memoria del motor: nodo_id → tick en que se quedó sin
    portadores. Se limpia sola cuando el nodo vuelve a tener portador o se
    apaga, así que reiniciar la partida no arrastra deuda. Devuelve los nodos
    apagados en este tick como `(id, tick_apagado)`, en orden de grafo.
    """
    apagados: list[tuple[str, int]] = []
    for nodo in list(grafo.nodos.values()):
        if nodo.estado != "activo":
            continue
        if portadores(mundo, nodo.id) > 0:
            desde.pop(nodo.id, None)
            continue
        inicio = desde.setdefault(nodo.id, tick)
        if tick - inicio < TICKS_SIN_PORTADOR:
            continue
        if grafo.apagar(nodo.id, tick, MOTIVO_SIN_PORTADORES) is not None:
            apagados.append((nodo.id, tick))
        desde.pop(nodo.id, None)
    return apagados
