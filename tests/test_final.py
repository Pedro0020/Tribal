"""HARD-3: una partida completa se reproduce byte a byte entre procesos.

Misma semilla, backend falso y modo síncrono: el resumen de `run` y el KPI de
`report kpi --json` son idénticos en dos procesos, con la partida escrita en
SQLite. Es la comprobación de cierre del proyecto: lo que se publica en el README
se puede volver a ejecutar y da los mismos hitos, el mismo porcentaje y el mismo
veredicto.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SEMILLAS = tuple(range(1, 11))
#: Suficiente para que nazcan hitos y tradiciones, y corto para la suite.
TICKS = 1200


def _tribal(*argumentos: str) -> str:
    resultado = subprocess.run(
        [sys.executable, "-m", "tribal", *argumentos],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    )
    return resultado.stdout


@pytest.mark.parametrize("seed", SEMILLAS)
def test_la_partida_completa_se_reproduce_entre_procesos(seed: int, tmp_path: Path) -> None:
    db = tmp_path / f"tribu-{seed}.db"
    partida = [
        "run",
        "--headless",
        "--json",
        "--llm",
        "stub",
        "--llm-sincrono",
        "--ticks",
        str(TICKS),
        "--seed",
        str(seed),
        "--db",
        str(db),
    ]

    primera = _tribal(*partida, "--fresh")
    kpi_primera = _tribal("report", "kpi", "--db", str(db), "--json")

    segunda = _tribal(*partida, "--fresh")
    kpi_segunda = _tribal("report", "kpi", "--db", str(db), "--json")

    assert primera == segunda
    assert kpi_primera == kpi_segunda

    resumen = json.loads(primera)
    assert resumen["seed"] == seed
    assert resumen["ticks"] == TICKS
    assert resumen["llm"]["peticiones"] > 0
    assert resumen["llm"]["en_vuelo"] == 0

    kpi = json.loads(kpi_primera)
    assert set(kpi["hitos"]) == {"fuego", "herramienta_compuesta", "proto_lenguaje", "mito"}
    assert kpi["activos"] > 0
    # Ancla del KPI: forzar origen="arbol" al guardar baja el pct a 0 y este
    # assert cae (mutación verificada); sin él, una base corrupta pasaría.
    assert kpi["pct_fuera_arbol"] > 0.0
    assert kpi["umbral"] == 50.0
    assert kpi["veredicto"] == (
        all(kpi["hitos"].values()) and kpi["pct_fuera_arbol"] >= kpi["umbral"]
    )
