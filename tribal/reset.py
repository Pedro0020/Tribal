"""Nuevo mundo: archivar o borrar la partida y empezar de cero (concepto §17).

`tribal world reset` no pasa por la puerta de permisos de `agents/contracts`:
esa protege a los agentes del arnés, no a la CLI del juego. La confirmación es
propia y vive en `tribal.cli`: sin `--yes` no se toca nada.

La partida nueva se crea cerrando una simulación de cero ticks, así que pasa
por el mismo camino que `run --db` (esquema, volcado y `save_meta.json`) en vez
de escribir SQLite a mano.
"""

from __future__ import annotations

import random
import shutil
from datetime import UTC, datetime
from pathlib import Path

from tribal.sim import run

#: Tribu inicial de un mundo nuevo: el default de `SimConfig`, dentro de 8-15.
INDIVIDUOS = 12

#: Ficheros de la base que se archivan o borran con ella (WAL y su índice).
_SUFIJOS = ("", "-wal", "-shm")


def semilla_nueva() -> int:
    """Semilla no reproducible: `SystemRandom` lee la entropía del sistema."""
    return random.SystemRandom().randrange(2**31)


def archivar(db: Path) -> Path | None:
    """Mueve la partida y su meta a `<db.parent>/archivo/world-<UTC>.db`.

    La marca de tiempo es UTC con segundos; si dos archivos caen en el mismo
    segundo, el segundo lleva sufijo `-2`, `-3`... para no pisar el anterior.
    Devuelve la ruta del `.db` archivado, o `None` si no había partida: sin base
    no se crea `archivo/` ni se archiva la meta de una partida que no existe.
    """
    if not db.is_file():
        return None
    destino = _ruta_archivo(db)
    destino.parent.mkdir(parents=True, exist_ok=True)
    for sufijo in _SUFIJOS:
        origen = Path(f"{db}{sufijo}")
        if origen.exists():
            shutil.move(str(origen), f"{destino}{sufijo}")
    meta = db.parent / "save_meta.json"
    if meta.exists():
        shutil.move(str(meta), str(destino.with_suffix(".meta.json")))
    return destino


def borrar(db: Path) -> None:
    """Elimina la partida, sus sidecars de WAL y su `save_meta.json`."""
    for sufijo in _SUFIJOS:
        Path(f"{db}{sufijo}").unlink(missing_ok=True)
    (db.parent / "save_meta.json").unlink(missing_ok=True)


def crear(db: Path, seed: int, individuos: int = INDIVIDUOS) -> None:
    """Escribe una partida nueva en `db`: tick 0 y una tribu de `individuos`.

    Cero ticks por el mismo camino que `run --db`: `Simulacion.cerrar()` vuelca
    el mundo recién creado con su `save_meta.json`.
    """
    run(0, seed, headless=True, individuos=individuos, db=db)


def _ruta_archivo(db: Path) -> Path:
    marca = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    sufijo = db.suffix or ".db"
    carpeta = db.parent / "archivo"
    destino = carpeta / f"{db.stem}-{marca}{sufijo}"
    numero = 2
    while destino.exists():
        destino = carpeta / f"{db.stem}-{marca}-{numero}{sufijo}"
        numero += 1
    return destino
