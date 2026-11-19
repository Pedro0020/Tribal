"""
Esquema de la respuesta del LLM y validación de la decisión.

El contrato de Fase 2 no es «el modelo genera la acción» sino «elige entre 2–4
candidatas» (`vault/01_PROYECTO/viabilidad-modelo.md`). Por eso el esquema fija
el esqueleto —`accion` dentro del vocabulario real de `core.acciones`— y deja
libres los textos (`objetivo`, `razon`, `dialogo`): constriñe coherencia, no
dirección (stack §8).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast, get_args

from tribal.core.acciones import NombreAccion

#: Vocabulario real del motor; no se duplican los strings a mano.
ACCIONES: tuple[str, ...] = get_args(NombreAccion)

#: Campos de texto libre, en el orden en que se validan.
CAMPOS_TEXTO = ("objetivo", "razon", "dialogo")

#: JSON schema que viaja en `format` a Ollama. Fija los nombres de los campos y
#: la acción; los textos quedan libres para que el modelo pueda sorprender.
ESQUEMA_RESPUESTA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "accion": {"type": "string", "enum": list(ACCIONES)},
        "objetivo": {"type": "string"},
        "razon": {"type": "string"},
        "dialogo": {"type": "string"},
    },
    "required": ["accion", *CAMPOS_TEXTO],
    "additionalProperties": False,
}


def esquema_para(candidatas: Sequence[str]) -> dict[str, Any]:
    """Mismo esqueleto que `ESQUEMA_RESPUESTA`, con el `enum` de las candidatas.

    El modelo no puede inventar una acción fuera de las que las reglas
    consideran viables en este estado (contrato F2-CONTRATO).
    """
    esquema = dict(ESQUEMA_RESPUESTA)
    propiedades = dict(esquema["properties"])
    propiedades["accion"] = {"type": "string", "enum": list(candidatas)}
    esquema["properties"] = propiedades
    return esquema


SISTEMA = (
    "Eres un homínido de una tribu paleolítica. No inventes una acción: elige "
    "exactamente una de las acciones candidatas. Devuelve solo un objeto JSON "
    "con los campos accion, objetivo, razon y dialogo. `razon` explica la "
    "elección en una frase; `dialogo` es lo que dice (cadena vacía si no habla)."
)

#: Few-shot del prompt: dos dilemas resueltos para que el modelo copie el
#: formato de elección, no el contenido.
EJEMPLOS: tuple[dict[str, Any], ...] = (
    {
        "estado": {"energia": 30, "sed": 80, "cerca": ["agua"]},
        "candidatas": ("beber", "descansar", "comer"),
        "accion": "beber",
        "objetivo": "la orilla",
        "razon": "la sed aprieta más que el cansancio",
        "dialogo": "",
    },
    {
        "estado": {"energia": 70, "sed": 20, "vecino": "herido"},
        "candidatas": ("cuidar", "hablar", "comer"),
        "accion": "cuidar",
        "objetivo": "el vecino herido",
        "razon": "está a un paso y perderlo debilita al grupo",
        "dialogo": "aguanta, que ya pasa",
    },
)


@dataclass(frozen=True, slots=True)
class Decision:
    """Lo que el motor puede aplicar: una acción del vocabulario y su relato."""

    accion: NombreAccion
    objetivo: str
    razon: str
    dialogo: str


@dataclass(frozen=True, slots=True)
class ErrorValidacion:
    """Respuesta que no cumple el esquema. Se devuelve, no se lanza."""

    motivo: str


def validar(datos: object) -> Decision | ErrorValidacion:
    """Comprueba el esqueleto y devuelve la decisión o el motivo del fallo."""
    if not isinstance(datos, Mapping):
        return ErrorValidacion("la respuesta no es un objeto JSON")

    accion = datos.get("accion")
    if not isinstance(accion, str):
        return ErrorValidacion("falta 'accion' o no es texto")
    if accion not in ACCIONES:
        return ErrorValidacion(f"accion fuera del vocabulario: {accion!r}")

    textos: dict[str, str] = {}
    for campo in CAMPOS_TEXTO:
        valor = datos.get(campo)
        if not isinstance(valor, str):
            return ErrorValidacion(f"falta '{campo}' o no es texto")
        textos[campo] = valor

    return Decision(
        accion=cast(NombreAccion, accion),
        objetivo=textos["objetivo"],
        razon=textos["razon"],
        dialogo=textos["dialogo"],
    )


def construir_prompt(
    estado: Mapping[str, Any] | str,
    candidatas: Sequence[str],
    ejemplos: Sequence[Mapping[str, Any]] = EJEMPLOS,
) -> list[dict[str, str]]:
    """Mensajes de `/api/chat`: sistema + few-shot + el dilema de este tick.

    `estado` es un diccionario plano o una frase ya redactada. Las candidatas
    son las únicas acciones que el motor considera viables ahora; el modelo
    elige una, no las inventa.
    """
    mensajes: list[dict[str, str]] = [{"role": "system", "content": SISTEMA}]
    for ejemplo in ejemplos:
        mensajes.append(
            {"role": "user", "content": _texto(ejemplo["estado"], ejemplo["candidatas"])}
        )
        mensajes.append(
            {
                "role": "assistant",
                "content": json.dumps(
                    {
                        "accion": ejemplo["accion"],
                        "objetivo": ejemplo["objetivo"],
                        "razon": ejemplo["razon"],
                        "dialogo": ejemplo["dialogo"],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }
        )
    mensajes.append({"role": "user", "content": _texto(estado, candidatas)})
    return mensajes


def _texto(estado: Mapping[str, Any] | str, candidatas: Sequence[str]) -> str:
    cuerpo = (
        estado
        if isinstance(estado, str)
        else json.dumps(estado, ensure_ascii=False, sort_keys=True)
    )
    return (
        f"Estado: {cuerpo}\n"
        f"Acciones candidatas: {', '.join(candidatas)}\n"
        "Elige exactamente una candidata y responde con el JSON del esquema."
    )
