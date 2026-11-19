"""La capa de consulta del grafo (stack §6): camino mínimo y nodos apagados.

Los tests van sobre un grafo sintético para fijar el contrato sin depender de
una partida: el camino es el más corto, un destino inexistente devuelve vacío
sin lanzar, y la lista de apagados conserva el portador. El último test usa la
CLI real sobre una partida guardada para comprobar que el comando cablea la
respuesta.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tribal.cli import main
from tribal.core.habilidades import Rama
from tribal.culture.arbol import Nodo
from tribal.culture.consulta import consultar
from tribal.culture.grafo import Arista, Grafo
from tribal.sim import run
from tribal.store import Repositorio


def _nodo(
    nodo_id: str,
    rama: Rama,
    nivel: int,
    titulo: str,
    requisitos: tuple[str, ...] = (),
    autor: int = 1,
    tick: int = 0,
) -> Nodo:
    return Nodo(
        id=nodo_id,
        rama=rama,
        nivel=nivel,
        titulo=titulo,
        contenido="",
        requisitos=requisitos,
        autor=autor,
        tick=tick,
    )


def _grafo(nodos: tuple[Nodo, ...]) -> Grafo:
    grafo = Grafo()
    grafo.nodos = {nodo.id: nodo for nodo in nodos}
    grafo.aristas = [Arista(requisito, nodo.id) for nodo in nodos for requisito in nodo.requisitos]
    return grafo


def test_camino_minimo_va_por_la_ruta_corta() -> None:
    # Dos caminos de la raíz al fuego: 2 aristas por el atajo y 3 por el rodeo.
    grafo = _grafo(
        (
            _nodo("raiz", "litica", 0, "Guijarro", autor=1, tick=10),
            _nodo("atajo", "litica", 1, "Lasca", ("raiz",), autor=2, tick=20),
            _nodo("rodeo", "litica", 1, "Rodeo", ("raiz",), autor=3, tick=21),
            _nodo("medio", "litica", 2, "Bifaz", ("rodeo",), autor=4, tick=30),
            _nodo("fuego", "litica", 3, "Fuego", ("atajo", "medio"), autor=5, tick=40),
        )
    )

    respuesta = consultar(grafo, "que ruta llevo al fuego")

    assert respuesta.intencion == "ruta"
    assert respuesta.destino == "fuego"
    assert [paso.id for paso in respuesta.camino] == ["raiz", "atajo", "fuego"]
    # Cada paso lleva el dato de nacimiento del nodo y la arista usada.
    assert [paso.origen for paso in respuesta.camino] == ["arbol", "arbol", "arbol"]
    assert [paso.autor for paso in respuesta.camino] == [1, 2, 5]
    assert [paso.tick for paso in respuesta.camino] == [10, 20, 40]
    assert [paso.desde for paso in respuesta.camino] == [None, "raiz", "atajo"]


def test_nodo_inexistente_devuelve_vacio_sin_excepcion() -> None:
    grafo = _grafo((_nodo("raiz", "litica", 0, "Guijarro"),))

    respuesta = consultar(grafo, "que ruta llevo al dinosaurio")

    assert respuesta.intencion == "ruta"
    assert respuesta.destino is None
    assert respuesta.camino == ()
    assert respuesta.motivo == "no encontrado"


def test_apagados_lista_portador_y_ultimo_conocido() -> None:
    grafo = _grafo(
        (
            _nodo("friccion", "fuego", 1, "Fricción", autor=7, tick=50),
            _nodo("cocinar", "fuego", 2, "Cocinar", ("friccion",), autor=8, tick=60),
            _nodo("brasa", "fuego", 0, "Brasa", autor=9, tick=5),
        )
    )
    grafo.apagar("friccion", tick=300, motivo="sin portadores")
    grafo.apagar("cocinar", tick=350, motivo="sequía")
    grafo.ultimo_imitador["friccion"] = 9

    respuesta = consultar(grafo, "que nodos se apagaron")

    assert respuesta.intencion == "apagados"
    assert [apagado.id for apagado in respuesta.apagados] == ["friccion", "cocinar"]
    friccion, cocinar = respuesta.apagados
    assert (friccion.autor, friccion.tick_apagado, friccion.motivo_apagado) == (
        7,
        300,
        "sin portadores",
    )
    assert friccion.ultimo_portador == "ind-9"
    assert cocinar.ultimo_portador == "desconocido"


def test_consulta_ambigua_elige_el_mas_cercano_y_lo_dice() -> None:
    grafo = _grafo(
        (
            _nodo("pintar_fuego", "simbolico", 0, "Pintar el fuego", autor=1),
            _nodo(
                "fuego_sagrado",
                "simbolico",
                1,
                "Fuego sagrado",
                ("pintar_fuego",),
                autor=2,
            ),
        )
    )

    respuesta = consultar(grafo, "que ruta llevo al fuego")

    assert respuesta.destino == "pintar_fuego"
    assert "2 candidatos" in respuesta.aviso
    assert respuesta.camino[0].id == "pintar_fuego"


def test_consulta_es_determinista() -> None:
    grafo = _grafo(
        (
            _nodo("raiz", "litica", 0, "Guijarro"),
            _nodo("lasca", "litica", 1, "Lasca", ("raiz",)),
        )
    )

    primera = consultar(grafo, "que ruta llevo a la lasca").a_json()
    segunda = consultar(grafo, "que ruta llevo a la lasca").a_json()

    assert json.dumps(primera, sort_keys=True) == json.dumps(segunda, sort_keys=True)
    assert primera["camino"][-1]["id"] == "lasca"


def test_cli_ask_sobre_una_partida_guardada(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ruta = tmp_path / "tribu.db"
    simulacion = run(600, 42, headless=True)
    repositorio = Repositorio(ruta)
    try:
        repositorio.guardar(
            simulacion.mundo,
            simulacion.grafo,
            simulacion.diario,
            [],
            config=simulacion.config,
        )
    finally:
        repositorio.cerrar()

    assert main(["culture", "ask", "--db", str(ruta), "--query", "que ruta llevo al fuego"]) == 0
    texto = capsys.readouterr().out
    assert "camino (" in texto
    assert "origen arbol" in texto

    assert (
        main(["culture", "ask", "--db", str(ruta), "--query", "que ruta llevo al fuego", "--json"])
        == 0
    )
    respuesta = json.loads(capsys.readouterr().out)
    assert respuesta["intencion"] == "ruta"
    assert respuesta["camino"]
    assert all(paso["origen"] for paso in respuesta["camino"])


def test_vocabulario_documentado_de_ruta() -> None:
    grafo = _grafo(
        (
            _nodo("raiz", "litica", 0, "Guijarro"),
            _nodo("fuego", "litica", 1, "Fuego", ("raiz",)),
        )
    )

    for pregunta in ("hasta el fuego", "llegar al fuego", "llego al fuego"):
        respuesta = consultar(grafo, pregunta)
        assert respuesta.intencion == "ruta", pregunta
        assert [paso.id for paso in respuesta.camino] == ["raiz", "fuego"], pregunta


def test_vocabulario_documentado_de_apagados() -> None:
    grafo = _grafo((_nodo("raiz", "litica", 0, "Guijarro"),))
    grafo.apagar("raiz", tick=200, motivo="sin portadores")

    for pregunta in (
        "que nodos murieron con el anciano",
        "que nodos fallecieron",
        "que nodos desaparecieron",
    ):
        respuesta = consultar(grafo, pregunta)
        assert respuesta.intencion == "apagados", pregunta
        assert [apagado.id for apagado in respuesta.apagados] == ["raiz"], pregunta


def test_bfs_recorre_aristas_en_sentido_inverso() -> None:
    # La única arista va de lasca → guijarro, pero la raíz es guijarro: el
    # camino a lasca solo existe si el BFS trata la arista como no dirigida.
    grafo = _grafo(
        (
            _nodo("guijarro", "litica", 0, "Guijarro", ("lasca",)),
            _nodo("lasca", "litica", 1, "Lasca"),
        )
    )

    respuesta = consultar(grafo, "que ruta llevo a la lasca")

    assert [paso.id for paso in respuesta.camino] == ["guijarro", "lasca"]
    assert respuesta.camino[-1].desde == "guijarro"


def test_desempate_estable_entre_caminos_de_igual_longitud() -> None:
    # Dos rutas de 2 aristas hasta fuego. Las aristas se insertan en el orden
    # raiz→beta, raiz→alfa, así que sin `vecinos.sort()` el BFS elegiría beta.
    grafo = _grafo(
        (
            _nodo("raiz", "litica", 0, "Guijarro"),
            _nodo("beta", "litica", 1, "Beta", ("raiz",)),
            _nodo("alfa", "litica", 1, "Alfa", ("raiz",)),
            _nodo("fuego", "litica", 2, "Fuego", ("alfa", "beta")),
        )
    )

    respuesta = consultar(grafo, "que ruta llevo al fuego")

    assert [paso.id for paso in respuesta.camino] == ["raiz", "alfa", "fuego"]


def test_cli_ask_con_directorio_sale_con_dos(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    directorio = tmp_path / "carpeta"
    directorio.mkdir()

    assert main(["culture", "ask", "--db", str(directorio), "--query", "hasta el fuego"]) == 2
    assert "no es un fichero" in capsys.readouterr().err


def test_cli_ask_con_base_invalida_sale_con_dos(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ruta = tmp_path / "no-es-una-partida.db"
    ruta.write_text("no soy SQLite", encoding="utf-8")

    assert main(["culture", "ask", "--db", str(ruta), "--query", "que nodos se apagaron"]) == 2
    assert "error:" in capsys.readouterr().err
