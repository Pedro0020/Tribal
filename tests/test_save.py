"""Guardar y reanudar: la partida sobrevive entre sesiones (SAVE-001).

El juez del determinismo es un test de ida y vuelta: 600 ticks seguidos frente
a 300 + guardar/cerrar + reanudar 300, con el mismo seed y sin LLM. Si algo no
se persiste —el RNG, el paseo, la saliencia acumulada, un contador—, el
`resumen()` deja de coincidir. El `save_meta.json` se comprueba aparte: existe,
lleva semilla y estado del RNG, y su escritura ocurre después del `COMMIT`, así
que un fallo al escribirlo no deja la base a medias.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from tribal.cli import main
from tribal.culture.kpi import evaluar
from tribal.sim import run
from tribal.store import BaseInvalida, Repositorio

TICKS = 300


@pytest.fixture(scope="module")
def partidas(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, Path, dict[str, object], dict[str, object]]:
    """Partida A de 600 seguidos y partida B de 300 + reanudar 300."""
    raiz = tmp_path_factory.mktemp("save")
    directa = raiz / "directa"
    reanudada = raiz / "reanudada"
    resumen_directo = run(TICKS * 2, 42, headless=True, db=directa / "world.db").resumen()
    run(TICKS, 42, headless=True, db=reanudada / "world.db")
    resumen_reanudado = run(
        TICKS, 42, headless=True, db=reanudada / "world.db", resume=True
    ).resumen()
    return (
        directa / "world.db",
        reanudada / "world.db",
        resumen_directo,
        resumen_reanudado,
    )


def test_reanudar_da_el_mismo_resumen_que_la_corrida_seguida(
    partidas: tuple[Path, Path, dict[str, object], dict[str, object]],
) -> None:
    directa, reanudada, resumen_directo, resumen_reanudado = partidas
    assert resumen_reanudado == resumen_directo
    assert resumen_reanudado["ticks"] == 600
    assert resumen_reanudado["seed"] == 42

    repositorio_a = Repositorio(directa, crear=False)
    try:
        estado_a = repositorio_a.cargar()
    finally:
        repositorio_a.cerrar()
    repositorio_b = Repositorio(reanudada, crear=False)
    try:
        estado_b = repositorio_b.cargar()
    finally:
        repositorio_b.cerrar()

    assert estado_a.tick == estado_b.tick == 600
    assert estado_a.partida is not None and estado_b.partida is not None
    assert estado_a.partida.mundo.tick == 600
    assert estado_b.partida.mundo.tick == 600


def test_la_semilla_y_el_estado_del_rng_se_restauran(
    partidas: tuple[Path, Path, dict[str, object], dict[str, object]],
) -> None:
    directa, reanudada, _resumen_directo, _resumen_reanudado = partidas
    for ruta in (directa, reanudada):
        meta = json.loads((ruta.parent / "save_meta.json").read_text(encoding="utf-8"))
        assert meta["seed"] == 42
        assert meta["tick"] == 600
        # `random.Random.getstate()`: versión, 625 enteros y gauss_next.
        assert meta["rng"][0] == 3
        assert len(meta["rng"][1]) == 625

    directa_repo = Repositorio(directa, crear=False)
    reanudada_repo = Repositorio(reanudada, crear=False)
    try:
        assert directa_repo.cargar().partida is not None
        assert reanudada_repo.cargar().partida is not None
        estado_directo = directa_repo.cargar().partida
        estado_reanudado = reanudada_repo.cargar().partida
    finally:
        directa_repo.cerrar()
        reanudada_repo.cerrar()

    assert estado_directo is not None and estado_reanudado is not None
    assert estado_directo.mundo.azar.getstate() == estado_reanudado.mundo.azar.getstate()


def test_report_kpi_es_identico_tras_reanudar(
    partidas: tuple[Path, Path, dict[str, object], dict[str, object]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    directa, reanudada, _resumen_directo, _resumen_reanudado = partidas
    assert main(["report", "kpi", "--db", str(directa), "--json"]) == 0
    kpi_directo = json.loads(capsys.readouterr().out)
    assert main(["report", "kpi", "--db", str(reanudada), "--json"]) == 0
    kpi_reanudado = json.loads(capsys.readouterr().out)

    assert kpi_directo.pop("db") != kpi_reanudado.pop("db")
    assert kpi_directo == kpi_reanudado
    assert evaluar(directa).a_json() == evaluar(reanudada).a_json()


def test_reanudar_sigue_desde_el_tick_guardado(tmp_path: Path) -> None:
    ruta = tmp_path / "world.db"
    run(250, 7, headless=True, db=ruta)

    repositorio = Repositorio(ruta, crear=False)
    try:
        partida = repositorio.cargar().partida
        assert partida is not None
        assert partida.mundo.tick == 250
    finally:
        repositorio.cerrar()

    segunda = run(50, 7, headless=True, db=ruta, resume=True)
    assert segunda.mundo.tick == 300


def test_save_meta_lleva_semilla_config_y_rng(tmp_path: Path) -> None:
    ruta = tmp_path / "world.db"
    run(120, 9, headless=True, db=ruta)

    meta = json.loads((tmp_path / "save_meta.json").read_text(encoding="utf-8"))
    assert meta["version"] == 1
    assert meta["nombre"] == "world"
    assert meta["seed"] == 9
    assert meta["tick"] == 120
    assert meta["poblacion"] > 0
    assert meta["nodos"] > 0
    assert meta["config"]["seed"] == 9
    assert meta["config"]["individuos"] == 12
    assert meta["rng"][0] == 3
    assert "creado" in meta and "actualizado" in meta


def test_un_fallo_al_escribir_meta_no_aborta_ni_corrompe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ruta = tmp_path / "world.db"

    def meta_rota(*_args: object, **_kwargs: object) -> None:
        raise OSError("disco lleno antes de save_meta")

    monkeypatch.setattr("tribal.store.repositorio._escribir_meta", meta_rota)
    simulacion = run(120, 42, headless=True, db=ruta)
    assert simulacion.mundo.tick == 120
    assert "warning" in capsys.readouterr().err

    with sqlite3.connect(ruta) as conexion:
        integridad = conexion.execute("PRAGMA integrity_check").fetchone()[0]
    assert integridad == "ok"

    repositorio = Repositorio(ruta, crear=False)
    try:
        estado = repositorio.cargar()
    finally:
        repositorio.cerrar()
    assert estado.tick == 120
    assert estado.partida is not None
    assert estado.partida.mundo.tick == 120

    # Reanudar no necesita la meta: la base es la fuente de verdad.
    segunda = run(10, 42, headless=True, db=ruta, resume=True)
    assert segunda.mundo.tick == 130


def test_fresh_borra_la_meta_de_la_partida_anterior(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ruta = tmp_path / "world.db"
    assert main(["run", "--headless", "--ticks", "60", "--db", str(ruta)]) == 0
    meta_vieja = json.loads((tmp_path / "save_meta.json").read_text(encoding="utf-8"))
    assert meta_vieja["tick"] == 60

    assert main(["run", "--headless", "--ticks", "30", "--db", str(ruta), "--fresh"]) == 0
    capsys.readouterr()

    meta_nueva = json.loads((tmp_path / "save_meta.json").read_text(encoding="utf-8"))
    assert meta_nueva["tick"] == 30
    assert meta_nueva["actualizado"] >= meta_vieja["actualizado"]


def test_reanudar_una_base_sin_partida_falla(tmp_path: Path) -> None:
    ruta = tmp_path / "vacia.db"
    Repositorio(ruta).cerrar()

    with pytest.raises(BaseInvalida):
        run(10, 42, headless=True, db=ruta, resume=True)


def test_cli_resume_suma_ticks_y_se_niega_a_pisar(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ruta = tmp_path / "world.db"
    assert main(["run", "--headless", "--ticks", "60", "--db", str(ruta)]) == 0
    capsys.readouterr()

    assert main(["run", "--headless", "--ticks", "60", "--db", str(ruta)]) == 2
    assert "ya existe" in capsys.readouterr().err

    assert (
        main(["run", "--headless", "--ticks", "60", "--db", str(ruta), "--resume", "--json"]) == 0
    )
    resumen = json.loads(capsys.readouterr().out)
    assert resumen["ticks"] == 120

    assert main(["run", "--resume", "--headless", "--ticks", "10"]) == 2
    assert "--resume necesita --db" in capsys.readouterr().err

    assert (
        main(["run", "--headless", "--ticks", "10", "--db", str(tmp_path / "no.db"), "--resume"])
        == 2
    )
    assert "no existe" in capsys.readouterr().err
