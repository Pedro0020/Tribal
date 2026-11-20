"""MEDIR-LLM: el resumen mide acciones decididas, no peticiones enviadas.

Una acción cuenta para el LLM solo si aplicó una `intencion_llm` vigente; el
experimento de un divergente y la corrección del motor cuentan instinto. El
ancla es el caso en que hubo intención pero no se pudo aplicar: si la métrica
contara lo encolado como decidido, ese tick sumaría al LLM y el test cae.
"""

from __future__ import annotations

import random
from pathlib import Path

from tribal.config import SimConfig
from tribal.core.genoma import Genoma
from tribal.core.modelos import Individuo, Mundo, Necesidades, TipoTile
from tribal.llm.cliente import ClienteLLM, backend_stub
from tribal.llm.cola import ColaLLM
from tribal.sim import Simulacion, run


def _mundo(*individuos: Individuo) -> Mundo:
    """Seis por seis de hierba, sin recursos: nada se resuelve por el mapa."""
    tiles = [[TipoTile.HIERBA for _ in range(6)] for _ in range(6)]
    return Mundo(
        ancho=6,
        alto=6,
        tiles=tiles,
        recursos=[],
        individuos=list(individuos),
        azar=random.Random(0),
    )


def _individuo(id_: int, *, energia: float = 60.0) -> Individuo:
    return Individuo(
        id=id_,
        sexo="m",
        genoma=Genoma(divergencia=0.5),
        necesidades=Necesidades(energia=energia, sed=0.0, salud=100.0),
        x=1.0,
        y=1.0,
    )


def _stub() -> ColaLLM:
    return ColaLLM(ClienteLLM(transporte=backend_stub()), sincrona=True)


def test_el_resumen_publica_acciones_llm_e_instinto_por_tramo() -> None:
    datos = run(1200, 42, headless=True, cola=_stub()).resumen()
    acciones = datos["llm"]["acciones"]

    # El stub decide de verdad: hay acciones del LLM, pero el instinto cubre
    # la mayoría. Las peticiones no son acciones: algunas no llegaron a usarse.
    assert acciones["llm"] > 0
    assert acciones["instinto"] > acciones["llm"]
    assert acciones["llm"] < datos["llm"]["peticiones"]
    assert acciones["total"] == acciones["llm"] + acciones["instinto"]
    assert acciones["pct_llm"] == round(100 * acciones["llm"] / acciones["total"], 1)

    tramos = acciones["por_tramo"]
    assert len(tramos) == 1200 // 60
    assert sum(tramo["llm"] for tramo in tramos) == acciones["llm"]
    assert sum(tramo["instinto"] for tramo in tramos) == acciones["instinto"]
    for tramo in tramos:
        assert tramo["llm"] + tramo["instinto"] > 0
        assert tramo["pct_llm"] == round(100 * tramo["llm"] / (tramo["llm"] + tramo["instinto"]), 1)
    assert any(tramo["pct_llm"] > 0 for tramo in tramos)


def test_los_tramos_cubren_la_partida_sin_huecos() -> None:
    simulacion = Simulacion(
        _mundo(_individuo(1)),
        SimConfig(seed=0, individuos=1, depredadores=0),
        cola=_stub(),
    )
    for _ in range(120):
        simulacion.step()

    acciones = simulacion.resumen()["llm"]["acciones"]
    assert [tramo["tramo"] for tramo in acciones["por_tramo"]] == [0, 1]
    assert [tramo["instinto"] for tramo in acciones["por_tramo"]] == [60, 60]
    assert acciones["total"] == 120


def test_una_intencion_aplicada_cuenta_como_llm() -> None:
    simulacion = Simulacion(
        _mundo(_individuo(1)),
        SimConfig(seed=0, individuos=1, depredadores=0),
    )
    simulacion.mundo.individuos[0].intencion_llm = ("descansar", 1)

    simulacion.step()

    assert simulacion.acciones_llm == 1
    assert simulacion.acciones_instinto == 0
    assert simulacion.acciones_totales == 1


def test_una_intencion_no_aplicable_cuenta_instinto_no_llm() -> None:
    """Ancla de mutación: contar lo encolado como decidido rompe esta aserción."""
    simulacion = Simulacion(
        _mundo(_individuo(1)),
        SimConfig(seed=0, individuos=1, depredadores=0),
    )
    # No hay agua en el mapa: el motor descarta la intención y vuelve al instinto.
    simulacion.mundo.individuos[0].intencion_llm = ("beber", 1)

    simulacion.step()

    assert simulacion.mundo.individuos[0].intencion_llm is None
    assert simulacion.acciones_llm == 0
    assert simulacion.acciones_instinto == 1


def test_una_intencion_caducada_cuenta_instinto_no_llm() -> None:
    """La ventana cerrada es el error plausible: había intención, pero no vale."""
    simulacion = Simulacion(
        _mundo(_individuo(1)),
        SimConfig(seed=0, individuos=1, depredadores=0),
        cola=_stub(),
    )
    # `step` sube el reloj a 1: la intención venció en el tick 0.
    simulacion.mundo.individuos[0].intencion_llm = ("descansar", simulacion.mundo.tick)

    simulacion.step()

    acciones = simulacion.resumen()["llm"]["acciones"]
    assert acciones == {
        "llm": 0,
        "instinto": 1,
        "total": 1,
        "pct_llm": 0.0,
        "por_tramo": [{"tramo": 0, "llm": 0, "instinto": 1, "pct_llm": 0.0}],
    }


def test_los_tramos_sin_acciones_se_incluyen() -> None:
    """Una tribu extinta no deja huecos en el eje temporal de la métrica."""
    simulacion = Simulacion(
        _mundo(),
        SimConfig(seed=0, individuos=1, depredadores=0),
        cola=_stub(),
    )
    for _ in range(120):
        simulacion.step()

    acciones = simulacion.resumen()["llm"]["acciones"]
    assert acciones["total"] == 0
    assert [tramo["tramo"] for tramo in acciones["por_tramo"]] == [0, 1]
    assert all(tramo["llm"] + tramo["instinto"] == 0 for tramo in acciones["por_tramo"])
    assert all(tramo["pct_llm"] == 0.0 for tramo in acciones["por_tramo"])


def test_los_contadores_de_acciones_sobreviven_a_reanudar(tmp_path: Path) -> None:
    db = tmp_path / "medir.db"
    primera = run(600, 42, headless=True, db=db, cola=_stub())
    parcial = primera.resumen()["llm"]["acciones"]

    segunda = run(600, 42, headless=True, db=db, resume=True, cola=_stub())
    acciones = segunda.resumen()["llm"]["acciones"]

    assert parcial["llm"] > 0
    assert acciones["llm"] >= parcial["llm"]
    assert acciones["instinto"] >= parcial["instinto"]
    assert acciones["total"] == acciones["llm"] + acciones["instinto"]
    assert len(acciones["por_tramo"]) == 1200 // 60
    primeros = acciones["por_tramo"][: len(parcial["por_tramo"])]
    for antes, despues in zip(parcial["por_tramo"], primeros, strict=True):
        assert despues["llm"] >= antes["llm"]
        assert despues["instinto"] >= antes["instinto"]


def test_sin_llm_no_hay_acciones_decididas_por_el_llm() -> None:
    simulacion = run(120, 42, headless=True)

    assert "llm" not in simulacion.resumen()
    assert simulacion.acciones_llm == 0
    assert simulacion.acciones_instinto == simulacion.acciones_totales > 0
