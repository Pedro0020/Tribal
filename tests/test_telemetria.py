"""`report telemetry`: una muestra por intervalo, determinista y cuadrada con el resumen."""

from __future__ import annotations

import json
from typing import Any, cast

import pytest

from tribal.cli import main
from tribal.sim import run

TICKS = 600
INTERVALO = 60
SEMILLA = 3
CAMPOS = {
    "tick",
    "poblacion",
    "divergentes",
    "conformistas",
    "neutros",
    "nodos",
    "aristas",
    "media_energia",
    "media_sed",
}


def _informe(capsys: pytest.CaptureFixture[str], *extra: str) -> dict[str, Any]:
    assert main(["report", "telemetry", "--json", *extra]) == 0
    return cast(dict[str, Any], json.loads(capsys.readouterr().out))


def test_json_da_una_muestra_por_intervalo_y_no_una_por_tick(
    capsys: pytest.CaptureFixture[str],
) -> None:
    informe = _informe(
        capsys,
        "--seed",
        str(SEMILLA),
        "--ticks",
        str(TICKS),
        "--intervalo",
        str(INTERVALO),
    )

    assert informe["seed"] == SEMILLA
    assert informe["ticks"] == TICKS
    assert informe["intervalo"] == INTERVALO
    assert informe["crisis"] is False
    assert len(informe["muestras"]) == TICKS // INTERVALO == 10
    assert len(informe["muestras"]) != informe["ticks"]
    assert [muestra["tick"] for muestra in informe["muestras"]] == [
        60,
        120,
        180,
        240,
        300,
        360,
        420,
        480,
        540,
        600,
    ]
    assert all(set(muestra) == CAMPOS for muestra in informe["muestras"])


def test_primera_y_ultima_muestra_cuadran_con_el_resumen(
    capsys: pytest.CaptureFixture[str],
) -> None:
    informe = _informe(capsys, "--seed", str(SEMILLA), "--ticks", str(TICKS))
    primera, ultima = informe["muestras"][0], informe["muestras"][-1]
    corto = run(INTERVALO, SEMILLA, headless=True).resumen()
    completo = run(TICKS, SEMILLA, headless=True).resumen()

    assert primera["tick"] == INTERVALO
    assert primera["poblacion"] == corto["poblacion_final"]
    assert primera["divergentes"] == corto["n_divergentes"]
    assert primera["conformistas"] == corto["n_conformistas"]
    assert primera["neutros"] == corto["n_neutros"]
    assert primera["nodos"] == len(corto["nodos"])
    assert primera["aristas"] == len(corto["aristas"])
    assert primera["media_energia"] == corto["media_energia"]
    assert primera["media_sed"] == corto["media_sed"]

    assert ultima["tick"] == TICKS
    assert ultima["poblacion"] == completo["poblacion_final"]
    assert ultima["divergentes"] == completo["n_divergentes"]
    assert ultima["conformistas"] == completo["n_conformistas"]
    assert ultima["neutros"] == completo["n_neutros"]
    assert ultima["nodos"] == len(completo["nodos"])
    assert ultima["aristas"] == len(completo["aristas"])
    assert ultima["media_energia"] == completo["media_energia"]
    assert ultima["media_sed"] == completo["media_sed"]


def test_sin_json_imprime_una_tabla_legible(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["report", "telemetry", "--ticks", "120", "--intervalo", "60"]) == 0
    lineas = capsys.readouterr().out.strip().splitlines()

    assert "intervalo 60" in lineas[0]
    assert "tick" in lineas[1] and "pob" in lineas[1] and "aristas" in lineas[1]
    assert len(lineas) == 2 + 2  # cabecera + dos muestras


def test_dos_corridas_dan_las_mismas_muestras(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["report", "telemetry", "--json", "--ticks", "600"]) == 0
    primera = capsys.readouterr().out
    assert main(["report", "telemetry", "--json", "--ticks", "600"]) == 0
    segunda = capsys.readouterr().out

    assert primera == segunda
