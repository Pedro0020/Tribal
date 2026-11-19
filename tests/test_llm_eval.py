"""`llm eval`: el contrato supera el 70 % con backend competente y no abre red."""

from __future__ import annotations

import json
import urllib.error

import pytest

from tribal.cli import main
from tribal.llm.candidatas import candidatas
from tribal.llm.cliente import ClienteLLM
from tribal.llm.eval import backend_competente, escenarios, evaluar


def test_el_contrato_supera_el_setenta_por_ciento() -> None:
    informe = evaluar(ClienteLLM(transporte=backend_competente()))
    assert informe["escenarios"] == 20
    assert informe["acierto"] > 0.70
    assert informe["aciertos"] == informe["escenarios"]


def test_cada_escenario_ofrece_entre_dos_y_cuatro_candidatas() -> None:
    for caso in escenarios():
        opciones = candidatas(caso.individuo, caso.mundo)
        assert 2 <= len(opciones) <= 4, caso.nombre


def test_llm_eval_json_con_backend_simulado(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["llm", "eval", "--json"]) == 0
    informe = json.loads(capsys.readouterr().out)
    assert informe["backend"] == "simulado"
    assert informe["acierto"] > 0.70
    assert informe["corregidas"] == 0


def test_llm_eval_avisa_si_se_piden_mas_escenarios_que_la_bateria(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["llm", "eval", "--escenarios", "50", "--json"]) == 0
    salida = capsys.readouterr()
    assert "la batería tiene 20 escenarios" in salida.err
    assert json.loads(salida.out)["escenarios"] == 20


def test_llm_eval_http_sin_servicio_no_revienta(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def caido(*_args: object, **_kwargs: object) -> object:
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", caido)
    codigo = main(
        ["llm", "eval", "--backend", "http", "--escenarios", "2", "--timeout", "0.05", "--json"]
    )

    assert codigo == 0
    informe = json.loads(capsys.readouterr().out)
    assert informe["backend"] == "http"
    assert informe["sin_decision"] == 2
    assert informe["acierto"] == 0.0
