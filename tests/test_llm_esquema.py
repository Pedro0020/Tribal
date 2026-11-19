"""Esquema de la respuesta LLM: vocabulario, validación y prompt few-shot."""

from __future__ import annotations

import json
from typing import get_args

import pytest

from tribal.core.acciones import NombreAccion
from tribal.llm.esquema import (
    ACCIONES,
    CAMPOS_TEXTO,
    ESQUEMA_RESPUESTA,
    Decision,
    ErrorValidacion,
    construir_prompt,
    validar,
)

VALIDO = {
    "accion": "beber",
    "objetivo": "la orilla",
    "razon": "la sed aprieta",
    "dialogo": "",
}


def test_acciones_salen_del_vocabulario_real() -> None:
    assert get_args(NombreAccion) == ACCIONES
    assert "beber" in ACCIONES
    assert "frotar_madera" in ACCIONES


def test_esquema_fija_la_accion_y_los_campos_obligatorios() -> None:
    propiedades = ESQUEMA_RESPUESTA["properties"]
    assert propiedades["accion"]["enum"] == list(ACCIONES)
    assert propiedades["accion"]["type"] == "string"
    for campo in CAMPOS_TEXTO:
        assert propiedades[campo] == {"type": "string"}
    assert set(ESQUEMA_RESPUESTA["required"]) == {"accion", *CAMPOS_TEXTO}
    assert ESQUEMA_RESPUESTA["additionalProperties"] is False


def test_validar_acepta_una_decision_completa() -> None:
    decision = validar(dict(VALIDO))
    assert isinstance(decision, Decision)
    assert decision.accion == "beber"
    assert decision.objetivo == "la orilla"
    assert decision.razon == "la sed aprieta"
    assert decision.dialogo == ""


def test_validar_rechaza_accion_fuera_del_vocabulario() -> None:
    error = validar({**VALIDO, "accion": "volar"})
    assert isinstance(error, ErrorValidacion)
    assert "volar" in error.motivo


@pytest.mark.parametrize("campo", CAMPOS_TEXTO)
def test_validar_rechaza_un_campo_de_texto_que_falta(campo: str) -> None:
    datos = dict(VALIDO)
    datos.pop(campo)
    error = validar(datos)
    assert isinstance(error, ErrorValidacion)
    assert campo in error.motivo


@pytest.mark.parametrize("campo", CAMPOS_TEXTO)
def test_validar_rechaza_tipos_que_no_son_texto(campo: str) -> None:
    error = validar({**VALIDO, campo: 42})
    assert isinstance(error, ErrorValidacion)
    assert campo in error.motivo


def test_validar_rechaza_algo_que_no_es_un_objeto() -> None:
    error = validar(["beber"])
    assert isinstance(error, ErrorValidacion)


def test_construir_prompt_incluye_candidatas_ejemplo_y_estado() -> None:
    ejemplo = {
        "estado": {"sed": 90},
        "candidatas": ("beber", "descansar"),
        "accion": "beber",
        "objetivo": "la orilla",
        "razon": "sed alta",
        "dialogo": "",
    }
    mensajes = construir_prompt({"energia": 20}, ["comer", "tallar"], [ejemplo])
    assert mensajes[0]["role"] == "system"
    assert "exactamente una" in mensajes[0]["content"]
    assert "beber, descansar" in mensajes[1]["content"]
    assert json.loads(mensajes[2]["content"])["accion"] == "beber"
    assert "comer, tallar" in mensajes[-1]["content"]
    assert "energia" in mensajes[-1]["content"]


def test_construir_prompt_trae_few_shot_por_defecto() -> None:
    mensajes = construir_prompt("sed alta", ["beber", "comer"])
    assert any(mensaje["role"] == "assistant" for mensaje in mensajes)
    assert mensajes[-1]["role"] == "user"
