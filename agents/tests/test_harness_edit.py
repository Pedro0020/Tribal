"""
test_harness_edit.py — Tests de `harness edit`.

Corregir el backlog sin abrirlo a mano es justo lo que `edit` existe para
evitar: un criterio mal escrito o una dependencia que ya no aplica atasca el
ciclo, y arreglarlo editando JSON desde un prompt es cómo se corrompe. Lo que
se prueba aquí es que la corrección se aplica, que se rechaza todo lo que
dejaría el grafo inconsistente, y que el cambio queda a la vista en `data`.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from agents.agents.harness_agent import HarnessAgent

BACKLOG = {
    "version": 1,
    "project": "Test",
    "features": [
        {
            "id": "A-001",
            "title": "Primera",
            "description": "d1",
            "acceptance_criteria": ["c1", "c2"],
            "status": "pending",
            "depends_on": [],
        },
        {
            "id": "B-001",
            "title": "Segunda",
            "description": "d2",
            "acceptance_criteria": ["c1"],
            "status": "pending",
            "depends_on": ["A-001"],
        },
        {
            "id": "C-001",
            "title": "Tercera",
            "description": "d3",
            "acceptance_criteria": ["c1"],
            "status": "pending",
            "depends_on": [],
        },
    ],
}


@pytest.fixture
def harness(context) -> HarnessAgent:
    (context.root / "harness").mkdir(exist_ok=True)
    (context.root / "harness" / "featureslist.json").write_text(
        json.dumps(BACKLOG, indent=2), encoding="utf-8"
    )
    (context.root / "harness" / "progress").mkdir(exist_ok=True)
    return HarnessAgent(context=context)


def _doc(harness: HarnessAgent) -> dict:
    path = harness.ctx.root / "harness" / "featureslist.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _feature(harness: HarnessAgent, feature_id: str) -> dict:
    return next(f for f in _doc(harness)["features"] if f["id"] == feature_id)


def _huellas(doc: dict) -> dict[str, str]:
    return {
        f["id"]: hashlib.md5(json.dumps(f, sort_keys=True).encode("utf-8")).hexdigest()
        for f in doc["features"]
    }


# -- lo que corrige -----------------------------------------------------------
def test_edit_corrige_el_titulo(harness):
    result = harness.edit(id="A-001", title="Primera corregida")
    assert result.success
    assert _feature(harness, "A-001")["title"] == "Primera corregida"
    assert result.data["changes"]["title"] == {
        "before": "Primera",
        "after": "Primera corregida",
    }


def test_edit_corrige_la_descripcion(harness):
    result = harness.edit(id="A-001", description="nueva descripción")
    assert result.success
    assert _feature(harness, "A-001")["description"] == "nueva descripción"


def test_edit_corrige_los_criterios(harness):
    result = harness.edit(id="A-001", criteria="uno; dos ;")
    assert result.success
    assert _feature(harness, "A-001")["acceptance_criteria"] == ["uno", "dos"]
    assert result.data["changes"]["acceptance_criteria"] == {
        "before": ["c1", "c2"],
        "after": ["uno", "dos"],
    }


def test_edit_corrige_las_dependencias(harness):
    result = harness.edit(id="B-001", depends_on="C-001; A-001")
    assert result.success
    assert _feature(harness, "B-001")["depends_on"] == ["C-001", "A-001"]


def test_edit_con_depends_on_vacio_las_limpia(harness):
    result = harness.edit(id="B-001", depends_on="")
    assert result.success
    assert _feature(harness, "B-001")["depends_on"] == []
    assert result.data["changes"]["depends_on"] == {"before": ["A-001"], "after": []}


def test_edit_no_toca_el_resto_del_backlog(harness):
    antes = _huellas(_doc(harness))
    harness.edit(id="A-001", title="otro", criteria="x")
    despues = _huellas(_doc(harness))

    assert despues["B-001"] == antes["B-001"]
    assert despues["C-001"] == antes["C-001"]
    assert _feature(harness, "A-001")["status"] == "pending"
    assert _feature(harness, "A-001")["depends_on"] == []


def test_edit_sin_cambios_reales_no_toca_el_fichero(harness):
    ruta: Path = harness.ctx.root / "harness" / "featureslist.json"
    antes = ruta.read_bytes()
    result = harness.edit(id="A-001", title="Primera")
    assert result.success
    assert result.data["changes"] == {}
    assert ruta.read_bytes() == antes


# -- lo que rechaza -----------------------------------------------------------
def test_edit_rechaza_id_inexistente(harness):
    result = harness.edit(id="NO-EXISTE", title="x")
    assert not result.success
    assert "NO-EXISTE" in result.message


@pytest.mark.parametrize("status", ["in_progress", "done", "blocked"])
def test_edit_solo_admite_features_pending(harness, status):
    doc = _doc(harness)
    doc["features"][0]["status"] = status
    (harness.ctx.root / "harness" / "featureslist.json").write_text(
        json.dumps(doc, indent=2), encoding="utf-8"
    )

    result = harness.edit(id="A-001", title="x")

    assert not result.success
    assert status in result.message
    assert _feature(harness, "A-001")["title"] == "Primera"


def test_edit_rechaza_dependencia_inexistente(harness):
    antes = _huellas(_doc(harness))
    result = harness.edit(id="C-001", depends_on="NO-EXISTE")
    assert not result.success
    assert "no existen" in result.message
    assert _huellas(_doc(harness)) == antes


def test_edit_rechaza_un_ciclo(harness):
    # B-001 ya depende de A-001: hacer que A-001 dependa de B-001 cierra el bucle.
    antes = _huellas(_doc(harness))
    result = harness.edit(id="A-001", depends_on="B-001")
    assert not result.success
    assert "ciclo" in result.message
    assert _huellas(_doc(harness)) == antes


def test_edit_rechaza_autodependencia(harness):
    result = harness.edit(id="C-001", depends_on="C-001")
    assert not result.success
    assert "ciclo" in result.message


@pytest.mark.parametrize("campo,valor", [("status", "done"), ("blocked_reason", "porque sí")])
def test_edit_no_permite_status_ni_blocked_reason(harness, campo, valor):
    antes = _huellas(_doc(harness))
    result = harness.edit(id="A-001", **{campo: valor})
    assert not result.success
    assert campo in result.message
    assert _huellas(_doc(harness)) == antes
    assert _feature(harness, "A-001")["status"] == "pending"


def test_edit_sin_id_pide_el_id(harness):
    result = harness.edit(title="x")
    assert not result.success
    assert result.needs


def test_edit_sin_campos_pide_que_editar(harness):
    result = harness.edit(id="A-001")
    assert not result.success
    assert result.needs


# -- flags sin valor: el CLI entrega `True`, no texto -------------------------
# En PowerShell `--flag ""` llega como flag sin valor (`True`): el shell se
# come el argumento vacío. Escribir `"title": true` en el backlog es peor que
# fallar, y un AttributeError es peor que las dos cosas. Por eso se prueba a
# través de `run()`, que es el camino que usa la CLI.


def _bytes(harness: HarnessAgent) -> bytes:
    return (harness.ctx.root / "harness" / "featureslist.json").read_bytes()


@pytest.mark.parametrize("campo", ["title", "description", "criteria"])
def test_run_rechaza_flags_sin_valor_sin_corromper_el_backlog(harness, campo):
    antes = _bytes(harness)
    result = harness.run("edit", id="A-001", **{campo: True})

    assert not result.success
    assert campo in result.message
    assert result.needs
    assert _bytes(harness) == antes, "un rechazo no puede reescribir el backlog"
    assert isinstance(_feature(harness, "A-001")["title"], str)


def test_run_depends_on_sin_valor_limpia(harness):
    # La semántica elegida: `--depends_on ""` llega como True en PowerShell y
    # se interpreta como «limpiar». Es documentado y tiene test.
    result = harness.run("edit", id="B-001", depends_on=True)

    assert result.success
    assert _feature(harness, "B-001")["depends_on"] == []
    assert result.data["changes"]["depends_on"] == {"before": ["A-001"], "after": []}


@pytest.mark.parametrize("campo", ["title", "description", "criteria", "depends_on"])
def test_run_rechaza_valores_no_textuales(harness, campo):
    antes = _bytes(harness)
    result = harness.run("edit", id="A-001", **{campo: 3})
    assert not result.success
    assert "no textual" in result.message
    assert _bytes(harness) == antes


def test_run_rechaza_criterios_que_quedan_vacios(harness):
    antes = _bytes(harness)
    result = harness.run("edit", id="A-001", criteria=";")
    assert not result.success
    assert "vacíos" in result.message
    assert _bytes(harness) == antes
    assert _feature(harness, "A-001")["acceptance_criteria"] == ["c1", "c2"]
