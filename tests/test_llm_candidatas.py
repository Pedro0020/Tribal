"""Candidatas: 2–4 acciones y viabilidad física del estado (F2-CONTRATO)."""

from __future__ import annotations

import random

from tribal.core.genoma import Genoma
from tribal.core.modelos import (
    Depredador,
    Individuo,
    Mundo,
    Necesidades,
    Recurso,
    TipoRecurso,
    TipoTile,
)
from tribal.llm.candidatas import candidatas, estado_para
from tribal.sim import _hay_dilema


def _situacion(
    *,
    sed: float = 0.0,
    energia: float = 100.0,
    salud: float = 100.0,
    agua: bool = False,
    comida: bool = False,
    amenaza: bool = False,
    vecino: bool = False,
    pisable: bool = True,
) -> tuple[Individuo, Mundo]:
    individuo = Individuo(
        id=1,
        sexo="m",
        genoma=Genoma(),
        necesidades=Necesidades(energia=energia, sed=sed, salud=salud),
        x=10.0,
        y=10.0,
    )
    individuos = [individuo]
    if vecino:
        individuos.append(
            Individuo(
                id=2,
                sexo="f",
                genoma=Genoma(),
                necesidades=Necesidades(),
                x=10.0,
                y=11.0,
            )
        )
    recursos: list[Recurso] = []
    if agua:
        recursos.append(Recurso(1, TipoRecurso.AGUA, 10, 10, 40, 40, 10, 1.5))
    if comida:
        recursos.append(Recurso(2, TipoRecurso.BAYAS, 10, 10, 4, 4, 300, 1.5))
    tile = TipoTile.HIERBA if pisable else TipoTile.AGUA
    mundo = Mundo(
        ancho=24,
        alto=24,
        tiles=[[tile for _ in range(24)] for _ in range(24)],
        recursos=recursos,
        individuos=individuos,
        azar=random.Random(0),
    )
    if amenaza:
        mundo.depredadores.append(Depredador(x=10.5, y=10.0))
    return individuo, mundo


def _nombres(individuo: Individuo, mundo: Mundo) -> list[str]:
    return [accion.nombre for accion in candidatas(individuo, mundo)]


def test_sin_agua_al_alcance_no_hay_beber() -> None:
    individuo, mundo = _situacion(sed=90.0)
    assert "beber" not in _nombres(individuo, mundo)
    assert estado_para(individuo, mundo)["agua_al_alcance"] is False


def test_sin_comida_al_alcance_no_hay_comer() -> None:
    individuo, mundo = _situacion(energia=20.0)
    assert "comer" not in _nombres(individuo, mundo)
    assert estado_para(individuo, mundo)["comida_al_alcance"] is False


def test_sin_depredador_no_hay_huir() -> None:
    individuo, mundo = _situacion(sed=70.0, agua=True, comida=True)
    assert "huir" not in _nombres(individuo, mundo)
    assert estado_para(individuo, mundo)["amenaza"] is False


def test_depredador_cerca_ofrece_huir_primero() -> None:
    individuo, mundo = _situacion(amenaza=True, agua=True, comida=True)
    nombres = _nombres(individuo, mundo)
    assert nombres[0] == "huir"
    assert estado_para(individuo, mundo)["amenaza"] is True


def test_agua_y_comida_al_alcance_entran_como_candidatas() -> None:
    individuo, mundo = _situacion(sed=70.0, energia=30.0, agua=True, comida=True)
    nombres = _nombres(individuo, mundo)
    assert nombres[0] == "beber"
    assert "comer" in nombres


def test_candidatas_entre_dos_y_cuatro_con_dos_acciones_viables() -> None:
    casos = [
        _situacion(sed=80.0, agua=True, comida=True),
        _situacion(energia=20.0, agua=True, comida=True),
        _situacion(energia=5.0, vecino=True),
        _situacion(amenaza=True, agua=True, comida=True),
        _situacion(energia=100.0, vecino=True),
    ]
    for individuo, mundo in casos:
        nombres = _nombres(individuo, mundo)
        assert 2 <= len(nombres) <= 4, nombres
        assert len(set(nombres)) == len(nombres)


def test_sin_recursos_ni_vecinos_la_segunda_es_moverse() -> None:
    individuo, mundo = _situacion(energia=100.0, sed=0.0)
    nombres = _nombres(individuo, mundo)
    assert len(nombres) >= 2
    assert "moverse" in nombres


def test_el_dilema_sin_recursos_tambien_deja_dos_candidatas() -> None:
    individuo, mundo = _situacion(energia=45.0, sed=60.0)
    assert _hay_dilema(individuo, mundo) is True
    assert len(_nombres(individuo, mundo)) >= 2


def test_sin_tiles_pisables_queda_una_y_no_se_pide_decision() -> None:
    individuo, mundo = _situacion(energia=45.0, sed=60.0, pisable=False)
    nombres = _nombres(individuo, mundo)
    assert nombres == ["descansar"]
    assert _hay_dilema(individuo, mundo) is False
