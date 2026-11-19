"""Cliente LLM: transporte inyectable, degradación sin excepciones y selfcheck."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from tribal.cli import main
from tribal.llm.cliente import (
    ClienteLLM,
    Servicio,
    backend_falso,
)
from tribal.llm.esquema import ESQUEMA_RESPUESTA, Decision

CANDIDATAS = ("beber", "comer", "descansar")


class _Respuesta:
    """Respuesta mínima de `urlopen` para el transporte real sin abrir socket."""

    status = 200

    def __enter__(self) -> _Respuesta:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def read(self) -> bytes:
        return b'{"models": []}'


def _urlopen_ok(*_args: Any, **_kwargs: Any) -> _Respuesta:
    return _Respuesta()


def _urlopen_caido(*_args: Any, **_kwargs: Any) -> Any:
    raise urllib.error.URLError("connection refused")


def _ollama(contenido: object) -> dict[str, Any]:
    texto = contenido if isinstance(contenido, str) else json.dumps(contenido)
    return {"message": {"role": "assistant", "content": texto}}


def _valida() -> dict[str, Any]:
    return {
        "accion": "beber",
        "objetivo": "la orilla",
        "razon": "la sed aprieta",
        "dialogo": "",
    }


def test_la_suite_no_abre_red() -> None:
    # `tests/conftest.py` parchea urlopen para toda la suite.
    with pytest.raises(AssertionError, match="no debe abrir red"):
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags")


def test_disponible_consulta_api_tags() -> None:
    visto: dict[str, Any] = {}

    def transporte(
        metodo: str, url: str, _cuerpo: dict[str, Any] | None, _timeout: float
    ) -> tuple[int, bytes]:
        visto.update(metodo=metodo, url=url)
        return 200, b'{"models": []}'

    cliente = ClienteLLM(endpoint="http://127.0.0.1:11434/", transporte=transporte)
    servicio = cliente.disponible()
    assert isinstance(servicio, Servicio)
    assert servicio.disponible is True
    assert servicio.error is None
    assert visto == {"metodo": "GET", "url": "http://127.0.0.1:11434/api/tags"}


def test_disponible_true_con_el_transporte_real(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_ok)
    servicio = ClienteLLM().disponible()
    assert servicio.disponible is True
    assert servicio.latencia_ms is not None


def test_disponible_false_si_el_servicio_esta_caido(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_caido)
    servicio = ClienteLLM().disponible()
    assert servicio.disponible is False
    assert servicio.error is not None
    assert "connection refused" in servicio.error


def test_disponible_false_con_http_no_200() -> None:
    servicio = ClienteLLM(transporte=backend_falso([(503, "no")])).disponible()
    assert servicio.disponible is False
    assert servicio.latencia_ms is not None
    assert servicio.error == "http 503"


def test_decidir_manda_modelo_formato_y_timeout() -> None:
    visto: dict[str, Any] = {}

    def transporte(
        metodo: str, url: str, cuerpo: dict[str, Any] | None, timeout: float
    ) -> tuple[int, bytes]:
        visto.update(metodo=metodo, url=url, cuerpo=cuerpo, timeout=timeout)
        return 200, json.dumps(_ollama(_valida())).encode()

    resultado = ClienteLLM(timeout=2.5, transporte=transporte).decidir({"sed": 80}, CANDIDATAS)
    assert resultado.estado == "ok"
    assert visto["metodo"] == "POST"
    assert visto["url"] == "http://127.0.0.1:11434/api/chat"
    assert visto["timeout"] == 2.5
    assert visto["cuerpo"]["model"] == "tribal-llm"
    assert visto["cuerpo"]["format"] == ESQUEMA_RESPUESTA


def test_decidir_ok_devuelve_la_decision() -> None:
    transporte = backend_falso([_ollama(_valida())])
    resultado = ClienteLLM(transporte=transporte).decidir({"sed": 80}, CANDIDATAS)
    assert resultado.estado == "ok"
    assert isinstance(resultado.decision, Decision)
    assert resultado.decision.accion == "beber"


def test_decidir_json_roto_es_error_sin_excepcion() -> None:
    transporte = backend_falso([_ollama("{no es json")])
    resultado = ClienteLLM(transporte=transporte).decidir({}, CANDIDATAS)
    assert resultado.estado == "error"
    assert resultado.decision is None
    assert resultado.motivo == "el contenido no es JSON"


def test_decidir_cuerpo_http_no_json_es_error_sin_excepcion() -> None:
    resultado = ClienteLLM(transporte=backend_falso([(200, "no json")])).decidir({}, CANDIDATAS)
    assert resultado.estado == "error"
    assert resultado.motivo == "la respuesta HTTP no es JSON"


def test_decidir_accion_fuera_del_vocabulario_es_error() -> None:
    datos = {**_valida(), "accion": "volar"}
    resultado = ClienteLLM(transporte=backend_falso([_ollama(datos)])).decidir({}, CANDIDATAS)
    assert resultado.estado == "error"
    assert "volar" in (resultado.motivo or "")


def test_decidir_accion_fuera_de_candidatas_es_error() -> None:
    transporte = backend_falso([_ollama(_valida())])
    resultado = ClienteLLM(transporte=transporte).decidir({}, ("comer", "descansar"))
    assert resultado.estado == "error"
    assert "beber" in (resultado.motivo or "")


@pytest.mark.parametrize(
    "fallo",
    [TimeoutError("timeout"), urllib.error.URLError("connection refused")],
)
def test_decidir_fallo_de_transporte_degrada_sin_excepcion(fallo: Exception) -> None:
    resultado = ClienteLLM(transporte=backend_falso([fallo])).decidir({}, CANDIDATAS)
    assert resultado.estado == "degradado"
    assert resultado.decision is None


def test_decidir_http_no_200_degrada() -> None:
    resultado = ClienteLLM(transporte=backend_falso([(500, "boom")])).decidir({}, CANDIDATAS)
    assert resultado.estado == "degradado"
    assert resultado.motivo == "http 500"


def test_decidir_sin_candidatas_es_error_y_no_llama_al_transporte() -> None:
    resultado = ClienteLLM(transporte=backend_falso([])).decidir({}, [])
    assert resultado.estado == "error"
    assert resultado.motivo == "sin acciones candidatas"


def test_backend_falso_es_determinista_y_secuencial() -> None:
    transporte = backend_falso([_ollama(_valida()), (500, "boom")])
    cliente = ClienteLLM(transporte=transporte)
    assert cliente.decidir({}, CANDIDATAS).estado == "ok"
    assert cliente.decidir({}, CANDIDATAS).estado == "degradado"


def test_selfcheck_json_sin_servicio_sale_cero(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_caido)
    assert main(["llm", "selfcheck", "--json"]) == 0
    informe = json.loads(capsys.readouterr().out)
    assert informe["disponible"] is False
    assert informe["endpoint"] == "http://127.0.0.1:11434"
    assert informe["modelo"] == "tribal-llm"
    assert informe["latencia_ms"] is None
    assert "connection refused" in informe["error"]


def test_selfcheck_json_con_servicio(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_ok)
    assert main(["llm", "selfcheck", "--json"]) == 0
    informe = json.loads(capsys.readouterr().out)
    assert informe["disponible"] is True
    assert informe["error"] is None
    assert informe["latencia_ms"] is not None
