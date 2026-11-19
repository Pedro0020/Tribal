"""`report telemetry`: una muestra por intervalo, determinista y cuadrada con el resumen."""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any, cast

import pytest

from tribal.cli import main
from tribal.sim import run
from tribal.store import Repositorio

TICKS = 600
INTERVALO = 60
SEMILLA = 3
CAMPOS = {
    "tick",
    "poblacion",
    "divergentes",
    "conformistas",
    "neutros",
    "nodos",
    "aristas",
    "media_energia",
    "media_sed",
}
CAMPOS_CSV = (
    "tick",
    "poblacion",
    "divergentes",
    "conformistas",
    "neutros",
    "nodos",
    "aristas",
    "media_energia",
    "media_sed",
)


@pytest.fixture(scope="module")
def partida_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Una partida larga ya escrita: 6000 ticks deben dejar 100 muestras."""
    ruta = tmp_path_factory.mktemp("telemetria") / "tribu.db"
    run(6000, SEMILLA, headless=True, db=ruta)
    return ruta


def _informe(capsys: pytest.CaptureFixture[str], *extra: str) -> dict[str, Any]:
    assert main(["report", "telemetry", "--json", *extra]) == 0
    return cast(dict[str, Any], json.loads(capsys.readouterr().out))


def test_json_da_una_muestra_por_intervalo_y_no_una_por_tick(
    capsys: pytest.CaptureFixture[str],
) -> None:
    informe = _informe(
        capsys,
        "--seed",
        str(SEMILLA),
        "--ticks",
        str(TICKS),
        "--intervalo",
        str(INTERVALO),
    )

    assert informe["seed"] == SEMILLA
    assert informe["ticks"] == TICKS
    assert informe["intervalo"] == INTERVALO
    assert informe["crisis"] is False
    assert len(informe["muestras"]) == TICKS // INTERVALO == 10
    assert len(informe["muestras"]) != informe["ticks"]
    assert [muestra["tick"] for muestra in informe["muestras"]] == [
        60,
        120,
        180,
        240,
        300,
        360,
        420,
        480,
        540,
        600,
    ]
    assert all(set(muestra) == CAMPOS for muestra in informe["muestras"])


def test_primera_y_ultima_muestra_cuadran_con_el_resumen(
    capsys: pytest.CaptureFixture[str],
) -> None:
    informe = _informe(capsys, "--seed", str(SEMILLA), "--ticks", str(TICKS))
    primera, ultima = informe["muestras"][0], informe["muestras"][-1]
    corto = run(INTERVALO, SEMILLA, headless=True).resumen()
    completo = run(TICKS, SEMILLA, headless=True).resumen()

    assert primera["tick"] == INTERVALO
    assert primera["poblacion"] == corto["poblacion_final"]
    assert primera["divergentes"] == corto["n_divergentes"]
    assert primera["conformistas"] == corto["n_conformistas"]
    assert primera["neutros"] == corto["n_neutros"]
    assert primera["nodos"] == len(corto["nodos"])
    assert primera["aristas"] == len(corto["aristas"])
    assert primera["media_energia"] == corto["media_energia"]
    assert primera["media_sed"] == corto["media_sed"]

    assert ultima["tick"] == TICKS
    assert ultima["poblacion"] == completo["poblacion_final"]
    assert ultima["divergentes"] == completo["n_divergentes"]
    assert ultima["conformistas"] == completo["n_conformistas"]
    assert ultima["neutros"] == completo["n_neutros"]
    assert ultima["nodos"] == len(completo["nodos"])
    assert ultima["aristas"] == len(completo["aristas"])
    assert ultima["media_energia"] == completo["media_energia"]
    assert ultima["media_sed"] == completo["media_sed"]


def test_sin_json_imprime_una_tabla_legible(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["report", "telemetry", "--ticks", "120", "--intervalo", "60"]) == 0
    lineas = capsys.readouterr().out.strip().splitlines()

    assert "intervalo 60" in lineas[0]
    assert "tick" in lineas[1] and "pob" in lineas[1] and "aristas" in lineas[1]
    assert len(lineas) == 2 + 2  # cabecera + dos muestras


def test_dos_corridas_dan_las_mismas_muestras(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["report", "telemetry", "--json", "--ticks", "600"]) == 0
    primera = capsys.readouterr().out
    assert main(["report", "telemetry", "--json", "--ticks", "600"]) == 0
    segunda = capsys.readouterr().out

    assert primera == segunda


def test_db_escribe_una_muestra_por_intervalo_y_no_por_frame(
    partida_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["report", "telemetry", "--db", str(partida_db), "--json"]) == 0
    muestras = cast(list[dict[str, Any]], json.loads(capsys.readouterr().out))

    assert len(muestras) == 6000 // 60 == 100
    assert len(muestras) != 6000
    assert [muestra["tick"] for muestra in muestras] == list(range(60, 6001, 60))
    assert all(set(muestra) == CAMPOS for muestra in muestras)


def test_db_csv_tiene_cabecera_una_fila_por_muestra_y_es_parseable(
    partida_db: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destino = tmp_path / "telemetria.csv"
    assert main(["report", "telemetry", "--db", str(partida_db), "--csv", str(destino)]) == 0
    assert capsys.readouterr().out == ""

    crudo = destino.read_bytes()
    assert b"\r" not in crudo
    filas = list(csv.reader(crudo.decode("utf-8").splitlines()))
    assert tuple(filas[0]) == CAMPOS_CSV
    assert len(filas) == 1 + 100
    assert [int(fila[0]) for fila in filas[1:]] == list(range(60, 6001, 60))

    # `--csv` sin PATH vuelca el mismo CSV a stdout.
    assert main(["report", "telemetry", "--db", str(partida_db), "--csv"]) == 0
    salida = list(csv.reader(capsys.readouterr().out.splitlines()))
    assert salida == filas


def test_db_json_coincide_con_el_csv(
    partida_db: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destino = tmp_path / "telemetria.csv"
    assert main(["report", "telemetry", "--db", str(partida_db), "--csv", str(destino)]) == 0
    filas = list(csv.reader(destino.read_text(encoding="utf-8").splitlines()))[1:]

    assert main(["report", "telemetry", "--db", str(partida_db), "--json"]) == 0
    muestras = cast(list[dict[str, Any]], json.loads(capsys.readouterr().out))

    assert [[str(muestra[campo]) for campo in CAMPOS_CSV] for muestra in muestras] == filas


def test_db_csv_a_stdout_es_utf8_con_lf_en_bytes(
    partida_db: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    assert main(["report", "telemetry", "--db", str(partida_db), "--csv"]) == 0
    crudo = capsysbinary.readouterr().out

    assert b"\r" not in crudo
    assert crudo.endswith(b"\n")
    assert crudo.decode("utf-8").splitlines()[0] == ",".join(CAMPOS_CSV)


def test_db_csv_a_directorio_inexistente_sale_con_2(
    partida_db: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destino = tmp_path / "no-existe" / "telemetria.csv"
    assert main(["report", "telemetry", "--db", str(partida_db), "--csv", str(destino)]) == 2
    assert "error:" in capsys.readouterr().err


def test_db_avisa_de_las_opciones_de_simulacion_ignoradas(
    partida_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        main(
            [
                "report",
                "telemetry",
                "--db",
                str(partida_db),
                "--json",
                "--ticks",
                "999",
                "--seed",
                "7",
            ]
        )
        == 0
    )
    error = capsys.readouterr().err
    assert "warning:" in error and "--ticks" in error and "--seed" in error


def test_db_vieja_por_cli_migra_al_leer_y_run_no_borra_el_historico(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ruta = tmp_path / "f3-003.db"
    Repositorio(ruta).cerrar()
    conexion = sqlite3.connect(ruta)
    try:
        conexion.execute("DROP TABLE telemetria")
        conexion.execute(
            "CREATE TABLE telemetria (tick INTEGER PRIMARY KEY, poblacion INTEGER NOT NULL, "
            "n_divergentes INTEGER NOT NULL, n_conformistas INTEGER NOT NULL, "
            "n_nodos INTEGER NOT NULL, n_aristas INTEGER NOT NULL)"
        )
        conexion.executemany(
            "INSERT INTO telemetria VALUES (?, ?, ?, ?, ?, ?)",
            [(tick, 12, 3, 7, 15, 12) for tick in range(60, 6001, 60)],
        )
        conexion.commit()
    finally:
        conexion.close()

    # Leer la base vieja migra columnas sin perder las 100 filas; las nuevas
    # valen 0 porque el esquema anterior no las guardaba.
    assert main(["report", "telemetry", "--db", str(ruta), "--json"]) == 0
    muestras = cast(list[dict[str, Any]], json.loads(capsys.readouterr().out))
    assert len(muestras) == 100
    assert [muestra["tick"] for muestra in muestras] == list(range(60, 6001, 60))
    assert all(muestra["neutros"] == 0 for muestra in muestras)
    assert all(muestra["media_energia"] == 0 and muestra["media_sed"] == 0 for muestra in muestras)

    # `run --db` sobre una partida existente no la pisa: rechaza con 2 y la deja intacta.
    assert main(["run", "--headless", "--ticks", "120", "--db", str(ruta)]) == 2
    assert "usa --fresh para empezar de cero" in capsys.readouterr().err
    assert main(["report", "telemetry", "--db", str(ruta), "--json"]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 100

    # `--fresh` es la única vía que empieza de cero, y lo dice el help.
    assert main(["run", "--headless", "--ticks", "120", "--db", str(ruta), "--fresh"]) == 0
    capsys.readouterr()
    assert main(["report", "telemetry", "--db", str(ruta), "--json"]) == 0
    nuevas = cast(list[dict[str, Any]], json.loads(capsys.readouterr().out))
    assert [muestra["tick"] for muestra in nuevas] == [60, 120]


def test_db_sin_telemetria_o_sin_tabla_sale_con_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vacia = tmp_path / "vacia.db"
    Repositorio(vacia).cerrar()
    assert main(["report", "telemetry", "--db", str(vacia)]) == 2
    assert "no tiene telemetria" in capsys.readouterr().err

    sin_tablas = tmp_path / "sin-tablas.db"
    with sqlite3.connect(sin_tablas):
        pass
    assert main(["report", "telemetry", "--db", str(sin_tablas)]) == 2
    assert "faltan tablas" in capsys.readouterr().err
