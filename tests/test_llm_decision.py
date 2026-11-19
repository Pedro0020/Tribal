"""Decisión con candidatas: esquema restringido, few-shot, temp y corrección dura."""

from __future__ import annotations

import json
from typing import Any

from tribal.core.acciones import Accion
from tribal.llm.cliente import ClienteLLM, backend_falso
from tribal.llm.decision import TEMPERATURA, decidir_con_candidatas


def _transporte(contenido: object, visto: dict[str, Any] | None = None) -> Any:
    texto = contenido if isinstance(contenido, str) else json.dumps(contenido)

    def transporte(
        metodo: str,
        url: str,
        cuerpo: dict[str, Any] | None,
        timeout: float,
    ) -> tuple[int, bytes]:
        if visto is not None:
            visto.update(metodo=metodo, url=url, cuerpo=cuerpo, timeout=timeout)
        sobre = {"message": {"role": "assistant", "content": texto}}
        return 200, json.dumps(sobre).encode()

    return transporte


def _valida(accion: str) -> dict[str, str]:
    return {"accion": accion, "objetivo": "aquí", "razon": "porque sí", "dialogo": ""}


def test_el_payload_limita_el_enum_a_las_candidatas() -> None:
    visto: dict[str, Any] = {}
    cliente = ClienteLLM(transporte=_transporte(_valida("beber"), visto))
    candidatas = [Accion("beber"), Accion("descansar")]
    eleccion = decidir_con_candidatas(cliente, {"sed": 80}, candidatas)

    assert eleccion.decision is not None
    cuerpo = visto["cuerpo"]
    assert cuerpo["format"]["properties"]["accion"]["enum"] == ["beber", "descansar"]
    assert cuerpo["options"]["temperature"] == TEMPERATURA == 0.3


def test_el_payload_usa_los_ejemplos_del_cliente() -> None:
    visto: dict[str, Any] = {}
    ejemplo = {
        "estado": {"sed": 99},
        "candidatas": ("beber", "comer"),
        "accion": "beber",
        "objetivo": "la orilla",
        "razon": "ejemplo inyectado",
        "dialogo": "",
    }
    cliente = ClienteLLM(transporte=_transporte(_valida("beber"), visto), ejemplos=[ejemplo])
    decidir_con_candidatas(cliente, {"sed": 80}, ["beber", "descansar"])

    mensajes = visto["cuerpo"]["messages"]
    ejemplos = [mensaje for mensaje in mensajes if mensaje["role"] == "assistant"]
    assert len(ejemplos) == 1
    assert json.loads(ejemplos[0]["content"])["razon"] == "ejemplo inyectado"


def test_el_payload_lleva_few_shot_estado_accion() -> None:
    visto: dict[str, Any] = {}
    cliente = ClienteLLM(transporte=_transporte(_valida("beber"), visto))
    decidir_con_candidatas(cliente, {"sed": 80}, ["beber", "descansar"])

    mensajes = visto["cuerpo"]["messages"]
    ejemplos = [mensaje for mensaje in mensajes if mensaje["role"] == "assistant"]
    assert len(ejemplos) == 2
    for mensaje in ejemplos:
        ejemplo = json.loads(mensaje["content"])
        assert {"accion", "razon"} <= set(ejemplo)
    assert mensajes[-1]["role"] == "user"
    assert "beber, descansar" in mensajes[-1]["content"]


def test_una_eleccion_valida_no_se_corrige() -> None:
    cliente = ClienteLLM(transporte=_transporte(_valida("comer")))
    eleccion = decidir_con_candidatas(cliente, {}, ["beber", "comer"])
    assert eleccion.corregida is False
    assert eleccion.motivo is None
    assert eleccion.decision is not None
    assert eleccion.decision.accion == "comer"


def test_accion_fuera_de_candidatas_se_corrige_a_la_primera() -> None:
    cliente = ClienteLLM(transporte=_transporte(_valida("beber")))
    eleccion = decidir_con_candidatas(cliente, {}, ["comer", "descansar"])

    assert eleccion.corregida is True
    assert "fuera de candidatas" in (eleccion.motivo or "")
    assert eleccion.decision is not None
    assert eleccion.decision.accion == "comer"
    assert "corrección del motor" in eleccion.decision.razon


def test_huir_sin_amenaza_viola_una_restriccion_dura() -> None:
    cliente = ClienteLLM(transporte=_transporte(_valida("huir")))
    estado = {"amenaza": False, "agua_al_alcance": True}
    eleccion = decidir_con_candidatas(cliente, estado, ["huir", "beber"])

    assert eleccion.corregida is True
    assert eleccion.motivo == "huir sin amenaza"
    assert eleccion.decision is not None
    assert eleccion.decision.accion == "beber"


def test_respuesta_invalida_se_corrige() -> None:
    cliente = ClienteLLM(transporte=_transporte("{no es json"))
    eleccion = decidir_con_candidatas(cliente, {}, ["beber", "descansar"])

    assert eleccion.corregida is True
    assert eleccion.decision is not None
    assert eleccion.decision.accion == "beber"


def test_transporte_caido_no_es_una_eleccion_que_corregir() -> None:
    cliente = ClienteLLM(transporte=backend_falso([TimeoutError("timeout")]))
    eleccion = decidir_con_candidatas(cliente, {}, ["beber", "descansar"])

    assert eleccion.decision is None
    assert eleccion.corregida is False
    assert eleccion.motivo is not None
