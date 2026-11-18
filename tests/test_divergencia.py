"""Divergentes y conformistas (concepto §9b): genoma, crisis, cruces e imitación."""

from __future__ import annotations

import json
import random
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from tribal.cli import main
from tribal.config import SimConfig
from tribal.core.genoma import (
    UMBRAL_CONFORMISTA,
    UMBRAL_DIVERGENTE,
    Genoma,
    temperamento,
)
from tribal.core.habilidades import Habilidades
from tribal.core.modelos import (
    Individuo,
    Mundo,
    Necesidades,
    Recurso,
    TipoRecurso,
    TipoTile,
)
from tribal.culture.arbol import ARBOL
from tribal.culture.combinaciones import COMBINACIONES
from tribal.culture.grafo import Grafo, PrerequisitoFaltante
from tribal.sim import Simulacion, run

SEMILLA = 42


def test_el_genoma_decide_quien_experimenta_y_quien_imita() -> None:
    assert temperamento(Genoma(divergencia=0.9)) == "divergente"
    assert temperamento(Genoma(divergencia=0.3)) == "conformista"
    assert temperamento(Genoma(divergencia=0.5)) == "neutro"
    assert temperamento(Genoma(divergencia=UMBRAL_DIVERGENTE)) == "neutro"
    assert temperamento(Genoma(divergencia=UMBRAL_CONFORMISTA)) == "neutro"


def test_las_combinaciones_cruzan_dos_nodos_del_arbol_y_no_estan_en_el() -> None:
    assert COMBINACIONES
    for combinacion in COMBINACIONES.values():
        assert combinacion.id not in ARBOL
        assert combinacion.origen == "combinacion"
        assert len(combinacion.requisitos) == 2
        assert all(requisito in ARBOL for requisito in combinacion.requisitos)


def _mundo_de_dos(*individuos: Individuo) -> Mundo:
    """Seis por seis de hierba y un montón de bayas en (1, 1)."""
    tiles = [[TipoTile.HIERBA for _ in range(6)] for _ in range(6)]
    bayas = Recurso(
        id=1,
        tipo=TipoRecurso.BAYAS,
        x=1,
        y=1,
        cantidad=8,
        capacidad=8,
        regeneracion=420,
        alcance=1.5,
    )
    return Mundo(
        ancho=6,
        alto=6,
        tiles=tiles,
        recursos=[bayas],
        individuos=list(individuos),
        azar=random.Random(0),
    )


def _hambriento(id_: int, divergencia: float) -> Individuo:
    return Individuo(
        id=id_,
        sexo="m",
        genoma=Genoma(divergencia=divergencia),
        necesidades=Necesidades(energia=40.0),
        x=1.0,
        y=1.0,
        habilidades=Habilidades({"recolectar"}),
    )


def test_el_conformista_que_usa_un_nodo_ajeno_cuenta_como_imitacion() -> None:
    divergente = _hambriento(1, divergencia=0.9)
    conformista = _hambriento(2, divergencia=0.1)
    simulacion = Simulacion(_mundo_de_dos(divergente, conformista))

    simulacion.step()

    assert simulacion.grafo.nodos["guijarro"].autor == divergente.id
    assert simulacion.grafo.veces_usado == {"guijarro": 1}
    assert simulacion.grafo.imitado == {"guijarro": 1}
    assert simulacion.resumen()["imitaciones"] == 1


def test_ni_el_divergente_ni_el_neutro_suman_imitaciones() -> None:
    autor = _hambriento(1, divergencia=0.9)
    otro_divergente = _hambriento(2, divergencia=0.9)
    neutro = _hambriento(3, divergencia=0.5)
    simulacion = Simulacion(_mundo_de_dos(autor, otro_divergente, neutro))

    simulacion.step()

    assert simulacion.grafo.nodos["guijarro"].autor == autor.id
    assert simulacion.grafo.veces_usado == {"guijarro": 2}
    assert simulacion.grafo.imitado == {}
    assert simulacion.resumen()["imitaciones"] == 0


def test_el_mismo_montaje_con_un_conformista_si_suma_imitacion() -> None:
    autor = _hambriento(1, divergencia=0.9)
    otro_divergente = _hambriento(2, divergencia=0.9)
    conformista = _hambriento(3, divergencia=0.1)
    simulacion = Simulacion(_mundo_de_dos(autor, otro_divergente, conformista))

    simulacion.step()

    assert simulacion.grafo.veces_usado == {"guijarro": 2}
    assert simulacion.grafo.imitado == {"guijarro": 1}
    assert simulacion.resumen()["imitaciones"] == 1


def test_en_crisis_los_divergentes_intentan_y_aparecen_nodos_combinacion() -> None:
    simulacion = run(
        ticks=5000,
        seed=SEMILLA,
        headless=True,
        config=SimConfig(seed=SEMILLA, individuos=12, crisis=True),
    )

    resumen = simulacion.resumen()
    assert resumen["intentos_divergentes"] > 0
    assert resumen["combinaciones_logradas"] > 0
    assert resumen["nodos_por_origen"]["combinacion"] > 0
    assert any(nodo["origen"] == "combinacion" for nodo in resumen["nodos"])
    assert resumen["pct_fuera_arbol"] > 0.0


def test_sin_crisis_no_hay_intentos_ni_nodos_combinacion() -> None:
    simulacion = run(
        ticks=5000,
        seed=SEMILLA,
        headless=True,
        config=SimConfig(seed=SEMILLA, individuos=12),
    )

    resumen = simulacion.resumen()
    assert resumen["intentos_divergentes"] == 0
    assert resumen["combinaciones_logradas"] == 0
    assert resumen["nodos_por_origen"]["combinacion"] == 0
    assert all(nodo["origen"] == "arbol" for nodo in resumen["nodos"])


def test_el_origen_de_una_combinacion_es_inmutable() -> None:
    grafo = Grafo()
    grafo.descubrir("guijarro", autor=1, tick=1)
    grafo.descubrir("lasca", autor=1, tick=2)

    with pytest.raises(PrerequisitoFaltante):
        grafo.descubrir("raedera", autor=2, tick=3)

    grafo.descubrir("bifaz", autor=1, tick=3)
    nodo = grafo.descubrir("raedera", autor=2, tick=3)
    assert nodo.origen == "combinacion"
    assert (nodo.autor, nodo.tick) == (2, 3)

    with pytest.raises(FrozenInstanceError):
        nodo.__setattr__("origen", "llm")

    otra_vez = grafo.descubrir("raedera", autor=9, tick=99, origen="arbol")
    assert (otra_vez.origen, otra_vez.autor, otra_vez.tick) == ("combinacion", 2, 3)


@pytest.mark.parametrize(
    ("datos", "clave"),
    [
        ({"crisis": 1}, "crisis"),
        ({"sequia_ticks": -1}, "sequia_ticks"),
        ({"sequia_ticks": 1.5}, "sequia_ticks"),
    ],
)
def test_la_config_valida_crisis_y_sequia(
    tmp_path: Path, datos: dict[str, object], clave: str
) -> None:
    ruta = tmp_path / "cfg.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")

    with pytest.raises(ValueError) as fallo:
        SimConfig.desde_json(ruta)
    assert clave in str(fallo.value)


def test_el_cli_con_crisis_refleja_el_parametro_y_los_contadores(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["run", "--headless", "--json", "--ticks", "120", "--crisis"]) == 0

    datos = json.loads(capsys.readouterr().out)
    assert datos["config"]["crisis"] is True
    assert {"n_divergentes", "n_conformistas", "n_neutros"} <= set(datos)
    assert (
        datos["n_divergentes"] + datos["n_conformistas"] + datos["n_neutros"]
        == (datos["poblacion_final"])
    )


def test_dos_procesos_con_crisis_dan_la_misma_salida() -> None:
    comando = [
        sys.executable,
        "-m",
        "tribal",
        "run",
        "--seed",
        str(SEMILLA),
        "--headless",
        "--json",
        "--ticks",
        "600",
        "--crisis",
    ]

    primera = subprocess.run(comando, capture_output=True, text=True, check=True)
    segunda = subprocess.run(comando, capture_output=True, text=True, check=True)

    assert primera.stdout == segunda.stdout
