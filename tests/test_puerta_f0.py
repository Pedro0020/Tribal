"""Puerta F0->F1: nacimientos, agolpamiento junto al agua, huida en manada y herencia."""

from __future__ import annotations

import json
import math
import random
import subprocess
import sys
from typing import Literal

import pytest

from tribal.cli import main
from tribal.config import SimConfig
from tribal.core import mundo as modulo_mundo
from tribal.core.modelos import (
    LONGEVIDAD_TICKS,
    Depredador,
    Genoma,
    Individuo,
    Mundo,
    Necesidades,
    TipoTile,
)
from tribal.sim import MUTACION, Simulacion, run


def _mundo(
    individuos: list[Individuo],
    depredadores: list[Depredador] | None = None,
    ancho: int = 20,
    alto: int = 12,
) -> Mundo:
    tiles = [[TipoTile.HIERBA for _ in range(ancho)] for _ in range(alto)]
    return Mundo(
        ancho=ancho,
        alto=alto,
        tiles=tiles,
        recursos=[],
        individuos=individuos,
        azar=random.Random(0),
        depredadores=[] if depredadores is None else depredadores,
    )


def _individuo(
    id_: int,
    sexo: Literal["m", "f"],
    x: float = 5.0,
    y: float = 5.0,
    genoma: Genoma | None = None,
    edad: int = 300,
) -> Individuo:
    return Individuo(
        id=id_,
        sexo=sexo,
        genoma=genoma or Genoma(),
        necesidades=Necesidades(energia=100.0),
        x=x,
        y=y,
        edad=edad,
    )


def test_con_recursos_y_parejas_hay_nacimientos() -> None:
    simulacion = run(ticks=1500, seed=42, headless=True)

    assert simulacion.nacimientos > 0
    assert simulacion.poblacion > simulacion.poblacion_inicial


def test_sin_parejas_no_hay_nacimientos() -> None:
    mundo = modulo_mundo.crear(seed=42, individuos=12)
    for individuo in mundo.individuos:
        individuo.sexo = "m"

    simulacion = Simulacion(mundo)
    for _ in range(1500):
        simulacion.step()

    assert simulacion.nacimientos == 0


def test_agolpamiento_junto_al_agua() -> None:
    simulacion = Simulacion(modulo_mundo.crear(seed=2, individuos=12))

    for _ in range(3000):
        simulacion.step()

    # En algún tick, al menos la mitad de la tribu coincidió junto a un lago.
    assert simulacion.agrupamiento_max >= simulacion.poblacion // 2


def test_huida_en_manada_ante_el_depredador() -> None:
    individuos = [
        _individuo(id_=id_, sexo="m" if id_ % 2 else "f", x=float(id_), y=6.0, edad=0)
        for id_ in range(1, 6)
    ]
    depredador = Depredador(x=0.0, y=6.0)
    mundo = _mundo(individuos, [depredador])
    simulacion = Simulacion(mundo)

    def distancias() -> dict[int, float]:
        return {
            individuo.id: math.hypot(individuo.x - depredador.x, individuo.y - depredador.y)
            for individuo in individuos
        }

    antes = distancias()
    for _ in range(5):
        simulacion.step()
    medio = distancias()
    for _ in range(5):
        simulacion.step()
    despues = distancias()

    assert sum(1 for id_, valor in medio.items() if valor > antes[id_]) >= 3
    assert sum(1 for id_, valor in despues.items() if valor > medio[id_]) >= 3
    assert simulacion.huidas >= 3


def test_la_vejez_mata() -> None:
    viejo = _individuo(id_=1, sexo="m", edad=LONGEVIDAD_TICKS + 1)
    mundo = _mundo([viejo])
    simulacion = Simulacion(mundo)

    simulacion.step()

    assert simulacion.muertes == 1
    assert mundo.individuos == []


def test_el_genoma_del_hijo_hereda_de_los_dos_progenitores() -> None:
    madre = _individuo(
        id_=1,
        sexo="f",
        x=5.0,
        genoma=Genoma(velocidad=0.9, metabolismo=1.1, longevidad=0.95),
    )
    padre = _individuo(
        id_=2,
        sexo="m",
        x=6.0,
        genoma=Genoma(velocidad=1.1, metabolismo=1.3, longevidad=1.05),
    )
    mundo = _mundo([madre, padre])
    simulacion = Simulacion(mundo)

    simulacion.step()

    assert simulacion.nacimientos == 1
    hijo = mundo.individuos[-1]
    assert hijo.id == 3
    assert hijo.necesidades.energia == 80.0
    assert hijo.madurez > 0 and hijo.edad == 0
    for rasgo in ("velocidad", "metabolismo", "longevidad"):
        media = (getattr(madre.genoma, rasgo) + getattr(padre.genoma, rasgo)) / 2.0
        assert abs(getattr(hijo.genoma, rasgo) - media) <= media * MUTACION


def test_la_config_sin_depredadores_no_crea_ninguno() -> None:
    config = SimConfig(seed=42, individuos=12, depredadores=0)

    simulacion = run(ticks=30, seed=42, headless=True, config=config)

    assert simulacion.mundo.depredadores == []
    assert simulacion.resumen()["depredador"] == {"activos": 0, "ataques": 0, "muertes": 0}


def test_la_config_desactiva_los_depredadores() -> None:
    config = SimConfig(seed=42, individuos=12, depredadores=2, depredador_activo=False)

    simulacion = run(ticks=300, seed=42, headless=True, config=config)

    assert simulacion.mundo.depredadores == []
    assert simulacion.resumen()["depredador"] == {"activos": 0, "ataques": 0, "muertes": 0}


def _presa_acorralada(con_depredador: bool) -> Simulacion:
    """Presa sana en una isla de un tile rodeada de agua: no puede escapar."""
    ancho, alto = 12, 12
    tiles = [[TipoTile.HIERBA for _ in range(ancho)] for _ in range(alto)]
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            if (dx, dy) != (0, 0):
                tiles[5 + dy][5 + dx] = TipoTile.AGUA
    presa = _individuo(id_=1, sexo="m", x=5.5, y=5.5, edad=0)
    depredadores = [Depredador(x=5.9, y=5.5)] if con_depredador else []
    mundo = _mundo([presa], depredadores, ancho=ancho, alto=alto)
    mundo.tiles = tiles
    return Simulacion(mundo, SimConfig(seed=7, individuos=1, ancho=ancho, alto=alto))


def test_el_depredador_mata_a_una_presa_sana_acorralada() -> None:
    simulacion = _presa_acorralada(con_depredador=True)

    for _ in range(300):
        simulacion.step()

    assert simulacion.muertes == 1
    assert simulacion.mundo.individuos == []
    assert simulacion.resumen()["depredador"]["muertes"] > 0
    assert simulacion.muertes == simulacion.resumen()["depredador"]["muertes"]
    assert simulacion.resumen()["depredador"]["ataques"] >= 4


def test_la_misma_presa_lejos_del_depredador_sigue_viva() -> None:
    simulacion = _presa_acorralada(con_depredador=False)

    for _ in range(300):
        simulacion.step()

    assert simulacion.muertes == 0
    assert simulacion.poblacion == 1
    assert simulacion.resumen()["depredador"]["muertes"] == 0


def test_dos_procesos_dan_el_mismo_resumen_con_nacimientos() -> None:
    comando = [
        sys.executable,
        "-m",
        "tribal",
        "run",
        "--seed",
        "42",
        "--headless",
        "--json",
        "--ticks",
        "1200",
    ]

    primera = subprocess.run(comando, capture_output=True, text=True, check=True)
    segunda = subprocess.run(comando, capture_output=True, text=True, check=True)

    assert primera.stdout == segunda.stdout
    assert json.loads(primera.stdout)["nacimientos"] > 0


def test_el_json_del_cli_incluye_depredador_agrupamiento_y_huidas(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["run", "--headless", "--json", "--ticks", "60"]) == 0
    datos = json.loads(capsys.readouterr().out)

    assert {"depredador", "agrupamiento_max", "huidas"} <= set(datos)
    assert datos["depredador"]["activos"] == 1
