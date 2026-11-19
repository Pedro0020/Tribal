"""HARD-1: diez semillas reproducen su resumen exacto, también entre subprocesos."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from tribal.sim import run

SEMILLAS = tuple(range(1, 11))
TICKS = 600


def _comando(seed: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "tribal",
        "run",
        "--headless",
        "--json",
        "--ticks",
        str(TICKS),
        "--seed",
        str(seed),
    ]


@pytest.mark.parametrize("seed", SEMILLAS)
def test_cada_semilla_reproduce_su_resumen_exacto(seed: int) -> None:
    primera = subprocess.run(_comando(seed), capture_output=True, check=True)
    segunda = subprocess.run(_comando(seed), capture_output=True, check=True)

    # Byte a byte: dos procesos no pueden diferir en un espacio ni en un orden.
    assert primera.stdout == segunda.stdout

    serializado = json.dumps(run(TICKS, seed, headless=True).resumen(), ensure_ascii=True)
    assert primera.stdout.decode("utf-8").splitlines() == [serializado]
    assert json.loads(primera.stdout) == json.loads(serializado)
