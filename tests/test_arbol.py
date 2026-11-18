"""Árbol de conocimiento: catálogo, prerrequisitos, origen de nacimiento y KPI."""

from __future__ import annotations

import json
import random
from dataclasses import FrozenInstanceError

import pytest

from tribal.cli import main
from tribal.core.habilidades import Habilidades
from tribal.core.modelos import (
    Genoma,
    Individuo,
    Mundo,
    Necesidades,
    Recurso,
    TipoRecurso,
    TipoTile,
)
from tribal.culture.arbol import ARBOL, RAMAS
from tribal.culture.grafo import Arista, Grafo, PrerequisitoFaltante
from tribal.sim import Simulacion, crear

RAMAS_ESPERADAS = {"litica", "fuego", "lenguaje", "roles", "simbolico"}


def _mundo_con_bayas(*individuos: Individuo) -> tuple[Mundo, Recurso]:
    """Seis por seis de hierba y un montón de bayas en la casilla (1, 1)."""
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
    mundo = Mundo(
        ancho=6,
        alto=6,
        tiles=tiles,
        recursos=[bayas],
        individuos=list(individuos),
        azar=random.Random(0),
    )
    return mundo, bayas


def _hambriento(id_: int, habilidades: set[str]) -> Individuo:
    """Adulto con el hambre justa encima de las bayas: este tick come."""
    return Individuo(
        id=id_,
        sexo="m",
        genoma=Genoma(),
        necesidades=Necesidades(energia=40.0),
        x=1.0,
        y=1.0,
        habilidades=Habilidades(habilidades),
    )


def test_el_arbol_cubre_las_cinco_ramas_con_una_escalera_sin_huecos() -> None:
    assert {nodo.rama for nodo in ARBOL.values()} == RAMAS_ESPERADAS
    for rama in RAMAS:
        niveles = {nodo.nivel for nodo in ARBOL.values() if nodo.rama == rama}
        assert niveles == set(range(max(niveles) + 1)), f"{rama}: escalera con huecos"


def test_los_requisitos_existen_y_forman_un_dag() -> None:
    for nodo in ARBOL.values():
        for requisito in nodo.requisitos:
            assert requisito in ARBOL, f"{nodo.id} exige un nodo que no existe: {requisito}"
            assert requisito != nodo.id

    estado: dict[str, int] = {}

    def visitar(nodo_id: str) -> None:
        if estado.get(nodo_id) == 2:
            return
        assert estado.get(nodo_id) != 1, f"ciclo de prerrequisitos en {nodo_id}"
        estado[nodo_id] = 1
        for requisito in ARBOL[nodo_id].requisitos:
            visitar(requisito)
        estado[nodo_id] = 2

    for nodo_id in ARBOL:
        visitar(nodo_id)


def test_los_nodos_de_nivel_cero_no_exigen_nada_y_el_mito_cruza_ramas() -> None:
    assert all(nodo.requisitos == () for nodo in ARBOL.values() if nodo.nivel == 0)
    assert {ARBOL[requisito].rama for requisito in ARBOL["mito"].requisitos} == {
        "lenguaje",
        "simbolico",
    }


def test_sin_prerrequisito_no_hay_nodo() -> None:
    grafo = Grafo()

    with pytest.raises(PrerequisitoFaltante) as fallo:
        grafo.descubrir("lasca", autor=1, tick=10)

    assert "guijarro" in str(fallo.value)
    assert grafo.nodos == {}
    assert grafo.aristas == []


def test_con_el_prerrequisito_el_nodo_nace_con_origen_arbol() -> None:
    grafo = Grafo()
    grafo.descubrir("guijarro", autor=3, tick=7)

    nodo = grafo.descubrir("lasca", autor=5, tick=42)

    assert nodo.id == "lasca"
    assert nodo.origen == "arbol"
    assert (nodo.autor, nodo.tick, nodo.estado) == (5, 42, "activo")
    assert grafo.aristas == [Arista("guijarro", "lasca")]
    assert grafo.activo("lasca")


def test_un_nodo_que_no_esta_en_el_arbol_no_existe() -> None:
    with pytest.raises(ValueError, match="desconocido"):
        Grafo().descubrir("fuego_artificial", autor=1, tick=1)


def test_el_origen_no_se_puede_reescribir_despues() -> None:
    grafo = Grafo()
    grafo.descubrir("guijarro", autor=1, tick=1)
    nodo = grafo.nodos["guijarro"]

    with pytest.raises(FrozenInstanceError):
        # Sin setter posible: el `__setattr__` que genera `frozen` rebota.
        nodo.__setattr__("origen", "llm")

    # Redescubrirlo es idempotente: ni origen, ni autor, ni tick cambian.
    otra_vez = grafo.descubrir("guijarro", autor=9, tick=99, origen="combinacion")
    assert (otra_vez.origen, otra_vez.autor, otra_vez.tick) == ("arbol", 1, 1)
    assert grafo.nodos["guijarro"] is otra_vez
    assert grafo.aristas == []


def test_pct_fuera_arbol_es_cero_sin_nodos_de_emergencia() -> None:
    grafo = Grafo()
    grafo.descubrir("guijarro", autor=1, tick=1)
    grafo.descubrir("lasca", autor=1, tick=2)

    assert grafo.pct_fuera_arbol() == 0.0
    assert grafo.a_json()["pct_fuera_arbol"] == 0.0
    assert grafo.nodos_por_origen() == {"arbol": 2, "combinacion": 0, "interaccion": 0, "llm": 0}


def test_pct_fuera_arbol_solo_cuenta_combinacion_e_interaccion() -> None:
    grafo = Grafo()
    grafo.descubrir("guijarro", autor=1, tick=1)  # arbol
    grafo.descubrir("observar_rayo", autor=1, tick=2)  # arbol
    grafo.descubrir("gestos", autor=1, tick=3)  # arbol
    grafo.descubrir("lasca", autor=1, tick=4, origen="combinacion")
    grafo.descubrir("bifaz", autor=1, tick=5, origen="interaccion")

    assert grafo.pct_fuera_arbol() == 40.0  # 2 de 5

    # `llm` cuenta en el reparto por origen, pero no es un nivel 1/2 de §8b.
    grafo.descubrir("conservar_brasas", autor=1, tick=6, origen="llm")
    assert grafo.nodos_por_origen()["llm"] == 1
    assert grafo.pct_fuera_arbol() == 33.3  # 2 de 6


def test_sin_la_habilidad_no_se_descubre_nodo() -> None:
    mundo, bayas = _mundo_con_bayas(_hambriento(1, habilidades=set()))
    simulacion = Simulacion(mundo)

    simulacion.step()

    assert bayas.cantidad == 7, "el individuo comió: el tick ocurrió"
    assert simulacion.grafo.nodos == {}


def test_con_la_habilidad_el_nodo_nace_en_el_arbol() -> None:
    individuo = _hambriento(1, habilidades={"recolectar"})
    mundo, _ = _mundo_con_bayas(individuo)
    simulacion = Simulacion(mundo)

    simulacion.step()

    nodo = simulacion.grafo.nodos["guijarro"]
    assert nodo.origen == "arbol"
    assert nodo.autor == individuo.id


def test_como_mucho_un_nodo_nuevo_por_tick() -> None:
    individuos = [_hambriento(id_, habilidades={"recolectar"}) for id_ in (1, 2, 3)]
    mundo, bayas = _mundo_con_bayas(*individuos)
    simulacion = Simulacion(mundo)

    simulacion.step()

    assert bayas.cantidad == 5, "los tres comieron en el mismo tick"
    assert list(simulacion.grafo.nodos) == ["guijarro"]


def test_la_simulacion_descubre_el_arbol_y_alguna_tradicion() -> None:
    simulacion = crear(seed=42)
    for _ in range(600):
        simulacion.step()

    resumen = simulacion.resumen()
    assert resumen["nodos"], "la corrida no descubrió ningún nodo"
    del_arbol = [nodo for nodo in resumen["nodos"] if nodo["origen"] == "arbol"]
    assert del_arbol[0]["id"] == "guijarro"
    assert resumen["nodos_por_origen"]["arbol"] >= 5
    assert resumen["nodos_por_origen"]["interaccion"] >= 1
    assert resumen["pct_fuera_arbol"] > 0.0
    ids = {nodo["id"] for nodo in resumen["nodos"]}
    assert all(
        arista["origen"] in ids and arista["destino"] in ids for arista in resumen["aristas"]
    )


def test_report_culture_json_imprime_nodos_aristas_y_pct(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["report", "culture", "--json"]) == 0

    datos = json.loads(capsys.readouterr().out)
    assert datos["seed"] == 42
    assert datos["nodos"]
    assert datos["aristas"]
    assert datos["crisis"] is False
    assert datos["nivel_max"] == 2
    assert datos["pct_fuera_arbol"] > 0.0
    assert datos["nodos_por_origen"]["arbol"] >= 5
    assert datos["nodos_por_origen"]["interaccion"] >= 1


def test_report_culture_sin_json_es_legible(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["report", "culture", "--ticks", "300"]) == 0

    salida = capsys.readouterr().out
    assert "pct_fuera_arbol" in salida
    assert "Guijarro" in salida
