"""Prácticas ociosas (CONNECT-001): cada rama avanza con lo que la tribu hace."""

from __future__ import annotations

import random
import subprocess
import sys
from collections.abc import Callable

import pytest

from tribal.agents import instinto
from tribal.config import SimConfig
from tribal.core import acciones
from tribal.core.genoma import Genoma
from tribal.core.habilidades import Habilidades
from tribal.core.modelos import Individuo, Mundo, Necesidades, Recurso, TipoRecurso, TipoTile
from tribal.culture.arbol import RAMAS
from tribal.sim import PRACTICAS, Simulacion, run

SEMILLA = 42
ANCHO = 8
ALTO = 8
#: Verbos del tramo ocioso; ninguno puede elegirse con una urgencia pendiente.
OCIOSOS = frozenset(PRACTICAS) | {"cuidar"}


def _mundo(
    individuos: list[Individuo],
    *,
    tiles: list[list[TipoTile]] | None = None,
    recursos: list[Recurso] | None = None,
    seed: int = 0,
) -> Mundo:
    return Mundo(
        ancho=ANCHO,
        alto=ALTO,
        tiles=tiles or [[TipoTile.HIERBA for _ in range(ANCHO)] for _ in range(ALTO)],
        recursos=[] if recursos is None else recursos,
        individuos=individuos,
        azar=random.Random(seed),
    )


def _individuo(
    id_: int,
    x: float = 2.5,
    y: float = 2.5,
    *,
    energia: float = 100.0,
    habilidades: set[str] | None = None,
    edad: int = 300,
) -> Individuo:
    return Individuo(
        id=id_,
        sexo="m",
        genoma=Genoma(),
        necesidades=Necesidades(energia=energia),
        x=x,
        y=y,
        edad=edad,
        habilidades=Habilidades(habilidades or set()),
    )


def _tiles_con(tipo: TipoTile, x: int = 1, y: int = 1) -> list[list[TipoTile]]:
    tiles = [[TipoTile.HIERBA for _ in range(ANCHO)] for _ in range(ALTO)]
    tiles[y][x] = tipo
    return tiles


def test_practicas_cubre_las_cinco_ramas_del_arbol() -> None:
    assert {practica.rama for practica in PRACTICAS.values()} == set(RAMAS)


@pytest.mark.parametrize(
    ("accion", "rama", "nodo", "tiles", "id_", "habilidades"),
    [
        ("tallar", "litica", "guijarro", _tiles_con(TipoTile.BOSQUE), 3, None),
        ("frotar_madera", "fuego", "observar_rayo", _tiles_con(TipoTile.BOSQUE), 1, None),
        ("pintar", "simbolico", "arte_rupestre", _tiles_con(TipoTile.AGUA), 1, None),
        ("hablar", "lenguaje", "gestos", None, 1, None),
        ("ensenar", "roles", "cazador", None, 1, {"recolectar", "fuego"}),
    ],
)
def test_una_practica_por_rama_descubre_su_rama(
    accion: str,
    rama: str,
    nodo: str,
    tiles: list[list[TipoTile]] | None,
    id_: int,
    habilidades: set[str] | None,
) -> None:
    protagonista = _individuo(
        id_,
        1.5 if tiles is not None else 2.5,
        1.5 if tiles is not None else 2.5,
        habilidades=habilidades,
    )
    individuos = [protagonista]
    if accion == "hablar":
        individuos.append(_individuo(2, 3.5))
    if accion == "ensenar":
        individuos.append(_individuo(2, 3.5, habilidades={"recolectar"}))
    simulacion = Simulacion(_mundo(individuos, tiles=tiles, seed=1))

    simulacion.step()

    creado = simulacion.grafo.nodos.get(nodo)
    assert creado is not None, f"{accion} no descubrió {nodo}"
    assert (creado.rama, creado.origen) == (rama, "arbol")


@pytest.mark.parametrize(
    ("tick", "esperada"),
    [(0, "tallar"), (1, "frotar_madera"), (2, "pintar")],
)
def test_el_instinto_elige_la_practica_del_bosque_en_ocio(tick: int, esperada: str) -> None:
    individuo = _individuo(1, 1.5, 1.5)
    mundo = _mundo([individuo], tiles=_tiles_con(TipoTile.BOSQUE))
    mundo.tick = tick

    assert instinto.elegir(individuo, mundo).nombre == esperada


def test_el_instinto_elige_hablar_y_ensenar_en_ocio() -> None:
    hablador = _individuo(1)
    oyente = _individuo(2, 3.5)
    assert instinto.elegir(hablador, _mundo([hablador, oyente])).nombre == "hablar"

    maestro = _individuo(1, habilidades={"recolectar", "fuego"})
    aprendiz = _individuo(2, 3.5, habilidades={"recolectar"})
    assert instinto.elegir(maestro, _mundo([maestro, aprendiz])).nombre == "ensenar"


@pytest.mark.parametrize("tick", [0, 1, 2])
def test_el_instinto_no_practica_cuando_hay_urgencia(tick: int) -> None:
    individuo = _individuo(1, 1.5, 1.5, energia=40.0)
    mundo = _mundo([individuo], tiles=_tiles_con(TipoTile.BOSQUE))
    mundo.tick = tick

    accion = instinto.elegir(individuo, mundo)

    assert accion.nombre not in OCIOSOS


def test_sin_la_habilidad_de_comer_no_avanza_la_litica() -> None:
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
    individuo = _individuo(1, 1.0, 1.0, energia=40.0)
    simulacion = Simulacion(_mundo([individuo], recursos=[bayas]))

    simulacion.step()

    assert bayas.cantidad == 3, "comió: el tick ocurrió"
    assert not any(nodo.rama == "litica" for nodo in simulacion.grafo.nodos.values())


def test_sin_la_condicion_no_avanza_la_rama() -> None:
    # Lejos del bosque no se talla, no se frota y no se pinta.
    solitario = _individuo(1)
    simulacion = Simulacion(_mundo([solitario]))
    simulacion.step()
    assert not any(
        nodo.rama in ("litica", "fuego", "simbolico") for nodo in simulacion.grafo.nodos.values()
    )

    # Sin otro individuo a distancia social no se habla y no hay lenguaje.
    assert not any(nodo.rama == "lenguaje" for nodo in simulacion.grafo.nodos.values())

    # Sin aprendiz ni herido no se cuida y no hay roles.
    assert not any(nodo.rama == "roles" for nodo in simulacion.grafo.nodos.values())


def test_un_nodo_combinacion_distinto_de_raedera_es_alcanzable_en_partida() -> None:
    simulacion = run(
        ticks=600,
        seed=SEMILLA,
        headless=True,
        config=SimConfig(seed=SEMILLA, individuos=12, crisis=True),
    )

    combinaciones = {
        nodo.id for nodo in simulacion.grafo.nodos.values() if nodo.origen == "combinacion"
    }
    assert "canto_ritual" in combinaciones
    assert combinaciones - {"raedera"}, "solo apareció la raedera"
    # El cruce existe porque las prácticas nuevas hicieron avanzar lenguaje y símbolo.
    assert simulacion.grafo.activo("proto_palabras")
    assert simulacion.grafo.activo("ritual")


def test_dos_procesos_dan_la_misma_salida_con_practicas() -> None:
    comando = [
        sys.executable,
        "-m",
        "tribal",
        "report",
        "culture",
        "--json",
        "--crisis",
        "--seed",
        str(SEMILLA),
        "--ticks",
        "600",
    ]

    primera = subprocess.run(comando, capture_output=True, text=True, check=True)
    segunda = subprocess.run(comando, capture_output=True, text=True, check=True)

    assert primera.stdout == segunda.stdout
    assert '"canto_ritual"' in primera.stdout


def test_hablar_puede_transmitir_una_habilidad() -> None:
    hablador = _individuo(1, habilidades={"recolectar", "cazar"})
    oyente = _individuo(2, 3.5, habilidades={"recolectar"})
    mundo = _mundo([hablador, oyente], seed=1)

    assert acciones.hablar(hablador, mundo) is True
    assert oyente.habilidades.sabe("cazar")


def test_hablar_no_gasta_energia() -> None:
    hablador = _individuo(1)
    oyente = _individuo(2, 3.5)
    mundo = _mundo([hablador, oyente])

    assert acciones.hablar(hablador, mundo) is True
    assert hablador.necesidades.energia == 100.0


@pytest.mark.parametrize(
    ("verbo", "coste"),
    [
        (acciones.tallar, 0.5),
        (acciones.frotar_madera, 1.0),
        (acciones.pintar, 0.2),
    ],
)
def test_las_practicas_de_materia_prima_gastan_energia(
    verbo: Callable[[Individuo, Mundo], bool], coste: float
) -> None:
    individuo = _individuo(1, 1.5, 1.5)
    mundo = _mundo([individuo], tiles=_tiles_con(TipoTile.BOSQUE))

    assert verbo(individuo, mundo) is True
    assert individuo.necesidades.energia == pytest.approx(100.0 - coste)


def test_cuidar_recupera_salud_y_gasta_energia_al_cuidador() -> None:
    cuidador = _individuo(1)
    herido = _individuo(2, 3.5)
    herido.necesidades.salud = 50.0

    assert acciones.cuidar(cuidador, _mundo([cuidador, herido]), herido) is True
    assert herido.necesidades.salud == pytest.approx(50.5)
    assert cuidador.necesidades.energia == pytest.approx(99.8)


def test_candidato_a_cuidar_ignora_a_quien_esta_sano() -> None:
    cuidador = _individuo(1)
    cria_sana = _individuo(2, 3.0, edad=100)
    herido = _individuo(3, 3.5)
    herido.necesidades.salud = 98.0

    # La cría está más cerca, pero a salud 100 el cuidado no daría ganancia.
    mundo = _mundo([cuidador, cria_sana, herido])
    assert acciones.candidato_a_cuidar(cuidador, mundo) is herido

    assert acciones.candidato_a_cuidar(cuidador, _mundo([cuidador, cria_sana])) is None
