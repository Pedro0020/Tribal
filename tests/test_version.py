"""La versión tiene una sola fuente: los metadatos del paquete instalado."""

from __future__ import annotations

import tomllib
from importlib.metadata import version
from pathlib import Path

import tribal

RAIZ = Path(__file__).resolve().parents[1]


def test_version_coincide_con_pyproject_y_metadatos() -> None:
    pyproject = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    declarada = pyproject["project"]["version"]

    assert version("tribal") == declarada, "el paquete instalado no refleja pyproject: uv lock/sync"
    assert tribal.__version__ == declarada
    assert tribal.__version__ == version("tribal")
