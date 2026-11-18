"""El CLI no puede morir por la consola de Windows (cp1252)."""

from __future__ import annotations

import io
import sys

from agents import cli


def test_describe_no_revienta_con_stdout_cp1252(monkeypatch):
    buffer = io.BytesIO()
    salida = io.TextIOWrapper(buffer, encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", salida)

    exit_code = cli.main(["describe", "cicd"])

    assert exit_code == 0
    salida.flush()
    texto = buffer.getvalue().decode("utf-8")
    assert '"cicd"' in texto
    # La flecha que tumbaba la consola: cp1252 no la puede representar.
    assert "→" in texto
