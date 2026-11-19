"""
Decisión con candidatas: elegir entre 2–4 y corregir solo lo inválido.

`decidir_con_candidatas` construye el cuerpo de `/api/chat` con el enum
restringido a las candidatas de este estado, el prompt few-shot de `esquema` y
temperatura 0.3, y después valida la elección. Si la acción no está entre las
candidatas o viola una restricción dura —`huir` sin amenaza, `beber` sin agua,
`comer` sin comida— la sustituye por la mejor candidata según el orden de las
reglas. Una elección válida no se segundea nunca.

Los fallos de transporte no son elecciones: se devuelven sin decisión y el
individuo sigue por instinto.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from tribal.core.acciones import Accion, NombreAccion
from tribal.llm.cliente import MAX_TOKENS, ClienteLLM
from tribal.llm.esquema import Decision, construir_prompt, esquema_para

#: Temperatura de las decisiones: baja, la del estudio de viabilidad (§8).
TEMPERATURA = 0.3


@dataclass(frozen=True, slots=True)
class Eleccion:
    """Decisión del modelo más lo que el motor tuvo que arreglar, si algo."""

    decision: Decision | None
    corregida: bool = False
    motivo: str | None = None


def decidir_con_candidatas(
    cliente: ClienteLLM,
    estado: Mapping[str, Any] | str,
    candidatas: Sequence[str | Accion],
) -> Eleccion:
    """Pide al modelo una candidata y valida la respuesta contra el estado.

    `candidatas` admite nombres o `Accion`: solo se usa el nombre. Si el
    modelo no responde (transporte caído o timeout) no hay corrección: no hay
    elección que corregir y el motor sigue por instinto.
    """
    nombres = tuple(
        candidata.nombre if isinstance(candidata, Accion) else candidata for candidata in candidatas
    )
    if not nombres:
        return Eleccion(None, motivo="sin acciones candidatas")

    cuerpo: dict[str, Any] = {
        "model": cliente.modelo,
        "messages": construir_prompt(estado, nombres, cliente.ejemplos),
        "format": esquema_para(nombres),
        "stream": False,
        "options": {"temperature": TEMPERATURA, "num_predict": MAX_TOKENS},
    }
    resultado = cliente.intercambiar(cuerpo)

    if resultado.estado == "degradado":
        return Eleccion(None, motivo=resultado.motivo)

    if resultado.estado == "ok" and resultado.decision is not None:
        violacion = _violacion(resultado.decision.accion, nombres, estado)
        if violacion is None:
            return Eleccion(resultado.decision)
        return _corregir(nombres, estado, violacion)

    return _corregir(nombres, estado, resultado.motivo or "respuesta inválida")


def _violacion(
    accion: str,
    candidatas: Sequence[str],
    estado: Mapping[str, Any] | str,
) -> str | None:
    """Motivo por el que la elección no vale, o `None` si es válida."""
    if accion not in candidatas:
        return f"accion fuera de candidatas: {accion}"
    if not isinstance(estado, Mapping):
        return None
    if accion == "huir" and estado.get("amenaza") is False:
        return "huir sin amenaza"
    if accion == "beber" and estado.get("agua_al_alcance") is False:
        return "beber sin agua al alcance"
    if accion == "comer" and estado.get("comida_al_alcance") is False:
        return "comer sin comida al alcance"
    return None


def _corregir(
    candidatas: Sequence[str],
    estado: Mapping[str, Any] | str,
    motivo: str,
) -> Eleccion:
    """Sustituye la elección por la primera candidata que no viola nada."""
    for nombre in candidatas:
        if _violacion(nombre, candidatas, estado) is None:
            return Eleccion(
                Decision(
                    accion=cast(NombreAccion, nombre),
                    objetivo="",
                    razon=f"corrección del motor: {motivo}",
                    dialogo="",
                ),
                corregida=True,
                motivo=motivo,
            )
    return Eleccion(
        Decision(
            accion="descansar",
            objetivo="",
            razon=f"corrección del motor: {motivo}",
            dialogo="",
        ),
        corregida=True,
        motivo=motivo,
    )
