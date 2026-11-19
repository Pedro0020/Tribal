"""Guarda de red de la suite: ningún test debe abrir una conexión."""

from __future__ import annotations

import urllib.request
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def sin_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bloquea `urllib.request.urlopen` en todos los tests.

    El cliente LLM habla HTTP real solo cuando lo ejecuta el producto; la suite
    le inyecta `backend_falso`. Si un test se salta la inyección, falla aquí en
    vez de depender de que la máquina tenga o no red.
    """

    def prohibido(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("la suite no debe abrir red: inyecta un transporte falso")

    monkeypatch.setattr(urllib.request, "urlopen", prohibido)
