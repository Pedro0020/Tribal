"""Tradiciones (nivel 2 de concepto §8b): imitación social y persistencia."""

from __future__ import annotations

import json
import random
import subprocess
import sys
from dataclasses import replace

import pytest

from tribal.cli import main
from tribal.config import SimConfig
from tribal.core import mundo as modulo_mundo
from tribal.core.modelos import Genoma, Individuo, Mundo, Necesidades, TipoTile
from tribal.culture import tradiciones
from tribal.culture.arbol import Nodo
from tribal.culture.grafo import Arista, Grafo
from tribal.sim import Simulacion, run

SEMILLA = 42


def _grafo_con_guijarro() -> Grafo:
    grafo = Grafo()
    grafo.descubrir("guijarro", autor=1, tick=1)
    return grafo


def _correr(mundo: Mundo, ticks: int) -> Simulacion:
    simulacion = Simulacion(mundo)
    for _ in range(ticks):
        simulacion.step()
    return simulacion


def test_tres_imitadores_distintos_convierten_la_practica_en_tradicion() -> None:
    grafo = _grafo_con_guijarro()
    for usuario in (2, 3, 4):
        assert grafo.registrar_uso("guijarro", usuario=usuario, es_conformista=True, tick=10)

    nodo = tradiciones.evaluar(grafo, tick=20)

    assert nodo is not None
    assert nodo.id == "tradicion_litica_1"
    assert nodo.origen == "interaccion"
    assert nodo.rama == "litica", "la tradición pertenece a la rama de la práctica"
    assert nodo.requisitos == ("guijarro",)
    assert nodo.titulo == "Cantera del grupo"
    assert "talla" in nodo.contenido and "memoria" in nodo.contenido
    assert (nodo.autor, nodo.tick) == (4, 20)
    assert grafo.activo(nodo.id)
    assert Arista("guijarro", "tradicion_litica_1") in grafo.aristas
    assert grafo.nodos_por_origen() == {"arbol": 1, "combinacion": 0, "interaccion": 1, "llm": 0}
    assert grafo.a_json()["nivel_max"] == 2


def test_una_tradicion_no_nace_de_un_nodo_llm() -> None:
    grafo = Grafo()
    grafo.descubrir("guijarro", autor=1, tick=1)
    grafo.agregar(
        Nodo(
            "llm_inventado",
            "litica",
            1,
            "Canto inventado",
            "Un nodo que el KPI excluye a propósito.",
            requisitos=("guijarro",),
            origen="llm",
            autor=1,
            tick=2,
        )
    )
    for usuario in (2, 3, 4):
        grafo.registrar_uso("llm_inventado", usuario=usuario, es_conformista=True, tick=10)

    assert tradiciones.evaluar(grafo, tick=20) is None
    assert grafo.nodos_por_origen()["interaccion"] == 0


def test_como_mucho_una_tradicion_por_rama() -> None:
    grafo = Grafo()
    grafo.descubrir("guijarro", autor=1, tick=1)
    grafo.descubrir("lasca", autor=1, tick=2)
    grafo.descubrir("bifaz", autor=1, tick=3)
    for nodo_id in ("guijarro", "lasca", "bifaz"):
        for usuario in (2, 3, 4):
            grafo.registrar_uso(nodo_id, usuario=usuario, es_conformista=True, tick=10)

    primera = tradiciones.evaluar(grafo, tick=20)
    segunda = tradiciones.evaluar(grafo, tick=21)

    assert primera is not None and primera.id == "tradicion_litica_1"
    assert segunda is None
    assert len(tradiciones._tradiciones_de(grafo, "litica")) == 1


def test_la_tradicion_que_deja_de_imitarse_se_apaga() -> None:
    grafo = _grafo_con_guijarro()
    for usuario in (2, 3, 4):
        grafo.registrar_uso("guijarro", usuario=usuario, es_conformista=True, tick=10)
    nodo = tradiciones.evaluar(grafo, tick=20)
    assert nodo is not None

    assert tradiciones.sostener(grafo, tick=20 + tradiciones.TICKS_SIN_IMITACION - 1) == []
    apagadas = tradiciones.sostener(grafo, tick=20 + tradiciones.TICKS_SIN_IMITACION)

    assert apagadas == [(nodo.id, 20 + tradiciones.TICKS_SIN_IMITACION)]
    assert grafo.nodos[nodo.id].estado == "apagado"
    assert grafo.nodos[nodo.id].motivo_apagado == tradiciones.MOTIVO_SIN_IMITACION


def test_cinco_imitaciones_en_ventana_tambien_crean_tradicion() -> None:
    grafo = _grafo_con_guijarro()
    for tick in range(10, 15):
        grafo.registrar_uso("guijarro", usuario=2, es_conformista=True, tick=tick)

    assert len(grafo.imitadores["guijarro"]) == 1
    assert grafo.imitaciones_en_ventana("guijarro", tick=15, ventana=600) == 5
    assert tradiciones.evaluar(grafo, tick=15) is not None


def test_cinco_imitaciones_fuera_de_ventana_no_bastan() -> None:
    grafo = _grafo_con_guijarro()
    for tick in (0, 1000, 2000, 3000, 4000):
        grafo.registrar_uso("guijarro", usuario=2, es_conformista=True, tick=tick)

    assert grafo.imitaciones_en_ventana("guijarro", tick=5000, ventana=600) == 0
    assert tradiciones.evaluar(grafo, tick=5000) is None


def test_sin_imitacion_real_no_nace_ninguna_tradicion() -> None:
    grafo = _grafo_con_guijarro()
    # Usos de divergentes: no son imitación, por mucho que repitan.
    for _ in range(5):
        grafo.registrar_uso("guijarro", usuario=2, es_conformista=False, tick=10)

    assert tradiciones.evaluar(grafo, tick=20) is None
    assert grafo.nodos_por_origen()["interaccion"] == 0


def test_una_poblacion_sin_conformistas_no_crea_tradiciones() -> None:
    mundo = modulo_mundo.crear(seed=SEMILLA, individuos=12, config=SimConfig(seed=SEMILLA))
    for individuo in mundo.individuos:
        individuo.genoma = replace(individuo.genoma, divergencia=0.9)

    simulacion = _correr(mundo, ticks=600)

    assert simulacion.resumen()["imitaciones"] == 0
    assert simulacion.tradiciones == 0
    assert simulacion.resumen()["nodos_por_origen"]["interaccion"] == 0


def test_la_tradicion_sigue_activa_aunque_muera_su_autor() -> None:
    grafo = _grafo_con_guijarro()
    for usuario in (2, 3, 4):
        grafo.registrar_uso("guijarro", usuario=usuario, es_conformista=True, tick=10)
    nodo = tradiciones.evaluar(grafo, tick=20)
    assert nodo is not None

    # El autor era el último imitador; su muerte no toca el grafo: el nodo es
    # de la tribu. Solo lo apaga que el grupo deje de imitarlo.
    autor = Individuo(
        id=nodo.autor,
        sexo="m",
        genoma=Genoma(),
        necesidades=Necesidades(),
        x=0.0,
        y=0.0,
    )
    mundo = Mundo(
        ancho=6,
        alto=6,
        tiles=[[TipoTile.HIERBA for _ in range(6)] for _ in range(6)],
        recursos=[],
        individuos=[autor],
        azar=random.Random(0),
    )
    mundo.individuos.remove(autor)

    assert grafo.activo(nodo.id)
    assert grafo.nodos[nodo.id] is nodo


def test_e2e_sin_llm_crea_un_nodo_de_interaccion_con_semilla_fija() -> None:
    simulacion = run(ticks=1200, seed=SEMILLA, headless=True)

    resumen = simulacion.resumen()
    assert resumen["nodos_por_origen"]["interaccion"] >= 1
    assert resumen["tradiciones"] >= 1
    assert resumen["nivel_max"] == 2
    assert resumen["nodos_por_origen"]["llm"] == 0
    nodos = [nodo for nodo in resumen["nodos"] if nodo["origen"] == "interaccion"]
    assert nodos
    assert all(nodo["id"].startswith("tradicion_") for nodo in nodos)


def test_dos_procesos_crean_la_misma_tradicion() -> None:
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
        "1200",
    ]

    primera = subprocess.run(comando, capture_output=True, text=True, check=True)
    segunda = subprocess.run(comando, capture_output=True, text=True, check=True)

    assert primera.stdout == segunda.stdout
    assert json.loads(primera.stdout)["nodos_por_origen"]["interaccion"] >= 1


def test_report_culture_json_muestra_nivel_y_origenes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["report", "culture", "--json"]) == 0

    datos = json.loads(capsys.readouterr().out)
    assert datos["seed"] == 42
    assert datos["ticks"] == 600
    assert datos["crisis"] is False
    assert datos["nivel_max"] >= 2
    assert datos["nodos_por_origen"]["interaccion"] >= 1


def test_report_culture_refleja_seed_ticks_y_crisis(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["report", "culture", "--json", "--seed", "7", "--ticks", "900", "--crisis"]) == 0

    datos = json.loads(capsys.readouterr().out)
    assert datos["seed"] == 7
    assert datos["ticks"] == 900
    assert datos["crisis"] is True
