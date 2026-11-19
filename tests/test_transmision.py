"""Transmisión intergeneracional y nodos apagados (concepto §6 y §9)."""

from __future__ import annotations

import random

import pytest

from tribal.core import acciones
from tribal.core.genoma import Genoma, temperamento
from tribal.core.habilidades import Habilidades
from tribal.core.modelos import (
    Individuo,
    Mundo,
    Necesidades,
    Recurso,
    TipoRecurso,
    TipoTile,
)
from tribal.culture import transmision
from tribal.culture.grafo import Grafo
from tribal.sim import SimConfig, Simulacion


def _individuo(
    id_: int,
    *,
    x: float = 2.0,
    edad: int = 300,
    genoma: Genoma | None = None,
    habilidades: Habilidades | None = None,
) -> Individuo:
    return Individuo(
        id=id_,
        sexo="m" if id_ % 2 else "f",
        genoma=genoma or Genoma(),
        necesidades=Necesidades(energia=10.0),
        x=x,
        y=2.0,
        edad=edad,
        habilidades=habilidades or Habilidades(),
    )


def _mundo(
    individuos: list[Individuo], seed: int = 1, recursos: list[Recurso] | None = None
) -> Mundo:
    tiles = [[TipoTile.HIERBA for _ in range(12)] for _ in range(12)]
    return Mundo(
        ancho=12,
        alto=12,
        tiles=tiles,
        recursos=[] if recursos is None else recursos,
        individuos=individuos,
        azar=random.Random(seed),
    )


def _grafo_con_raedera() -> Grafo:
    """Un nodo de combinación: la única técnica con habilidad aprendida propia."""
    grafo = Grafo()
    grafo.descubrir("guijarro", autor=1, tick=0)
    grafo.descubrir("lasca", autor=1, tick=1)
    grafo.descubrir("bifaz", autor=1, tick=2)
    grafo.descubrir("raedera", autor=1, tick=3)
    return grafo


def test_sin_portadores_el_nodo_queda_apagado_y_no_se_borra() -> None:
    grafo = _grafo_con_raedera()
    mundo = _mundo([_individuo(1, habilidades=Habilidades({"fabricar"}))])
    desde: dict[str, int] = {}

    assert transmision.portadores(mundo, "raedera") == 1
    assert transmision.sostener(grafo, mundo, desde, tick=4) == []

    muere = 5
    mundo.individuos = []  # el único portador muere sin enseñar
    assert transmision.sostener(grafo, mundo, desde, tick=muere) == []
    assert (
        transmision.sostener(grafo, mundo, desde, tick=muere + transmision.TICKS_SIN_PORTADOR - 1)
        == []
    )
    assert grafo.activo("raedera")

    apagados = transmision.sostener(
        grafo, mundo, desde, tick=muere + transmision.TICKS_SIN_PORTADOR
    )

    assert ("raedera", muere + transmision.TICKS_SIN_PORTADOR) in apagados
    nodo = grafo.nodos["raedera"]
    assert nodo.estado == "apagado"
    assert nodo.tick_apagado == muere + transmision.TICKS_SIN_PORTADOR
    assert nodo.motivo_apagado == transmision.MOTIVO_SIN_PORTADORES
    # El nodo sigue en el grafo y su nacimiento (origen, autor, tick) no se toca.
    assert (nodo.origen, nodo.autor, nodo.tick) == ("combinacion", 1, 3)
    assert grafo.contar() == {"activos": 0, "apagados": 4}
    # Apagarlo otra vez no reescribe su historia.
    assert grafo.apagar("raedera", tick=999, motivo="otro") is None
    assert grafo.nodos["raedera"].motivo_apagado == transmision.MOTIVO_SIN_PORTADORES


def test_con_ensenanza_previa_el_nodo_sobrevive_a_la_muerte_del_portador() -> None:
    grafo = _grafo_con_raedera()
    maestro = _individuo(1, habilidades=Habilidades({"fabricar", "recolectar"}))
    aprendiz = _individuo(2, x=2.5, habilidades=Habilidades({"recolectar"}))
    mundo = _mundo([maestro, aprendiz])

    assert acciones.ensenar(maestro, mundo, aprendiz, lenguaje=True) is True
    assert aprendiz.habilidades.sabe("fabricar")

    mundo.individuos = [aprendiz]  # muere el portador original, no la técnica
    desde: dict[str, int] = {}
    assert transmision.sostener(grafo, mundo, desde, tick=5) == []
    assert (
        transmision.sostener(grafo, mundo, desde, tick=5 + 10 * transmision.TICKS_SIN_PORTADOR)
        == []
    )
    assert grafo.activo("raedera")


def test_sin_lenguaje_ensenar_no_transfiere() -> None:
    maestro = _individuo(1, habilidades=Habilidades({"fabricar", "recolectar"}))
    aprendiz = _individuo(2, x=2.5, habilidades=Habilidades({"recolectar"}))
    mundo = _mundo([maestro, aprendiz])

    assert acciones.ensenar(maestro, mundo, aprendiz, lenguaje=False) is False
    assert not aprendiz.habilidades.sabe("fabricar")


def test_la_ensenanza_exige_proximidad_aunque_haya_lenguaje(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Decisivo: con probabilidad 100 y a 2,5 tiles (radio 2,0) sin el guard de
    # distancia la habilidad se transferiría; con el guard, no.
    monkeypatch.setattr(acciones, "PROB_ENSENANZA", 100.0)
    maestro = _individuo(1, habilidades=Habilidades({"fabricar", "recolectar"}))
    aprendiz = _individuo(2, x=4.5, habilidades=Habilidades({"recolectar"}))
    mundo = _mundo([maestro, aprendiz])

    assert acciones.ensenar(maestro, mundo, aprendiz, lenguaje=True) is False
    assert not aprendiz.habilidades.sabe("fabricar")


def test_el_conformista_tambien_imita(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(acciones, "PROB_IMITACION", 1.0)
    modelo = _individuo(1, habilidades=Habilidades({"cazar"}))
    observador = _individuo(2, x=2.5, genoma=Genoma(divergencia=0.1))
    mundo = _mundo(
        [modelo, observador],
        recursos=[
            Recurso(
                id=1,
                tipo=TipoRecurso.CAZA,
                x=2,
                y=2,
                cantidad=4,
                capacidad=4,
                regeneracion=1500,
                alcance=1.5,
            )
        ],
    )

    assert temperamento(observador.genoma) == "conformista"
    assert acciones.comer(modelo, mundo) is True
    assert observador.habilidades.sabe("cazar")


def test_el_grafo_no_reactiva_un_nodo_apagado() -> None:
    grafo = _grafo_con_raedera()
    grafo.apagar("raedera", tick=10, motivo=transmision.MOTIVO_SIN_PORTADORES)

    assert grafo.descubrir("raedera", autor=9, tick=99).estado == "apagado"
    assert "raedera" in grafo.nodos


def test_la_simulacion_apaga_el_nodo_sin_portadores(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(transmision, "TICKS_SIN_PORTADOR", 2)
    portador = _individuo(1, habilidades=Habilidades({"fabricar", "recolectar"}))
    simulacion = Simulacion(_mundo([portador]), SimConfig(seed=0, individuos=1, depredadores=0))
    for nodo_id, tick in (("guijarro", 0), ("lasca", 0), ("bifaz", 0), ("raedera", 0)):
        simulacion.grafo.descubrir(nodo_id, autor=1, tick=tick)

    simulacion.step()
    assert simulacion.grafo.activo("raedera")

    simulacion.mundo.individuos = []
    for _ in range(3):
        simulacion.step()

    assert simulacion.grafo.nodos["raedera"].estado == "apagado"


def test_dos_corridas_iguales_apagan_los_mismos_nodos() -> None:
    def corrida() -> dict[str, object]:
        grafo = _grafo_con_raedera()
        mundo = _mundo([_individuo(1, habilidades=Habilidades({"fabricar"}))])
        desde: dict[str, int] = {}
        mundo.individuos = []
        transmision.sostener(grafo, mundo, desde, tick=0)
        transmision.sostener(grafo, mundo, desde, tick=transmision.TICKS_SIN_PORTADOR)
        return grafo.a_json()

    assert corrida() == corrida()
