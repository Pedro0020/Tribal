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
from tribal.core import acciones, recursos
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
from tribal.culture import beneficios
from tribal.culture.arbol import ARBOL
from tribal.culture.combinaciones import COMBINACIONES
from tribal.culture.grafo import Grafo, PrerequisitoFaltante
from tribal.sim import (
    ENERGIA_CRIA,
    UMBRAL_REPRODUCCION,
    Simulacion,
    crear,
    run,
)

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
    assert all(nodo["origen"] in ("arbol", "interaccion") for nodo in resumen["nodos"])
    # La tradición sí puede nacer en calma: es imitación, no experimento.
    assert resumen["nodos_por_origen"]["interaccion"] >= 1


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


def _sin_habilidad(id_: int, divergencia: float = 0.5) -> Individuo:
    return Individuo(
        id=id_,
        sexo="m",
        genoma=Genoma(divergencia=divergencia),
        necesidades=Necesidades(energia=40.0),
        x=1.0,
        y=1.0,
        habilidades=Habilidades(),
    )


def _energia_tras_comer(individuo: Individuo, grafo: Grafo) -> float:
    mundo = _mundo_de_dos(individuo)
    # Escasez (2 de 8): la utilidad de la técnica solo paga cuando falta el
    # recurso, así que en abundancia este mismo test daría 80 para los dos.
    mundo.recursos[0].cantidad = 2
    estado = beneficios.situacion(mundo)
    utilidades_tick = beneficios.utilidades(grafo, mundo, estado)
    efecto = beneficios.conocidos(grafo, individuo.habilidades.conocidas, utilidades_tick)
    assert acciones.comer(individuo, mundo, bonus_bayas=efecto.bayas, bonus_caza=efecto.caza)
    return individuo.necesidades.energia


def test_el_temperamento_no_cambia_la_ganancia_de_comer() -> None:
    """Mismo bocado con las mismas habilidades: el rasgo no aporta ni quita."""
    conformista = _sin_habilidad(1, divergencia=0.1)
    divergente = _sin_habilidad(2, divergencia=0.9)

    assert _energia_tras_comer(conformista, Grafo()) == pytest.approx(80.0)
    assert _energia_tras_comer(divergente, Grafo()) == pytest.approx(80.0)


def test_el_temperamento_no_cambia_la_sed_en_crisis() -> None:
    def sed(divergencia: float) -> float:
        individuo = _sin_habilidad(1, divergencia=divergencia)
        individuo.necesidades = Necesidades(energia=100.0, sed=0.0)
        mundo = _mundo_de_dos(individuo)
        mundo.recursos = []
        simulacion = Simulacion(mundo, SimConfig(seed=0, individuos=1, crisis=True))
        simulacion.step()
        return individuo.necesidades.sed

    assert sed(0.1) == pytest.approx(sed(0.9))
    assert sed(0.1) > 0.0


def test_el_umbral_de_reproduccion_es_el_mismo_en_calma_y_crisis() -> None:
    calma = crear(1, 12)
    crisis = crear(1, 12, config=SimConfig(seed=1, individuos=12, crisis=True))
    individuo = calma.mundo.individuos[0]
    individuo.edad = individuo.madurez
    individuo.cooldown_reproduccion = 0

    assert crisis._umbral_reproduccion() >= calma._umbral_reproduccion()

    individuo.necesidades.energia = UMBRAL_REPRODUCCION + 1
    assert calma._puede_reproducir(individuo) is True
    assert crisis._puede_reproducir(individuo) is True

    individuo.necesidades.energia = UMBRAL_REPRODUCCION - 1
    assert calma._puede_reproducir(individuo) is False
    assert crisis._puede_reproducir(individuo) is False


def test_el_genoma_no_se_edita_en_runtime() -> None:
    assert not hasattr(Simulacion, "_plasmar_divergencia")
    assert not hasattr(Simulacion, "_moldear_divergencia")


def test_la_cria_no_inyecta_energia_neta() -> None:
    simulacion = crear(1, 12)
    madre, padre = simulacion.mundo.individuos[:2]
    madre.necesidades.energia = 100.0
    padre.necesidades.energia = 100.0
    antes = sum(individuo.necesidades.energia for individuo in simulacion.mundo.individuos)

    simulacion._nacer(madre, padre)

    hijo = simulacion.mundo.individuos[-1]
    despues = sum(individuo.necesidades.energia for individuo in simulacion.mundo.individuos)
    assert ENERGIA_CRIA < UMBRAL_REPRODUCCION
    assert hijo.necesidades.energia == ENERGIA_CRIA
    assert despues == pytest.approx(antes), "el nacimiento no crea energía"


def test_la_crisis_baja_la_capacidad_de_carga_del_agua_y_las_bayas() -> None:
    mundo = _mundo_de_dos()
    bayas = Recurso(
        id=1,
        tipo=TipoRecurso.BAYAS,
        x=1,
        y=1,
        cantidad=4,
        capacidad=4,
        regeneracion=420,
        alcance=1.5,
    )
    agua = Recurso(
        id=2,
        tipo=TipoRecurso.AGUA,
        x=2,
        y=2,
        cantidad=40,
        capacidad=40,
        regeneracion=10,
        alcance=3.0,
    )
    mundo.recursos = [bayas, agua]
    mundo.tick = 10

    recursos.regenerar(mundo, 1.0)
    assert (bayas.cantidad, agua.cantidad) == (4, 40)

    recursos.regenerar(mundo, 2.0)
    assert (bayas.cantidad, agua.cantidad) == (2, 20)


def test_el_bonus_de_una_tecnica_es_igual_para_quien_la_sabe() -> None:
    grafo = _grafo_con("raedera")
    conformista = _sin_habilidad(1, divergencia=0.1)
    divergente = _sin_habilidad(2, divergencia=0.9)
    conformista.habilidades = Habilidades({"fabricar"})
    divergente.habilidades = Habilidades({"fabricar"})

    # Escasez 0.75 y un portador: 1 + 0.25 · 0.75 / 1.1 ≈ 1.1705.
    esperado = 40.0 + 40.0 * (1.0 + 0.25 * 0.75 / 1.1)
    assert _energia_tras_comer(conformista, grafo) == pytest.approx(esperado)
    assert _energia_tras_comer(divergente, grafo) == pytest.approx(esperado)
    mundo = _mundo_de_dos()
    mundo.recursos[0].cantidad = 2
    estado = beneficios.situacion(mundo)
    assert beneficios.utilidad("raedera", estado, portadores=1) == pytest.approx(
        1.0 + 0.25 * 0.75 / 1.1
    )


def test_bajo_escasez_quien_descubrio_la_tecnica_rinde_mas() -> None:
    grafo = _grafo_con("raedera")
    sabio = _sin_habilidad(1, divergencia=0.9)
    ignorante = _sin_habilidad(2, divergencia=0.9)
    sabio.habilidades = Habilidades({"fabricar"})

    energia_sabio = _energia_tras_comer(sabio, grafo)
    energia_ignorante = _energia_tras_comer(ignorante, grafo)

    assert energia_sabio > energia_ignorante
    assert (energia_sabio, energia_ignorante) == (
        pytest.approx(86.818, abs=1e-2),
        pytest.approx(80.0),
    )


def test_un_divergente_que_no_descubre_nada_rinde_como_un_conformista() -> None:
    grafo = _grafo_con("raedera")
    divergente = _sin_habilidad(1, divergencia=0.9)
    conformista = _sin_habilidad(2, divergencia=0.1)

    assert _energia_tras_comer(divergente, grafo) == _energia_tras_comer(conformista, grafo)


def test_el_divergente_que_descubre_aprende_la_habilidad(monkeypatch: pytest.MonkeyPatch) -> None:
    individuo = _sin_habilidad(1, divergencia=0.9)
    individuo.necesidades = Necesidades(energia=80.0, sed=0.0)
    mundo = _mundo_de_dos(individuo)
    simulacion = Simulacion(mundo, SimConfig(seed=0, individuos=1, crisis=True))
    simulacion.grafo = _grafo_con()
    simulacion.grafo.descubrir("guijarro", autor=1, tick=1)
    simulacion.grafo.descubrir("lasca", autor=1, tick=2)
    simulacion.grafo.descubrir("bifaz", autor=1, tick=3)
    monkeypatch.setattr("tribal.sim.PROB_INTENTO_DIVERGENTE", 100.0)
    monkeypatch.setattr("tribal.sim.PROB_COMPLETAR_COMBINACION", 1.0)

    assert simulacion._intentar_combinacion(individuo) is True
    assert "raedera" in simulacion.grafo.nodos
    assert individuo.habilidades.sabe("fabricar")


def test_la_crisis_no_es_el_regimen_favorable() -> None:
    """La crisis no puede ser el régimen favorable: población y extinciones.

    Se mide con el criterio de la puerta sobre 5 semillas (el proxy de
    nacimientos de una sola semilla es demasiado ruidoso cuando la calma ya no
    migra). Umbral: crisis ≤ calma en ≥3/5 y no más extinciones en crisis.
    """
    from tribal.gate_f1 import medir_barrido

    barrido = medir_barrido((1, 2, 3, 4, 5), ticks=8000)
    filas = barrido.filas

    assert sum(1 for fila in filas if fila.crisis.poblacion <= fila.calma.poblacion) >= 3
    assert barrido.extinciones_crisis <= barrido.extinciones_calma
