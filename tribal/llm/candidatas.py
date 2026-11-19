"""
Candidatas de decisión: las 2–4 acciones que las reglas ofrecen al LLM.

El contrato de Fase 2 no es «el modelo genera la acción» sino «elige entre
candidatas» (`vault/01_PROYECTO/viabilidad-modelo.md`). Aquí vive el filtro
duro: solo se ofrece lo físicamente posible en este estado —sin agua al alcance
no hay `beber`, sin comida no hay `comer`, sin depredador encima no hay `huir`—
y el orden de la lista es la urgencia de las reglas, que es también el orden de
corrección de `decision.py`.

La invariante es **2–4 siempre que el mundo ofrezca al menos dos acciones
viables**: tras el filtro, si solo queda una, se añade `moverse` a un tile
pisable cercano y, si no lo hay, `descansar`. En un mundo sin ninguna salida
física (ni tiles pisables) queda una sola candidata y `_hay_dilema` no pide
decisión: no es un caso normal, pero está definido.
"""

from __future__ import annotations

from typing import Any, cast

from tribal.agents import instinto
from tribal.agents import necesidades as nec
from tribal.core import acciones, recursos
from tribal.core.acciones import Accion, NombreAccion
from tribal.core.modelos import Individuo, Mundo, TipoRecurso, TipoTile

#: Techo del contrato: el modelo elige entre 2 y 4, nunca entre todo el vocabulario.
MAX_CANDIDATAS = 4


def estado_para(individuo: Individuo, mundo: Mundo) -> dict[str, Any]:
    """Estado serializable y sus hechos de viabilidad, sin objetos vivos.

    Es lo que viaja al prompt y lo que lee la validación del motor: si el
    modelo elige `huir` sin amenaza, el motor lo ve en `amenaza` y corrige.
    """
    agua = recursos.mas_cercano(mundo, individuo, (TipoRecurso.AGUA,))
    comida = recursos.mas_cercano(mundo, individuo, (TipoRecurso.BAYAS, TipoRecurso.CAZA))
    amenaza = instinto.depredador_cercano(individuo, mundo)
    bosque = acciones.junto_a(mundo, individuo, TipoTile.BOSQUE)
    agua_cerca = acciones.junto_a(mundo, individuo, TipoTile.AGUA)
    return {
        "tick": mundo.tick,
        "individuo": individuo.id,
        "energia": round(individuo.necesidades.energia, 1),
        "sed": round(individuo.necesidades.sed, 1),
        "salud": round(individuo.necesidades.salud, 1),
        "agua_al_alcance": agua is not None and recursos.en_alcance(individuo, agua),
        "comida_al_alcance": comida is not None and recursos.en_alcance(individuo, comida),
        "amenaza": amenaza is not None,
        "vecino": acciones.vecino(individuo, mundo) is not None,
        "bosque": bosque,
        "agua_cerca": agua_cerca,
    }


def candidatas(individuo: Individuo, mundo: Mundo) -> list[Accion]:
    """Acciones viables para este estado, de la más urgente a la más neutra.

    Devuelve 2–4 si hay al menos dos acciones viables; si el filtro deja una
    sola, la segunda es `moverse` a un tile pisable o `descansar`. Sin ninguna
    salida física devuelve una: el borde está documentado y `_hay_dilema` lo
    excluye antes de encolar.
    """
    # Borde degenerado: si el individuo no está sobre terreno pisable, no hay
    # movimiento ni práctica posible. Se devuelve una sola y no se pide decisión.
    if not mundo.pisable(individuo.x, individuo.y):
        return [Accion("descansar")]

    estado = estado_para(individuo, mundo)
    urgencias = individuo.necesidades
    nombres: list[str] = []

    if estado["amenaza"]:
        nombres.append("huir")
    if nec.sed_critica(urgencias) and estado["agua_al_alcance"]:
        nombres.append("beber")
    if (nec.energia_baja(urgencias) or nec.agotado(urgencias)) and estado["comida_al_alcance"]:
        nombres.append("comer")
    if nec.agotado(urgencias):
        nombres.append("descansar")

    # Seguir con lo actual: quedarse donde está si hay algo que recuperar.
    if not nombres and urgencias.energia < 100.0:
        nombres.append("descansar")
    if estado["vecino"]:
        nombres.append("hablar")
    if estado["bosque"]:
        nombres.extend(("tallar", "frotar_madera"))
    if estado["bosque"] or estado["agua_cerca"]:
        nombres.append("pintar")
    if estado["agua_al_alcance"]:
        nombres.append("beber")
    if estado["comida_al_alcance"]:
        nombres.append("comer")

    # Si el filtro deja una sola, la segunda es moverse (efecto real) y, si el
    # mundo no tiene ni un tile pisable, descansar. Nunca se inventan acciones.
    unicos = _sin_repetir(nombres)
    destino = None
    if len(unicos) < 2:
        destino = _destino_pisable(individuo, mundo)
        if destino is not None:
            unicos.append("moverse")
    if len(unicos) < 2:
        unicos.append("descansar")
    unicos = _sin_repetir(unicos)[:MAX_CANDIDATAS]

    return [
        Accion(
            cast(NombreAccion, nombre),
            destino=destino if nombre == "moverse" else None,
        )
        for nombre in unicos
    ]


def _destino_pisable(individuo: Individuo, mundo: Mundo) -> tuple[float, float] | None:
    """Un tile vecino al que se puede dar un paso, o `None` si no hay ninguno."""
    for dx, dy in (
        (1.0, 0.0),
        (-1.0, 0.0),
        (0.0, 1.0),
        (0.0, -1.0),
        (1.0, 1.0),
        (1.0, -1.0),
        (-1.0, 1.0),
        (-1.0, -1.0),
    ):
        x = individuo.x + dx
        y = individuo.y + dy
        if mundo.pisable(x, y):
            return (x, y)
    return None


def _sin_repetir(nombres: list[str]) -> list[str]:
    """Conserva el orden de urgencia y elimina repetidos."""
    vistos: set[str] = set()
    unicos: list[str] = []
    for nombre in nombres:
        if nombre in vistos:
            continue
        vistos.add(nombre)
        unicos.append(nombre)
    return unicos
