"""Importar el paquete tribal no ejecuta la CLI ni mata el proceso (FIX-001)."""

from __future__ import annotations

import pkgutil

import tribal
import tribal.__main__  # noqa: F401 — regresión: importar no debe ejecutar la CLI


def test_walk_packages_sobre_tribal_no_mata_el_proceso() -> None:
    modulos = [m.name for m in pkgutil.walk_packages(tribal.__path__, prefix="tribal.")]
    assert "tribal.__main__" in modulos
    assert "tribal.cli" in modulos
