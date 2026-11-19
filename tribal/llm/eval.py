"""
`llm eval`: mide el contrato candidatas → elige → valida en escenarios simples.

En CI se corre con un **backend simulado competente** que elige la candidata de
mayor utilidad según el estado. Eso no mide la calidad de `tribal-llm`: mide
que el filtrado de candidatas, el esquema restringido y la validación funcionan.
La calidad del modelo real se mide aparte, contra Ollama:

    uv run python -m tribal llm eval --backend http

Un escenario es un estado con una acción claramente correcta: sed alta con agua
al alcance, hambre con comida, agotamiento, depredador y un vecino en calma.
"""

from __future__ import annotations

import json
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from tribal.core.acciones import NombreAccion
from tribal.core.genoma import Genoma
from tribal.core.modelos import (
    Depredador,
    Individuo,
    Mundo,
    Necesidades,
    Recurso,
    TipoRecurso,
    TipoTile,
)
from tribal.llm.candidatas import candidatas, estado_para
from tribal.llm.cliente import ClienteLLM, Transporte
from tribal.llm.decision import decidir_con_candidatas

#: Escenarios que corre `llm eval` por defecto.
ESCENARIOS_POR_DEFECTO = 20


@dataclass(frozen=True, slots=True)
class Escenario:
    """Un estado simple y la acción que cualquier regla sensata elegiría."""

    nombre: str
    individuo: Individuo
    mundo: Mundo
    esperada: NombreAccion


def escenarios() -> list[Escenario]:
    """La batería fija: 20 estados con una respuesta claramente correcta."""
    lista: list[Escenario] = []
    for indice in range(4):
        lista.append(
            _situacion(
                f"sed-{indice + 1}",
                sed=60.0 + 10.0 * indice,
                energia=80.0 - 10.0 * indice,
                agua=True,
                comida=True,
                esperada="beber",
            )
        )
    for indice in range(4):
        lista.append(
            _situacion(
                f"hambre-{indice + 1}",
                sed=5.0 + 5.0 * indice,
                energia=40.0 - 10.0 * indice,
                agua=True,
                comida=True,
                esperada="comer",
            )
        )
    for indice in range(4):
        lista.append(
            _situacion(
                f"agotado-{indice + 1}",
                sed=10.0,
                energia=9.0 - 2.0 * indice,
                vecino=True,
                esperada="descansar",
            )
        )
    for indice in range(4):
        lista.append(
            _situacion(
                f"amenaza-{indice + 1}",
                sed=20.0,
                energia=50.0 - 5.0 * indice,
                agua=True,
                comida=True,
                amenaza=True,
                esperada="huir",
            )
        )
    for indice in range(4):
        lista.append(
            _situacion(
                f"calma-{indice + 1}",
                sed=0.0,
                energia=100.0,
                vecino=True,
                esperada="hablar",
            )
        )
    return lista


def evaluar(
    cliente: ClienteLLM,
    casos: Sequence[Escenario] | None = None,
) -> dict[str, Any]:
    """Corre los escenarios y devuelve aciertos, correcciones y sin decisión."""
    lista = escenarios() if casos is None else list(casos)
    aciertos = 0
    corregidas = 0
    sin_decision = 0
    detalle: list[dict[str, Any]] = []

    for caso in lista:
        opciones = candidatas(caso.individuo, caso.mundo)
        estado = estado_para(caso.individuo, caso.mundo)
        eleccion = decidir_con_candidatas(cliente, estado, opciones)
        elegida = eleccion.decision.accion if eleccion.decision is not None else None
        acierto = elegida == caso.esperada
        aciertos += int(acierto)
        corregidas += int(eleccion.corregida)
        sin_decision += int(eleccion.decision is None)
        detalle.append(
            {
                "escenario": caso.nombre,
                "esperada": caso.esperada,
                "elegida": elegida,
                "acierto": acierto,
                "corregida": eleccion.corregida,
            }
        )

    total = len(lista)
    return {
        "escenarios": total,
        "aciertos": aciertos,
        "acierto": round(aciertos / total, 3) if total else 0.0,
        "corregidas": corregidas,
        "sin_decision": sin_decision,
        "detalle": detalle,
    }


def utilidad(accion: str, estado: Mapping[str, Any]) -> float:
    """Utilidad sencilla de cada acción para el backend simulado competente."""
    sed = float(estado.get("sed", 0.0))
    energia = float(estado.get("energia", 100.0))
    if accion == "huir":
        return 1000.0 if estado.get("amenaza") else -1000.0
    if estado.get("amenaza"):
        return -100.0
    if accion == "beber":
        return sed if estado.get("agua_al_alcance") else -100.0
    if accion == "comer":
        return max(0.0, 100.0 - energia) if estado.get("comida_al_alcance") else -100.0
    if accion == "descansar":
        return 100.0 - energia
    if accion == "hablar":
        return 50.0 if estado.get("vecino") else -100.0
    return 0.0


def backend_competente() -> Transporte:
    """Transporte simulado que elige la candidata de mayor utilidad.

    Es el backend de CI: prueba el contrato y el filtrado, no la calidad del
    modelo. Lee el estado del propio prompt, como haría el modelo real.
    """

    def transporte(
        metodo: str,
        _url: str,
        cuerpo: dict[str, Any] | None,
        _timeout: float,
    ) -> tuple[int, bytes]:
        if metodo != "POST" or cuerpo is None:
            return 200, b'{"models": []}'
        prompt = _ultimo_mensaje(cuerpo)
        estado = _estado_del_prompt(prompt)
        opciones = _candidatas_del_prompt(prompt)
        if not opciones:
            return 500, b'{"error": "sin candidatas"}'
        elegida = max(opciones, key=lambda nombre: utilidad(nombre, estado))
        contenido = {
            "accion": elegida,
            "objetivo": "",
            "razon": "simulado: la candidata de mayor utilidad",
            "dialogo": "",
        }
        sobre = {"message": {"role": "assistant", "content": json.dumps(contenido)}}
        return 200, json.dumps(sobre).encode("utf-8")

    return transporte


def _situacion(
    nombre: str,
    *,
    sed: float,
    energia: float,
    esperada: NombreAccion,
    agua: bool = False,
    comida: bool = False,
    amenaza: bool = False,
    vecino: bool = False,
) -> Escenario:
    """Fabrica un mundo mínimo con los hechos que pide el escenario."""
    tiles = [[TipoTile.HIERBA for _ in range(24)] for _ in range(24)]
    individuo = Individuo(
        id=1,
        sexo="m",
        genoma=Genoma(),
        necesidades=Necesidades(energia=energia, sed=sed, salud=100.0),
        x=10.0,
        y=10.0,
    )
    individuos = [individuo]
    if vecino:
        individuos.append(
            Individuo(
                id=2,
                sexo="f",
                genoma=Genoma(),
                necesidades=Necesidades(),
                x=10.0,
                y=11.0,
            )
        )
    recursos: list[Recurso] = []
    if agua:
        recursos.append(
            Recurso(
                id=1,
                tipo=TipoRecurso.AGUA,
                x=10,
                y=10,
                cantidad=40,
                capacidad=40,
                regeneracion=10,
                alcance=1.5,
            )
        )
    if comida:
        recursos.append(
            Recurso(
                id=2,
                tipo=TipoRecurso.BAYAS,
                x=10,
                y=10,
                cantidad=4,
                capacidad=4,
                regeneracion=300,
                alcance=1.5,
            )
        )
    mundo = Mundo(
        ancho=24,
        alto=24,
        tiles=tiles,
        recursos=recursos,
        individuos=individuos,
        azar=random.Random(0),
    )
    if amenaza:
        mundo.depredadores.append(Depredador(x=10.5, y=10.0))
    return Escenario(nombre=nombre, individuo=individuo, mundo=mundo, esperada=esperada)


def _ultimo_mensaje(cuerpo: Mapping[str, Any]) -> str:
    mensajes = cuerpo.get("messages")
    if not isinstance(mensajes, list):
        return ""
    for mensaje in reversed(mensajes):
        if isinstance(mensaje, Mapping) and mensaje.get("role") == "user":
            contenido = mensaje.get("content")
            if isinstance(contenido, str):
                return contenido
    return ""


def _estado_del_prompt(prompt: str) -> Mapping[str, Any]:
    for linea in prompt.splitlines():
        if linea.startswith("Estado: "):
            try:
                datos = json.loads(linea[len("Estado: ") :])
            except ValueError:
                return {}
            if isinstance(datos, Mapping):
                return datos
            return {}
    return {}


def _candidatas_del_prompt(prompt: str) -> tuple[str, ...]:
    for linea in prompt.splitlines():
        if linea.startswith("Acciones candidatas: "):
            return tuple(
                parte.strip()
                for parte in linea[len("Acciones candidatas: ") :].split(",")
                if parte.strip()
            )
    return ()
