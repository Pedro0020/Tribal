"""Habilidades: catálogo, efecto medible en la acción y aprendizaje social."""

from __future__ import annotations

import json
import random

import pytest

from tribal.agents import instinto
from tribal.agents import necesidades as nec
from tribal.cli import main
from tribal.core import acciones
from tribal.core.genoma import RASGOS, Genoma
from tribal.core.habilidades import CATALOGO, INICIALES, Habilidades
from tribal.core.modelos import (
    Individuo,
    Mundo,
    Necesidades,
    Recurso,
    TipoRecurso,
    TipoTile,
)
from tribal.sim import Simulacion, run


def _individuo(
    id_: int,
    *,
    x: float = 2.0,
    y: float = 2.0,
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
        y=y,
        edad=edad,
        habilidades=habilidades or Habilidades(),
    )


def _mundo(
    individuos: list[Individuo], seed: int = 0, recursos: list[Recurso] | None = None
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


def _comida(tipo: TipoRecurso, x: int = 2, y: int = 2) -> Recurso:
    return Recurso(
        id=1,
        tipo=tipo,
        x=x,
        y=y,
        cantidad=4,
        capacidad=4,
        regeneracion=1500,
        alcance=1.5,
    )


def _aporte(tipo: TipoRecurso, habilidades: Habilidades) -> float:
    """Energía ganada al comer un recurso del tipo dado, con esas habilidades."""
    individuo = _individuo(1, habilidades=habilidades)
    mundo = _mundo([individuo], recursos=[_comida(tipo)])
    antes = individuo.necesidades.energia

    assert acciones.comer(individuo, mundo) is True
    return individuo.necesidades.energia - antes


def test_el_catalogo_tiene_las_cinco_habilidades_del_arbol() -> None:
    assert {"cazar", "recolectar", "fabricar", "fuego", "ensenar"} == set(CATALOGO)
    ramas = {"litica", "fuego", "lenguaje", "roles", "simbolico"}
    assert {habilidad.rama for habilidad in CATALOGO.values()} <= ramas


def test_un_recien_nacido_sabe_recolectar_y_aprende_lo_demas() -> None:
    habilidades = Habilidades.iniciales()

    assert habilidades.sabe("recolectar")
    assert not habilidades.sabe("cazar")
    assert habilidades.aprender("cazar") is True
    assert habilidades.aprender("cazar") is False
    with pytest.raises(ValueError):
        habilidades.aprender("volar")
    assert frozenset({"recolectar"}) == INICIALES


def test_sin_habilidad_el_aporte_es_el_de_fase_0() -> None:
    assert _aporte(TipoRecurso.BAYAS, Habilidades()) == 40.0
    assert _aporte(TipoRecurso.CAZA, Habilidades()) == 60.0


def test_recolectar_y_cazar_aumentan_un_50_por_ciento_el_aporte() -> None:
    assert _aporte(TipoRecurso.BAYAS, Habilidades({"recolectar"})) == pytest.approx(60.0)
    assert _aporte(TipoRecurso.CAZA, Habilidades({"cazar"})) == pytest.approx(90.0)


def test_la_habilidad_de_otra_fuente_no_da_bonus() -> None:
    assert _aporte(TipoRecurso.BAYAS, Habilidades({"cazar"})) == 40.0
    assert _aporte(TipoRecurso.CAZA, Habilidades({"recolectar"})) == 60.0


def _sed_por_tick(resistencia: float) -> float:
    necesidades = Necesidades()
    nec.evolucionar(necesidades, Genoma(resistencia=resistencia), tasa_sed=1.0, tasa_energia=0.0)
    return necesidades.sed


def test_la_resistencia_es_simetrica_alrededor_de_1() -> None:
    assert _sed_por_tick(1.0) == pytest.approx(1.0)
    assert _sed_por_tick(1.5) == pytest.approx(0.8)
    assert _sed_por_tick(0.5) == pytest.approx(1.2)
    assert _sed_por_tick(1.2) == pytest.approx(0.92)
    assert _sed_por_tick(0.8) == pytest.approx(1.08)
    assert _sed_por_tick(0.8) > _sed_por_tick(1.0) > _sed_por_tick(1.2)


def _ensenanza(seed: int, distancia: float = 0.0, inteligencia: float = 1.0) -> bool:
    maestro = _individuo(1, habilidades=Habilidades({"recolectar", "cazar"}))
    aprendiz = _individuo(
        2,
        x=2.0 + distancia,
        genoma=Genoma(inteligencia=inteligencia),
        habilidades=Habilidades({"recolectar"}),
    )
    mundo = _mundo([maestro, aprendiz], seed=seed)
    return acciones.ensenar(maestro, mundo, aprendiz)


def test_ensenar_transmite_la_habilidad_y_depende_de_la_semilla() -> None:
    maestro = _individuo(1, habilidades=Habilidades({"recolectar", "cazar"}))
    aprendiz = _individuo(2, habilidades=Habilidades({"recolectar"}))
    mundo = _mundo([maestro, aprendiz], seed=1)

    assert acciones.ensenar(maestro, mundo, aprendiz) is True
    assert aprendiz.habilidades.sabe("cazar")

    resultados = {_ensenanza(seed) for seed in range(20)}
    assert resultados == {True, False}
    assert all(_ensenanza(seed) == _ensenanza(seed) for seed in range(10))


def test_ensenar_fuera_de_alcance_no_transmite() -> None:
    assert _ensenanza(seed=1, distancia=3.0) is False


def test_solo_un_adulto_ensena() -> None:
    maestro = _individuo(1, edad=0, habilidades=Habilidades({"recolectar", "cazar"}))
    aprendiz = _individuo(2, habilidades=Habilidades({"recolectar"}))
    mundo = _mundo([maestro, aprendiz], seed=1)

    assert acciones.ensenar(maestro, mundo, aprendiz) is False
    assert not aprendiz.habilidades.sabe("cazar")


def test_sin_nada_que_ensenar_no_hay_accion() -> None:
    maestro = _individuo(1, habilidades=Habilidades({"recolectar"}))
    aprendiz = _individuo(2, habilidades=Habilidades({"recolectar"}))
    mundo = _mundo([maestro, aprendiz], seed=1)

    assert acciones.candidato_a_ensenar(maestro, mundo) is None
    assert acciones.ensenar(maestro, mundo, aprendiz) is False


def test_la_imitacion_pasiva_aprende_al_ver_usar_la_habilidad() -> None:
    def imita(seed: int) -> bool:
        modelo = _individuo(1, habilidades=Habilidades({"cazar"}))
        observador = _individuo(2, x=2.5)
        mundo = _mundo([modelo, observador], seed=seed, recursos=[_comida(TipoRecurso.CAZA)])

        assert acciones.comer(modelo, mundo) is True
        return observador.habilidades.sabe("cazar")

    resultados = {imita(seed) for seed in range(30)}
    assert resultados == {True, False}
    assert all(imita(seed) == imita(seed) for seed in range(10))


def test_la_imitacion_no_alcanza_a_quien_esta_lejos() -> None:
    def imita(seed: int) -> bool:
        modelo = _individuo(1, habilidades=Habilidades({"cazar"}))
        observador = _individuo(2, x=9.0)
        mundo = _mundo([modelo, observador], seed=seed, recursos=[_comida(TipoRecurso.CAZA)])

        assert acciones.comer(modelo, mundo) is True
        return observador.habilidades.sabe("cazar")

    assert not any(imita(seed) for seed in range(20))


def test_el_instinto_no_elige_ensenar_sin_aprendiz() -> None:
    adulto = _individuo(1, habilidades=Habilidades({"recolectar"}))
    adulto.necesidades.energia = 100.0
    mundo = _mundo([adulto], seed=3)

    assert instinto.elegir(adulto, mundo).nombre != "ensenar"


def test_ensenar_fallido_no_clava_al_individuo() -> None:
    maestro = _individuo(1, habilidades=Habilidades({"recolectar", "fuego"}))
    aprendiz = _individuo(2, x=2.5, habilidades=Habilidades({"recolectar"}))
    maestro.necesidades.energia = 100.0
    aprendiz.necesidades.energia = 100.0
    # Semilla 0: el primer `random()` (0.844) supera la probabilidad de 0.5.
    mundo = _mundo([maestro, aprendiz], seed=0)
    simulacion = Simulacion(mundo)
    antes = (maestro.x, maestro.y)

    simulacion.step()

    assert not aprendiz.habilidades.sabe("fuego")
    assert (maestro.x, maestro.y) != antes


def test_el_instinto_ensena_cuando_falta_una_habilidad() -> None:
    maestro = _individuo(1, habilidades=Habilidades({"recolectar", "fuego"}))
    aprendiz = _individuo(2, x=2.5, habilidades=Habilidades({"recolectar"}))
    maestro.necesidades.energia = 100.0
    aprendiz.necesidades.energia = 100.0
    mundo = _mundo([maestro, aprendiz], seed=1)
    simulacion = Simulacion(mundo)

    for _ in range(20):
        simulacion.step()

    assert aprendiz.habilidades.sabe("fuego")


def test_las_habilidades_no_se_heredan_por_genoma() -> None:
    madre = _individuo(1, habilidades=Habilidades({"recolectar", "cazar", "fuego"}))
    padre = _individuo(2, x=3.0, habilidades=Habilidades({"recolectar", "fabricar"}))
    madre.necesidades.energia = 100.0
    padre.necesidades.energia = 100.0
    mundo = _mundo([madre, padre], seed=1)
    simulacion = Simulacion(mundo)

    simulacion.step()

    assert simulacion.nacimientos == 1
    hijo = mundo.individuos[-1]
    assert hijo.habilidades.conocidas == INICIALES


def test_el_resumen_incluye_media_de_genes_y_habilidades_distintas() -> None:
    resumen = run(ticks=120, seed=42, headless=True).resumen()

    assert set(resumen["media_genes"]) == set(RASGOS)
    assert resumen["habilidades_distintas"] == 1
    assert all("recolectar" in skills for skills in resumen["habilidades"].values())


def test_el_json_de_la_cli_incluye_genes_y_habilidades(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["run", "--headless", "--json", "--ticks", "60"]) == 0
    datos = json.loads(capsys.readouterr().out)

    assert set(datos["media_genes"]) == set(RASGOS)
    assert datos["habilidades_distintas"] >= 1
