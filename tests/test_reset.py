"""Nuevo mundo (RESET-001): archivar o borrar la partida y empezar en tick 0.

El juez es doble: la partida vieja sigue existiendo donde se archivó (misma
semilla, mismo tick y mismos bytes) y la nueva es de verdad otra (tick 0, tribu
de 8-15 y semilla distinta o la pedida). Sin `--yes` no se toca ni un byte:
mismo md5 y ningún fichero nuevo.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tribal import reset as modulo_reset
from tribal.cli import main
from tribal.config import MAX_INDIVIDUOS, MIN_INDIVIDUOS
from tribal.sim import run
from tribal.store import Repositorio

TICKS = 30
SEED = 7


def _md5(ruta: Path) -> str:
    return hashlib.md5(ruta.read_bytes()).hexdigest()


def _partida(tmp_path: Path) -> Path:
    db = tmp_path / "data" / "world.db"
    run(TICKS, SEED, headless=True, db=db)
    return db


def _instantanea(db: Path) -> tuple[int, int, int]:
    repositorio = Repositorio(db, crear=False)
    try:
        datos = repositorio.instantanea()
    finally:
        repositorio.cerrar()
    return datos["tick"], datos["poblacion"], datos["seed"]


def test_reset_archiva_la_partida_y_deja_un_mundo_nuevo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = _partida(tmp_path)
    viejo = _md5(db)
    assert _instantanea(db)[0] == TICKS

    assert main(["world", "reset", "--db", str(db), "--seed", "99", "--yes"]) == 0
    assert "seed 99" in capsys.readouterr().out

    tick, poblacion, seed = _instantanea(db)
    assert (tick, seed) == (0, 99)
    assert MIN_INDIVIDUOS <= poblacion <= MAX_INDIVIDUOS

    archivadas = sorted((db.parent / "archivo").glob("*.db"))
    assert len(archivadas) == 1
    assert _md5(archivadas[0]) == viejo
    vieja_tick, _, vieja_seed = _instantanea(archivadas[0])
    assert (vieja_tick, vieja_seed) == (TICKS, SEED)

    meta = json.loads((db.parent / "save_meta.json").read_text(encoding="utf-8"))
    assert (meta["seed"], meta["tick"], meta["poblacion"]) == (99, 0, poblacion)
    metas_archivadas = sorted((db.parent / "archivo").glob("*.meta.json"))
    assert len(metas_archivadas) == 1
    assert json.loads(metas_archivadas[0].read_text(encoding="utf-8"))["tick"] == TICKS


def test_sin_yes_no_toca_nada(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db = _partida(tmp_path)
    meta = db.parent / "save_meta.json"
    antes, meta_antes = _md5(db), _md5(meta)

    assert main(["world", "reset", "--db", str(db)]) == 2

    assert _md5(db) == antes
    assert _md5(meta) == meta_antes
    assert not (db.parent / "archivo").exists()
    assert "--yes" in capsys.readouterr().err


def test_borrar_no_deja_archivo(tmp_path: Path) -> None:
    db = _partida(tmp_path)

    assert main(["world", "reset", "--db", str(db), "--borrar", "--yes", "--seed", "5"]) == 0

    tick, poblacion, seed = _instantanea(db)
    assert (tick, seed) == (0, 5)
    assert MIN_INDIVIDUOS <= poblacion <= MAX_INDIVIDUOS
    assert not (db.parent / "archivo").exists()


def test_semilla_nueva_si_no_se_pasa_y_meta_coherente(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = _partida(tmp_path)

    assert main(["world", "reset", "--db", str(db), "--archivar", "--yes"]) == 0

    tick, poblacion, seed = _instantanea(db)
    assert tick == 0
    assert seed != SEED
    assert f"seed {seed}" in capsys.readouterr().out
    meta = json.loads((db.parent / "save_meta.json").read_text(encoding="utf-8"))
    assert (meta["seed"], meta["tick"], meta["poblacion"]) == (seed, 0, poblacion)


def test_el_mensaje_previo_nombra_sidecars_y_archivo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = _partida(tmp_path)

    assert main(["world", "reset", "--db", str(db)]) == 2

    error = capsys.readouterr().err
    assert "archivar" in error
    assert "-wal/-shm" in error
    assert "archivo/" in error


def test_archiva_los_sidecars_wal_y_shm(tmp_path: Path) -> None:
    db = _partida(tmp_path)
    Path(f"{db}-wal").write_bytes(b"wal")
    Path(f"{db}-shm").write_bytes(b"shm")

    assert main(["world", "reset", "--db", str(db), "--yes"]) == 0

    (archivada,) = (db.parent / "archivo").glob("*.db")
    assert not Path(f"{db}-wal").exists()
    assert not Path(f"{db}-shm").exists()
    assert Path(f"{archivada}-wal").read_bytes() == b"wal"
    assert Path(f"{archivada}-shm").read_bytes() == b"shm"


def test_colision_de_marca_no_pisa_el_archivo_anterior(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = _partida(tmp_path)

    class _Reloj:
        @staticmethod
        def now(_tz: object) -> datetime:
            return datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)

    monkeypatch.setattr(modulo_reset, "datetime", _Reloj)
    assert main(["world", "reset", "--db", str(db), "--yes", "--seed", "1"]) == 0
    assert main(["world", "reset", "--db", str(db), "--yes", "--seed", "2"]) == 0

    archivo = db.parent / "archivo"
    assert sorted(ruta.name for ruta in archivo.glob("*.db")) == [
        "world-20260102T030405Z-2.db",
        "world-20260102T030405Z.db",
    ]
    assert sorted(ruta.name for ruta in archivo.glob("*.meta.json")) == [
        "world-20260102T030405Z-2.meta.json",
        "world-20260102T030405Z.meta.json",
    ]


def test_sin_partida_previa_no_crea_archivo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "data" / "world.db"

    assert main(["world", "reset", "--db", str(db), "--yes", "--seed", "3"]) == 0

    assert "no habia partida previa" in capsys.readouterr().out
    assert not (db.parent / "archivo").exists()
    tick, poblacion, seed = _instantanea(db)
    assert (tick, seed) == (0, 3)
    assert MIN_INDIVIDUOS <= poblacion <= MAX_INDIVIDUOS


def test_sin_db_usa_data_world_db_y_avisa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    assert main(["world", "reset", "--yes", "--seed", "4"]) == 0

    assert "sin --db" in capsys.readouterr().err
    db = tmp_path / "data" / "world.db"
    assert db.is_file()
    assert _instantanea(db)[:2] == (0, 12)
