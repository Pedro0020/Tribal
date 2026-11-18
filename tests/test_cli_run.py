"""Subcomando `run`: JSON headless, validación de población y presupuesto de tick."""

from __future__ import annotations

import json
import re

import pytest

from tribal.cli import main

CLAVES = {
    "seed",
    "ticks",
    "poblacion_inicial",
    "poblacion_final",
    "nacimientos",
    "muertes",
    "media_energia",
    "media_sed",
    "media_genes",
    "habilidades_distintas",
    "habilidades",
    "individuos_movidos",
    "depredador",
    "agrupamiento_max",
    "huidas",
    "n_divergentes",
    "n_conformistas",
    "n_neutros",
    "intentos_divergentes",
    "combinaciones_logradas",
    "imitaciones",
    "nodos",
    "aristas",
    "pct_fuera_arbol",
    "nodos_por_origen",
    "config",
}


def test_run_headless_json_imprime_un_objeto(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "--headless", "--json", "--ticks", "120"]) == 0
    salida = capsys.readouterr().out
    datos = json.loads(salida)
    assert set(datos) == CLAVES
    assert datos["ticks"] == 120
    assert datos["poblacion_inicial"] == 12
    assert datos["nacimientos"] == 0
    assert datos["config"]["seed"] == 42


def test_dos_ejecuciones_json_dan_la_misma_salida(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "--headless", "--json", "--ticks", "300"]) == 0
    primera = capsys.readouterr().out
    assert main(["run", "--headless", "--json", "--ticks", "300"]) == 0
    segunda = capsys.readouterr().out
    assert primera == segunda


def test_run_headless_sin_json_imprime_resumen_legible(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["run", "--headless", "--ticks", "60"]) == 0
    salida = capsys.readouterr().out
    assert "seed" in salida
    assert "poblacion" in salida


def test_poblacion_fuera_de_rango_falla_con_mensaje(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["run", "--headless", "--ticks", "10", "--individuos", "5"]) != 0
    assert "--individuos" in capsys.readouterr().err


def test_benchmark_cabe_en_el_presupuesto_de_frame(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["run", "--benchmark", "--headless", "--json", "--ticks", "600"]) == 0
    capturado = capsys.readouterr()
    assert "ms_tick_medio" not in capturado.out
    assert json.loads(capturado.out)["ticks"] == 600
    veredicto = re.search(r"benchmark: ([0-9.]+) ms/tick, cabe en 16.67 ms", capturado.err)
    assert veredicto is not None
    assert float(veredicto.group(1)) < 16.67
