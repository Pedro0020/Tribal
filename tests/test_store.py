"""Persistencia de la partida en SQLite (stack §5).

El criterio es de ida y vuelta: lo que el motor tiene en RAM se escribe al
cerrar, y reabrir la base devuelve los mismos nodos —con su `origen`, `autor` y
`tick`—, las mismas aristas y la misma población. No se reanuda la partida
(eso es SAVE-001): solo se persiste y se vuelve a leer.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from tribal.cli import main
from tribal.sim import Simulacion, run
from tribal.store import Repositorio
from tribal.store.esquema import TABLAS


@pytest.fixture(scope="module")
def partida(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Simulacion]:
    """Una partida de 600 ticks ya escrita y cerrada, compartida por los tests."""
    ruta = tmp_path_factory.mktemp("store") / "tribu.db"
    return ruta, run(600, 42, headless=True, db=ruta)


def _estado(ruta: Path) -> Repositorio:
    return Repositorio(ruta, crear=False)


def test_el_esquema_crea_las_tablas_de_stack5(tmp_path: Path) -> None:
    ruta = tmp_path / "tribu.db"
    Repositorio(ruta).cerrar()

    with sqlite3.connect(ruta) as conexion:
        tablas = {
            fila[0]
            for fila in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        columnas_nodos = {fila[1] for fila in conexion.execute("PRAGMA table_info(nodos)")}
        columnas_telemetria = {
            fila[1] for fila in conexion.execute("PRAGMA table_info(telemetria)")
        }
        journal = str(conexion.execute("PRAGMA journal_mode").fetchone()[0]).lower()

    assert set(TABLAS) <= tablas
    assert {"id", "tipo", "titulo", "contenido", "popularidad", "estado"} <= columnas_nodos
    assert {"origen", "autor", "tick"} <= columnas_nodos
    assert {"tick_apagado", "motivo_apagado"} <= columnas_nodos
    assert {
        "tick",
        "poblacion",
        "n_divergentes",
        "n_conformistas",
        "n_neutros",
        "n_nodos",
        "n_aristas",
        "media_energia",
        "media_sed",
    } <= columnas_telemetria
    assert journal == "wal"


def test_cerrar_y_reabrir_conserva_nodos_aristas_y_origen(
    partida: tuple[Path, Simulacion],
) -> None:
    ruta, simulacion = partida
    repositorio = _estado(ruta)
    try:
        estado = repositorio.cargar()
    finally:
        repositorio.cerrar()

    assert estado.tick == 600 == simulacion.mundo.tick
    assert estado.seed == 42
    assert estado.config["seed"] == 42
    assert estado.config["ticks_guardado"] == 300

    assert set(estado.grafo.nodos) == set(simulacion.grafo.nodos)
    for nodo_id, original in simulacion.grafo.nodos.items():
        guardado = estado.grafo.nodos[nodo_id]
        assert (guardado.origen, guardado.autor, guardado.tick) == (
            original.origen,
            original.autor,
            original.tick,
        ), nodo_id
        assert guardado == original

    assert [(arista.origen, arista.destino) for arista in estado.grafo.aristas] == [
        (arista.origen, arista.destino) for arista in simulacion.grafo.aristas
    ]
    assert [individuo.id for individuo in estado.poblacion] == [
        individuo.id for individuo in simulacion.mundo.individuos
    ]
    assert all(individuo.estado == "vivo" for individuo in estado.poblacion)


def test_run_db_escribe_la_partida_y_report_db_coincide(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ruta = tmp_path / "tribu.db"
    assert main(["run", "--headless", "--ticks", "600", "--db", str(ruta), "--json"]) == 0
    resumen = json.loads(capsys.readouterr().out)

    assert main(["report", "db", "--db", str(ruta), "--json"]) == 0
    informe = json.loads(capsys.readouterr().out)

    assert informe["seed"] == resumen["seed"] == 42
    assert informe["tick"] == resumen["ticks"] == 600
    assert informe["poblacion"] == resumen["poblacion_final"]
    assert informe["nodos"] == len(resumen["nodos"])
    assert informe["nodos_por_origen"] == resumen["nodos_por_origen"]
    assert informe["aristas"] == len(resumen["aristas"])
    assert informe["diario"] == resumen["diario"]["entradas"]
    assert informe["recursos"] > 0
    # Una muestra por intervalo de telemetría (60 ticks), no una por volcado.
    assert informe["telemetria"] == 10


def test_la_telemetria_se_escribe_por_intervalo_y_al_cerrar(tmp_path: Path) -> None:
    ruta = tmp_path / "tribu.db"
    run(700, 42, headless=True, db=ruta)

    repositorio = _estado(ruta)
    try:
        # 60, 120, ..., 660 y el cierre en 700: el tick final se conserva.
        assert repositorio.instantanea()["telemetria"] == 12
    finally:
        repositorio.cerrar()


def test_dos_semillas_producen_bases_distintas(tmp_path: Path) -> None:
    primera = tmp_path / "primera.db"
    segunda = tmp_path / "segunda.db"
    run(120, 1, headless=True, db=primera)
    run(120, 2, headless=True, db=segunda)

    assert primera.read_bytes() != segunda.read_bytes()
    for ruta, seed in ((primera, 1), (segunda, 2)):
        repositorio = _estado(ruta)
        try:
            assert repositorio.cargar().seed == seed
        finally:
            repositorio.cerrar()


def test_report_db_sale_con_2_si_la_base_no_sirve(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    basura = tmp_path / "basura.db"
    basura.write_text("esto no es sqlite", encoding="utf-8")

    assert main(["report", "db", "--db", str(basura), "--json"]) == 2
    assert "error" in capsys.readouterr().err

    vacia = tmp_path / "vacia.db"
    with sqlite3.connect(vacia):
        pass
    assert main(["report", "db", "--db", str(vacia)]) == 2
    assert "faltan tablas" in capsys.readouterr().err

    assert main(["report", "db", "--db", str(tmp_path / "no-existe.db")]) == 2
    assert "no existe" in capsys.readouterr().err


def test_el_apagado_del_nodo_sobrevive_a_cerrar_y_reabrir(tmp_path: Path) -> None:
    ruta = tmp_path / "tribu.db"
    simulacion = run(120, 42, headless=True)
    original = simulacion.grafo.nodos["guijarro"]
    simulacion.grafo.apagar("guijarro", tick=100, motivo="sin portadores")

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

    reabierto = _estado(ruta)
    try:
        nodo = reabierto.cargar().grafo.nodos["guijarro"]
    finally:
        reabierto.cerrar()

    assert (nodo.estado, nodo.tick_apagado, nodo.motivo_apagado) == (
        "apagado",
        100,
        "sin portadores",
    )
    assert (nodo.origen, nodo.autor, nodo.tick) == (original.origen, original.autor, original.tick)


def test_una_base_sin_columnas_de_apagado_se_migra_al_abrirla(tmp_path: Path) -> None:
    ruta = tmp_path / "vieja.db"
    with sqlite3.connect(ruta) as conexion:
        conexion.execute(
            "CREATE TABLE nodos (id TEXT PRIMARY KEY, tipo TEXT NOT NULL, "
            "titulo TEXT NOT NULL, contenido TEXT NOT NULL, popularidad INTEGER NOT NULL, "
            "estado TEXT NOT NULL, origen TEXT NOT NULL, autor INTEGER NOT NULL, "
            "tick INTEGER NOT NULL, nivel INTEGER NOT NULL, requisitos TEXT NOT NULL)"
        )

    Repositorio(ruta).cerrar()

    with sqlite3.connect(ruta) as conexion:
        columnas = {fila[1] for fila in conexion.execute("PRAGMA table_info(nodos)")}
    assert {"tick_apagado", "motivo_apagado"} <= columnas


def test_una_base_sin_columnas_de_telemetria_se_migra_al_abrirla(tmp_path: Path) -> None:
    ruta = tmp_path / "telemetria-vieja.db"
    with sqlite3.connect(ruta) as conexion:
        conexion.execute(
            "CREATE TABLE telemetria (tick INTEGER PRIMARY KEY, poblacion INTEGER NOT NULL, "
            "n_divergentes INTEGER NOT NULL, n_conformistas INTEGER NOT NULL, "
            "n_nodos INTEGER NOT NULL, n_aristas INTEGER NOT NULL)"
        )
        conexion.execute("INSERT INTO telemetria VALUES (60, 12, 3, 7, 15, 12)")

    Repositorio(ruta).cerrar()

    with sqlite3.connect(ruta) as conexion:
        columnas = {fila[1] for fila in conexion.execute("PRAGMA table_info(telemetria)")}
    assert {"n_neutros", "media_energia", "media_sed"} <= columnas


def test_solo_el_repositorio_importa_sqlite3() -> None:
    """`store` es la única puerta: el resto del producto no habla SQL."""
    paquete = Path(__file__).resolve().parents[1] / "tribal"
    culpables = {
        ruta.name
        for ruta in paquete.rglob("*.py")
        if "import sqlite3" in ruta.read_text(encoding="utf-8")
        or "from sqlite3" in ruta.read_text(encoding="utf-8")
    }

    assert culpables == {"repositorio.py"}
