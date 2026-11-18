"""Motor de reglas sin Pygame: camino feliz, muerte, extinción y determinismo."""

from __future__ import annotations

import random
import subprocess
import sys

from tribal.agents import necesidades
from tribal.core import acciones
from tribal.core import mundo as modulo_mundo
from tribal.core.modelos import (
    Genoma,
    Individuo,
    Mundo,
    Necesidades,
    Recurso,
    TipoRecurso,
    TipoTile,
)
from tribal.sim import Simulacion


def _individuo(
    energia: float = 100.0, sed: float = 0.0, x: float = 2.0, y: float = 2.0
) -> Individuo:
    return Individuo(
        id=1,
        sexo="m",
        genoma=Genoma(),
        necesidades=Necesidades(energia=energia, sed=sed),
        x=x,
        y=y,
    )


def _mundo(recursos: list[Recurso], individuos: list[Individuo]) -> Mundo:
    tiles = [[TipoTile.HIERBA for _ in range(8)] for _ in range(8)]
    return Mundo(
        ancho=8,
        alto=8,
        tiles=tiles,
        recursos=recursos,
        individuos=individuos,
        azar=random.Random(0),
    )


def _agua(x: int = 2, y: int = 2, cantidad: int = 5) -> Recurso:
    return Recurso(
        id=1,
        tipo=TipoRecurso.AGUA,
        x=x,
        y=y,
        cantidad=cantidad,
        capacidad=40,
        regeneracion=10,
        alcance=3.0,
    )


def _bayas(x: int = 2, y: int = 2, cantidad: int = 2) -> Recurso:
    return Recurso(
        id=2,
        tipo=TipoRecurso.BAYAS,
        x=x,
        y=y,
        cantidad=cantidad,
        capacidad=4,
        regeneracion=420,
        alcance=1.5,
    )


def test_beber_sacia_la_sed_y_gasta_la_fuente() -> None:
    individuo = _individuo(sed=70.0)
    fuente = _agua()
    mundo = _mundo([fuente], [individuo])

    assert acciones.beber(individuo, mundo) is True
    assert individuo.necesidades.sed == 0.0
    assert fuente.cantidad == 4


def test_comer_recupera_energia_y_gasta_la_comida() -> None:
    individuo = _individuo(energia=40.0)
    bayas = _bayas()
    mundo = _mundo([bayas], [individuo])

    assert acciones.comer(individuo, mundo) is True
    assert individuo.necesidades.energia == 80.0
    assert bayas.cantidad == 1


def test_descansar_recupera_energia() -> None:
    individuo = _individuo(energia=50.0)
    mundo = _mundo([], [individuo])

    assert acciones.descansar(individuo, mundo) is True
    assert individuo.necesidades.energia > 50.0


def test_beber_fuera_de_alcance_no_toca_el_estado() -> None:
    individuo = _individuo(sed=90.0, x=0.0, y=0.0)
    fuente = _agua(x=7, y=7)
    mundo = _mundo([fuente], [individuo])

    assert acciones.beber(individuo, mundo) is False
    assert individuo.necesidades.sed == 90.0
    assert fuente.cantidad == 5


def test_moverse_acerca_al_destino() -> None:
    individuo = _individuo(x=1.0, y=1.0)
    mundo = _mundo([], [individuo])

    assert acciones.moverse(individuo, mundo, (5.0, 1.0)) is True
    assert individuo.x > 1.0
    assert individuo.y == 1.0


def test_las_necesidades_evolucionan_por_tick() -> None:
    individuo = _individuo(energia=80.0, sed=10.0)
    necesidades.evolucionar(individuo.necesidades, individuo.genoma)

    assert individuo.necesidades.sed > 10.0
    assert individuo.necesidades.energia < 80.0
    assert individuo.necesidades.salud == 100.0


def test_la_tribu_sobrevive_en_un_mundo_con_recursos() -> None:
    simulacion = Simulacion(modulo_mundo.crear(seed=42, individuos=12))

    for _ in range(1200):
        simulacion.step()

    resumen = simulacion.resumen()
    assert resumen["muertes"] == 0
    assert resumen["poblacion_final"] == 12
    assert resumen["individuos_movidos"] == 12


def test_sin_agua_el_individuo_muere_de_sed() -> None:
    mundo = modulo_mundo.crear(seed=3, individuos=1)
    mundo.recursos = [r for r in mundo.recursos if r.tipo != TipoRecurso.AGUA]
    individuo = mundo.individuos[0]
    simulacion = Simulacion(mundo)

    pasos = 0
    while simulacion.muertes == 0 and pasos < 3000:
        simulacion.step()
        pasos += 1

    assert simulacion.muertes == 1
    assert pasos < 3000
    assert individuo.necesidades.sed == 100.0
    assert simulacion.resumen()["poblacion_final"] == 0


def test_sin_recursos_la_tribu_se_extingue() -> None:
    mundo = modulo_mundo.crear(seed=5, individuos=8)
    mundo.recursos = []
    simulacion = Simulacion(mundo)
    inicial = len(mundo.individuos)

    for _ in range(1500):
        simulacion.step()

    resumen = simulacion.resumen()
    assert resumen["poblacion_final"] == 0
    assert resumen["muertes"] == inicial


def test_misma_semilla_y_ticks_dan_el_mismo_resumen() -> None:
    def correr(seed: int, ticks: int) -> dict[str, int | float]:
        simulacion = Simulacion(modulo_mundo.crear(seed, individuos=10))
        for _ in range(ticks):
            simulacion.step()
        return simulacion.resumen()

    assert correr(11, 600) == correr(11, 600)


def test_importar_el_motor_no_carga_pygame() -> None:
    salida = subprocess.run(
        [
            sys.executable,
            "-c",
            "import tribal.core.mundo, tribal.sim, sys; print('pygame' in sys.modules)",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert salida.stdout.strip() == "False"
