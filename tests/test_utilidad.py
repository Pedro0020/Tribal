"""UTIL-001: la utilidad de una combinación depende del estado del mundo.

Contratos:

1. La utilidad sube con la escasez del recurso que explota el nodo y baja con
   el número de portadores; con el recurso lleno vale 1.0 (sin premio).
2. Con la misma semilla, en calma (recurso abundante) tener el invento no
   mueve la energía; en escasez la mueve de forma clara.
3. El resumen publica `utilidad_media` por nodo y el estado que la modula
   (`escasez` por recurso y `estacion`).
4. El temperamento no entra en la cuenta: dos individuos con la misma
   habilidad rinden igual, con divergencia 0.1 o 0.9.
"""

from __future__ import annotations

import random
from typing import Any

import pytest

from tribal.config import SimConfig
from tribal.core import acciones
from tribal.core.genoma import Genoma
from tribal.core.habilidades import Habilidades
from tribal.core.modelos import (
    Individuo,
    Mundo,
    Necesidades,
    Recurso,
    TipoRecurso,
    TipoTile,
)
from tribal.culture import beneficios
from tribal.culture.arbol import ARBOL
from tribal.culture.combinaciones import COMBINACIONES
from tribal.culture.grafo import Grafo
from tribal.sim import Simulacion

#: Escenario controlado: un adulto junto a agua y bayas, sin depredadores.
#: El agua nunca escasea; solo cambia la escasez de las bayas (`ESCASEZ`).
TICKS = 3000
ENERGIA_INICIAL = 80.0
#: Escasez de las bayas en el brazo de crisis: 25 de 100 en la reserva.
ESCASEZ_CRISIS = 0.75


def _grafo_con(*nodo_ids: str) -> Grafo:
    """Grafo con esos nodos activos y todos sus prerrequisitos."""
    grafo = Grafo()

    def activar(nodo_id: str) -> None:
        if grafo.activo(nodo_id):
            return
        plantilla = ARBOL.get(nodo_id) or COMBINACIONES[nodo_id]
        for requisito in plantilla.requisitos:
            activar(requisito)
        grafo.descubrir(nodo_id, autor=1, tick=1)

    for nodo_id in nodo_ids:
        activar(nodo_id)
    return grafo


def _mundo_controlado(
    *, seed: int, escasez: float, habilidades: set[str]
) -> tuple[Mundo, Individuo]:
    """Doce por doce de hierba, agua de sobra y bayas con la escasez pedida."""
    tiles = [[TipoTile.HIERBA for _ in range(12)] for _ in range(12)]
    agua = Recurso(
        id=1,
        tipo=TipoRecurso.AGUA,
        x=5,
        y=5,
        cantidad=1000,
        capacidad=1000,
        regeneracion=1,
        alcance=3.0,
    )
    bayas = Recurso(
        id=2,
        tipo=TipoRecurso.BAYAS,
        x=6,
        y=6,
        cantidad=round(100 * (1.0 - escasez)),
        capacidad=100,
        # Abundante: se rellena cada tick y nunca baja del tope. Escaso: no se
        # regenera en la corrida, así que la escasez es la que fija el test.
        regeneracion=1 if escasez == 0.0 else 10**9,
        alcance=1.5,
    )
    individuo = Individuo(
        id=1,
        sexo="m",
        genoma=Genoma(divergencia=0.5),
        necesidades=Necesidades(energia=ENERGIA_INICIAL, sed=0.0),
        x=5.5,
        y=5.5,
        habilidades=Habilidades(habilidades),
    )
    mundo = Mundo(
        ancho=12,
        alto=12,
        tiles=tiles,
        recursos=[agua, bayas],
        individuos=[individuo],
        azar=random.Random(seed),
    )
    return mundo, individuo


def _corrida(
    seed: int, *, escasez: float, con_nodo: bool, ticks: int = TICKS
) -> tuple[float, dict[str, Any]]:
    """Media de energía de toda la corrida y resumen final.

    La media importa más que la energía final: al comer, la energía sube de
    golpe y el último tick puede caer en cualquier punto del diente de sierra.
    """
    mundo, individuo = _mundo_controlado(
        seed=seed, escasez=escasez, habilidades={"fabricar"} if con_nodo else set()
    )
    simulacion = Simulacion(mundo, SimConfig(seed=seed, individuos=1, depredadores=0))
    if con_nodo:
        simulacion.grafo = _grafo_con("raedera")
    suma = 0.0
    for _ in range(ticks):
        simulacion.step()
        suma += individuo.necesidades.energia
    return suma / ticks, simulacion.resumen()


# --- 1. Utilidad situacional ---------------------------------------------


def test_la_utilidad_crece_con_la_escasez_y_baja_con_los_portadores() -> None:
    lleno = beneficios.Situacion(escasez=dict.fromkeys(TipoRecurso, 0.0))
    agotado = beneficios.Situacion(escasez=dict.fromkeys(TipoRecurso, 1.0))

    assert beneficios.utilidad("raedera", lleno, portadores=1) == pytest.approx(1.0)
    assert beneficios.utilidad("raedera", agotado, portadores=1) == pytest.approx(1.0 + 0.25 / 1.1)

    # La ventaja es de oportunidad: cuantos más saben la técnica, menos separa.
    solo_uno = beneficios.utilidad("raedera", agotado, portadores=1)
    diez = beneficios.utilidad("raedera", agotado, portadores=10)
    todos = beneficios.utilidad("raedera", agotado, portadores=20)
    assert solo_uno > diez > todos > 1.0

    # Un efecto defensivo también se apaga cuando el recurso sobra.
    assert beneficios.utilidad("turnos_de_vigilia", lleno, portadores=1) == pytest.approx(1.0)
    assert beneficios.utilidad("turnos_de_vigilia", agotado, portadores=1) == pytest.approx(
        1.0 - 0.5 / 1.1
    )


def test_la_escasez_es_la_fraccion_que_falta_sobre_la_capacidad() -> None:
    mundo, _ = _mundo_controlado(seed=1, escasez=ESCASEZ_CRISIS, habilidades=set())
    assert beneficios.escasez_de(mundo, TipoRecurso.BAYAS) == pytest.approx(0.75)
    # Sin fuentes de caza no hay oportunidad que explotar: escasez 0.
    assert beneficios.escasez_de(mundo, TipoRecurso.CAZA) == 0.0


# --- 2. Calma frente a crisis, misma semilla ------------------------------


def test_en_calma_el_invento_no_mueve_la_energia_y_en_escasez_si() -> None:
    """Mismo escenario y misma semilla: solo cambia la reserva de bayas.

    Umbral justificado: en calma la utilidad vale exactamente 1.0, así que la
    diferencia tiene que ser 0 (se admite 0.1 por redondeo de la media); en
    crisis la media medida sube ~3.4 puntos y la más floja de las cinco
    semillas sube ~1.9, así que exigir 0.5 por semilla y 1.5 de media deja
    margen sin volver el test frágil.
    """
    semillas = range(1, 6)

    def diferencia(seed: int, escasez: float) -> float:
        sin_nodo, _ = _corrida(seed, escasez=escasez, con_nodo=False)
        con_nodo, _ = _corrida(seed, escasez=escasez, con_nodo=True)
        return con_nodo - sin_nodo

    calma = [diferencia(seed, 0.0) for seed in semillas]
    crisis = [diferencia(seed, ESCASEZ_CRISIS) for seed in semillas]
    media_calma = sum(calma) / len(calma)
    media_crisis = sum(crisis) / len(crisis)

    assert all(abs(d) < 0.1 for d in calma), f"en calma el invento movió la energía: {calma}"
    assert abs(media_calma) < 0.1, f"en calma el invento movió la media: {media_calma:.3f}"
    assert all(d > 0.5 for d in crisis), f"alguna semilla no premia la técnica: {crisis}"
    assert media_crisis > 1.5, f"en crisis la ventaja es demasiado pequeña: {media_crisis:.2f}"


# --- 3. Telemetría en el resumen ------------------------------------------


def test_el_resumen_publica_utilidad_media_y_el_estado_que_la_modula() -> None:
    _, calma = _corrida(1, escasez=0.0, con_nodo=True, ticks=200)
    _, crisis = _corrida(1, escasez=ESCASEZ_CRISIS, con_nodo=True, ticks=200)

    assert calma["utilidad_media"]["raedera"] == pytest.approx(1.0)
    # 200 ticks: nadie come todavía, así que la escasez no se mueve.
    assert crisis["utilidad_media"]["raedera"] == pytest.approx(1.0 + 0.25 * 0.75 / 1.1, abs=1e-3)
    assert crisis["escasez"] == {
        "agua": pytest.approx(0.0),
        "bayas": pytest.approx(0.75),
        "caza": pytest.approx(0.0),
    }
    assert crisis["estacion"] is None, "la estación llega en AMB-001; hoy es un gancho vacío"


# --- 4. El temperamento no entra en la utilidad ---------------------------


def test_la_utilidad_no_depende_del_temperamento() -> None:
    """Misma habilidad y mismo mundo: divergencia 0.1 y 0.9 rinden igual."""

    def tras_comer(divergencia: float) -> tuple[float, float]:
        mundo, individuo = _mundo_controlado(
            seed=1, escasez=ESCASEZ_CRISIS, habilidades={"fabricar"}
        )
        individuo.genoma = Genoma(divergencia=divergencia)
        individuo.necesidades.energia = 40.0
        grafo = _grafo_con("raedera")
        estado = beneficios.situacion(mundo)
        utilidades_tick = beneficios.utilidades(grafo, mundo, estado)
        efecto = beneficios.conocidos(grafo, individuo.habilidades.conocidas, utilidades_tick)
        assert acciones.comer(individuo, mundo, bonus_bayas=efecto.bayas)
        return individuo.necesidades.energia, efecto.bayas

    conformista = tras_comer(0.1)
    divergente = tras_comer(0.9)

    assert conformista == pytest.approx(divergente)
    assert conformista[1] > 1.0, "el test no mediría nada sin la utilidad aplicada"
