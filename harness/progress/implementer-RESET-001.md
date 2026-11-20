# implementer · RESET-001

- **Fecha:** 2026-11-20
- **Veredicto:** ok

## Qué cambié

- `tribal/reset.py` — `archivar()` devuelve `Path | None` y no crea `archivo/` ni mueve meta si no hay base.
- `tribal/cli.py` — `world reset`: mensaje de éxito honesto («no habia partida previa»), plan previo con sidecars `-wal/-shm` y destino `archivo/`, y `--db` sin default en argparse para avisar de `data/world.db` relativo al cwd.
- `.gitignore` — añade `data/` y `*.meta.json` (cubre `archivo/world-<marca>.meta.json` en cualquier ubicación).
- `tests/test_reset.py` — 5 tests nuevos: sidecars, colisión `-2` con reloj fijado, sin partida previa, mensaje previo y default `--db`.
- `README.md` y `vault/01_PROYECTO/arquitectura.md` §2.5 — documentan los dos matices de mensaje.

## Matices del reviewer

1. **Mensaje honesto sin partida** — `archivar` sale por `db.is_file()` y `_world_reset` imprime «no habia partida previa»; `test_sin_partida_previa_no_crea_archivo` comprueba que no existe `archivo/` y que hay mundo nuevo (tick 0, seed 3).
2. **`.gitignore`** — `git check-ignore -v data/archivo/world-20261120T044542Z.meta.json` → `.gitignore:82:data/`; también `data/save_meta.json` y `data/world.db` (exit 0). `*.meta.json` cubre archivos junto a una base fuera de `data/`.
3. **Sidecars y colisión** — `test_archiva_los_sidecars_wal_y_shm` (los `-wal/-shm` desaparecen de la raíz y aparecen junto al `.db` archivado) y `test_colision_de_marca_no_pisa_el_archivo_anterior` (reloj congelado: `world-…Z.db` y `world-…Z-2.db`, con sus dos meta).
4. **Mensaje previo** — nombra sidecars y `archivo/`: `test_el_mensaje_previo_nombra_sidecars_y_archivo`; demo real: «va a archivar … (con sus sidecars -wal/-shm y su save_meta.json) en archivo/ …».
5. **`--yes` sin `--db`** — se mantiene el default y se avisa por stderr: `aviso: sin --db se usa data/world.db relativo al directorio actual`; `test_sin_db_usa_data_world_db_y_avisa` lo comprueba con `monkeypatch.chdir`.

## Evidencia

```
$ uv run pytest tests/test_reset.py -q --no-header
9 passed in 1.21s

$ uv run pytest -q --no-header
1046 passed, 15 skipped in 393.46s (0:06:33)

$ uv run ruff check tribal/ tests/        → All checks passed!
$ uv run ruff format --check tribal/ tests/ → 90 files already formatted
$ uv run mypy tribal/ tests/              → Success: no issues found in 90 source files
```

Comando real (directorio temporal):

```
$ uv run python -m tribal world reset --db ...\world.db --yes --seed 12
nuevo mundo: no habia partida previa  seed 12  tick 0  -> ...\world.db
archivo existe: False

$ uv run python -m tribal world reset --db ...\world.db
error: `world reset` va a archivar ...\world.db (con sus sidecars -wal/-shm y su
save_meta.json) en archivo/ y a crear un mundo nuevo en su lugar; pasa --yes para confirmar
exit=2

$ uv run python -m tribal world reset --db ...\world.db --yes --seed 21
nuevo mundo: archivado en ...\archivo\world-20261120T050126Z.db  seed 21  tick 0  -> ...\world.db
archivo/: world-…Z.db, world-…Z.db-wal, world-…Z.db-shm, world-…Z.meta.json
$ uv run python -m tribal report db --db ...\world.db
seed 21  tick 0  poblacion 12  estacion sin estacion
```

Gate: `"success": true`, `"message": "ENTORNO LISTO — se puede trabajar."`,
`"pytest": "490 passed in 322.79s"`, errors 0 · warnings 0.

## Qué falta

- El menú de ventana «Continuar / Nuevo mundo» (concepto §17) sigue fuera de esta feature.
