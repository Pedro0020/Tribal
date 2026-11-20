"""
test_harness_discard.py — Tests de `harness discard`, `revive` y `remove`.

`blocked` mezcla «todavía no se puede» con «ya no se quiere». `discard`
separa el segundo caso conservando el motivo en el backlog y en `history.md`;
`remove` solo borra lo que se creó por error. Lo que se prueba aquí es que el
rastro no se pierde y que `remove` no puede romper el grafo de dependencias.
"""

from __future__ import annotations

import json

import pytest

from agents.agents.harness_agent import VALID_STATUS, HarnessAgent
from agents.core.base_agent import AgentResult
from agents.evals.runner import HARNESS_STATUS, _problemas_backlog

BACKLOG = {
    "version": 1,
    "project": "Test",
    "features": [
        {
            "id": "A-001",
            "title": "Primera",
            "description": "d",
            "acceptance_criteria": ["c1"],
            "status": "pending",
            "depends_on": [],
        },
        {
            "id": "B-001",
            "title": "Segunda",
            "description": "d",
            "acceptance_criteria": ["c1"],
            "status": "pending",
            "depends_on": ["A-001"],
        },
        {
            "id": "C-001",
            "title": "Tercera",
            "description": "d",
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
    (context.root / "harness" / "progress" / "history.md").write_text(
        "# Historial\n", encoding="utf-8"
    )
    return HarnessAgent(context=context)


def _doc(harness: HarnessAgent) -> dict:
    return json.loads(
        (harness.ctx.root / "harness" / "featureslist.json").read_text(encoding="utf-8")
    )


def _feature(harness: HarnessAgent, feature_id: str) -> dict:
    return next(f for f in _doc(harness)["features"] if f["id"] == feature_id)


def _set_status(harness: HarnessAgent, feature_id: str, status: str) -> None:
    doc = _doc(harness)
    next(f for f in doc["features"] if f["id"] == feature_id)["status"] = status
    (harness.ctx.root / "harness" / "featureslist.json").write_text(
        json.dumps(doc, indent=2), encoding="utf-8"
    )


def _bytes(harness: HarnessAgent) -> bytes:
    return (harness.ctx.root / "harness" / "featureslist.json").read_bytes()


def _history(harness: HarnessAgent) -> str:
    return (harness.ctx.root / "harness" / "progress" / "history.md").read_text(encoding="utf-8")


# -- estados válidos ---------------------------------------------------------
def test_discarded_es_valido_en_el_agente_y_en_el_runner():
    assert "discarded" in VALID_STATUS
    assert "discarded" in HARNESS_STATUS

    descartada = {
        "id": "X-001",
        "title": "X",
        "description": "d",
        "acceptance_criteria": ["c"],
        "status": "discarded",
        "depends_on": [],
    }
    assert _problemas_backlog([descartada]) == []


# -- discard -----------------------------------------------------------------
def test_discard_deja_estado_motivo_y_fecha(harness):
    result = harness.discard(id="A-001", reason="ya no se quiere")

    assert result.success
    feat = _feature(harness, "A-001")
    assert feat["status"] == "discarded"
    assert feat["discarded_reason"] == "ya no se quiere"
    assert feat["discarded_on"]


def test_discard_escribe_una_linea_en_history(harness):
    harness.discard(id="A-001", reason="ya no se quiere")

    lineas = [ln for ln in _history(harness).splitlines() if "Descartada" in ln]
    assert len(lineas) == 1
    assert "A-001" in lineas[0]
    assert "Primera" in lineas[0]
    assert "ya no se quiere" in lineas[0]


def test_discard_sin_motivo_pide_el_motivo(harness):
    antes = _bytes(harness)
    result = harness.discard(id="A-001")

    assert not result.success
    assert result.needs
    assert _bytes(harness) == antes
    assert _feature(harness, "A-001")["status"] == "pending"


@pytest.mark.parametrize("status", ["done", "in_progress"])
def test_discard_rechaza_done_e_in_progress(harness, status):
    _set_status(harness, "A-001", status)
    antes = _bytes(harness)

    result = harness.discard(id="A-001", reason="porque sí")

    assert not result.success
    assert _bytes(harness) == antes
    assert _feature(harness, "A-001")["status"] == status


def test_discard_de_una_ya_descartada_falla(harness):
    harness.discard(id="A-001", reason="una vez")
    result = harness.discard(id="A-001", reason="otra vez")

    assert not result.success
    assert _feature(harness, "A-001")["discarded_reason"] == "una vez"


def test_discard_de_una_blocked_limpia_blocked_reason(harness):
    doc = _doc(harness)
    feat = next(f for f in doc["features"] if f["id"] == "B-001")
    feat["status"] = "blocked"
    feat["blocked_reason"] = "faltaba decidir"
    (harness.ctx.root / "harness" / "featureslist.json").write_text(
        json.dumps(doc, indent=2), encoding="utf-8"
    )

    result = harness.discard(id="B-001", reason="ya no se quiere")

    assert result.success
    feat = _feature(harness, "B-001")
    assert feat["status"] == "discarded"
    assert "blocked_reason" not in feat
    assert feat["discarded_reason"] == "ya no se quiere"


def test_discard_avisa_de_los_dependientes_sin_impedirlo(harness):
    result = harness.discard(id="A-001", reason="ya no se quiere")

    assert result.success
    assert result.data is not None
    assert result.data["dependents"] == ["B-001"]
    assert any("B-001" in w for w in result.warnings)


def test_block_rechaza_una_descartada(harness):
    harness.discard(id="A-001", reason="ya no")

    result = harness.block(id="A-001", reason="intento resucitarla")

    assert not result.success
    assert "descartada" in result.message
    feat = _feature(harness, "A-001")
    assert feat["status"] == "discarded"
    assert "blocked_reason" not in feat


# -- status / next -----------------------------------------------------------
def test_status_cuenta_las_descartadas_aparte(harness):
    harness.discard(id="A-001", reason="ya no")

    result = harness.status()

    assert result.data is not None
    assert result.data["counts"]["discarded"] == 1
    assert result.data["counts"]["blocked"] == 0
    assert result.data["discarded"] == ["A-001"]
    assert "1 discarded" in result.message


def test_next_no_devuelve_ni_ofrece_una_descartada(harness):
    harness.discard(id="C-001", reason="ya no se quiere")

    result = harness.next()
    estado = harness.status()

    assert result.success
    assert result.data["id"] == "A-001"
    assert "C-001" not in estado.data["eligible"]


# -- revive ------------------------------------------------------------------
def test_revive_devuelve_a_pending_y_limpia_el_rastro(harness):
    harness.discard(id="A-001", reason="ya no")
    doc = _doc(harness)
    next(f for f in doc["features"] if f["id"] == "A-001")["review_rounds"] = 2
    (harness.ctx.root / "harness" / "featureslist.json").write_text(
        json.dumps(doc, indent=2), encoding="utf-8"
    )

    result = harness.revive(id="A-001")

    assert result.success
    feat = _feature(harness, "A-001")
    assert feat["status"] == "pending"
    assert "discarded_reason" not in feat
    assert "discarded_on" not in feat
    assert feat["review_rounds"] == 0


def test_revive_rechaza_una_feature_que_no_estaba_descartada(harness):
    assert not harness.revive(id="A-001").success


def test_start_rechaza_una_descartada(harness):
    harness.discard(id="A-001", reason="ya no")

    result = harness.start(id="A-001")

    assert not result.success
    assert "revive" in result.message
    assert _feature(harness, "A-001")["status"] == "discarded"


def test_start_funciona_tras_revivir(harness):
    harness.discard(id="A-001", reason="ya no")
    harness.revive(id="A-001")

    assert harness.start(id="A-001").success
    assert _feature(harness, "A-001")["status"] == "in_progress"


def test_finish_rechaza_una_descartada(harness, monkeypatch):
    harness.discard(id="A-001", reason="ya no")
    # La guardia debe ser el ÚNICO motivo del rechazo: con la puerta en verde y
    # evidencia, si desapareciera la feature se cerraría.
    monkeypatch.setattr(
        harness,
        "gate",
        lambda **_: AgentResult(success=True, agent="harness", action="gate", message="ok"),
    )

    result = harness.finish(id="A-001", evidence="no aplica")

    assert not result.success
    assert "descartada" in result.message
    assert _feature(harness, "A-001")["status"] == "discarded"


# -- remove ------------------------------------------------------------------
def test_remove_borra_solo_la_pending_y_conserva_los_informes(harness):
    informe = harness.ctx.root / "harness" / "progress" / "explorer-C-001.md"
    informe.write_text("# explorer · C-001\n", encoding="utf-8")

    result = harness.remove(id="C-001")

    assert result.success
    doc = _doc(harness)
    assert [f["id"] for f in doc["features"]] == ["A-001", "B-001"]
    assert "C-001" not in _bytes(harness).decode("utf-8")
    assert informe.is_file()
    assert "explorer-C-001.md" in result.data["reports_kept"]


@pytest.mark.parametrize("status", ["done", "in_progress"])
def test_remove_rechaza_done_e_in_progress(harness, status):
    # C-001 no tiene dependientes: si el rechazo viniera de la guardia de
    # depends_on, quitar la de estado dejaría este test en verde sin querer.
    _set_status(harness, "C-001", status)
    antes = _bytes(harness)

    result = harness.remove(id="C-001")

    assert not result.success
    assert result.data is not None
    assert result.data["status"] == status
    assert _bytes(harness) == antes


@pytest.mark.parametrize("status", ["blocked", "discarded"])
def test_remove_rechaza_blocked_y_discarded(harness, status):
    _set_status(harness, "C-001", status)
    antes = _bytes(harness)

    result = harness.remove(id="C-001")

    assert not result.success
    assert result.data is not None
    assert result.data["status"] == status
    assert _bytes(harness) == antes


def test_remove_se_niega_si_otra_depende_y_la_nombra(harness):
    antes = _bytes(harness)

    result = harness.remove(id="A-001")

    assert not result.success
    assert result.data is not None
    assert result.data["dependents"] == ["B-001"]
    assert "B-001" in result.message
    assert _bytes(harness) == antes


def test_remove_dry_run_no_escribe_nada(harness):
    antes = _bytes(harness)

    result = harness.run("remove", id="C-001", dry_run=True)

    assert result.success
    assert result.data is not None
    assert result.data["dry_run"] is True
    assert _bytes(harness) == antes


def test_remove_sin_yes_pide_confirmacion(harness, monkeypatch):
    monkeypatch.delenv("HARNESS_ASSUME_YES", raising=False)
    monkeypatch.delenv("HARNESS_CONFIRM", raising=False)
    antes = _bytes(harness)

    result = harness.run("remove", id="C-001")

    assert not result.success
    assert result.needs
    assert _bytes(harness) == antes


def test_remove_con_confirm_borra(harness, monkeypatch):
    monkeypatch.delenv("HARNESS_ASSUME_YES", raising=False)
    monkeypatch.delenv("HARNESS_CONFIRM", raising=False)

    result = harness.run("remove", id="C-001", confirm=True)

    assert result.success
    assert "C-001" not in _bytes(harness).decode("utf-8")
