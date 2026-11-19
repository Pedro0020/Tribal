# implementer · F3-004

- **Fecha:** 2026-11-19
- **Veredicto:** ok

## Qué cambié (ronda 2)

- `tribal/store/repositorio.py`: `Repositorio(crear=False)` ejecuta `_migrar_apagado` y `_migrar_telemetria` + `COMMIT` tras validar tablas; `ALTER TABLE` no borra filas y las heredadas leen 0 en las columnas nuevas.
- `tribal/cli.py`: `run --db` rechaza una base existente con exit 2 y «usa --fresh para empezar de cero»; `--fresh` borra base/-wal/-shm solo con flag explícito. `--csv` se genera como bytes UTF-8+LF (stdout incluido), errores de escritura → `error:` + exit 2. Con `--db` avisa por stderr de `--seed/--ticks/--intervalo/--config/--crisis/--llm` ignorados.
- `tests/test_telemetria.py`: test por CLI sobre BD F3-003 (100 filas, esquema de 6 columnas): lectura exit 0 con neutros/medias 0; `run --db` exit 2 sin tocar las 100; `--fresh` deja 2 muestras nuevas. Bytes de stdout sin CR, CSV a directorio inexistente exit 2, warning de opciones ignoradas.
- `README.md`, `vault/01_PROYECTO/arquitectura.md`: migración en lectura, rechazo de `run --db` sobre base existente y `--fresh`.

## Criterios

1. Leer BD vieja migra sin borrar y devuelve 100 filas con los tres campos a 0 — test CLI + evidencia.
2. `run --db` sobre existente exit 2 sin borrar — test CLI + evidencia; `--fresh` documentado y probado.
3. Test por CLI (no `crear=True`) cubre los tres pasos — `test_db_vieja_por_cli_migra_al_leer_y_run_no_borra_el_historico`.
4. CSV stdout LF (0 CR), directorio inexistente exit 2 sin traza, warning de opciones ignoradas — tests + evidencia.

## Evidencia

```
report vieja: exit 0 filas 100 primera {'tick': 60, ..., 'neutros': 0, ..., 'media_energia': 0.0, 'media_sed': 0.0}
run existente: exit 2 | error: la base ... ya existe; usa --fresh para empezar de cero
tras rechazo: filas 100
run --fresh: exit 0
tras fresh: ticks [60, 120]
csv stdout: exit 0 bytes CR 0 bytes LF 3
csv dir inexistente: exit 2 | error: no puedo escribir el CSV ...: [Errno 2] No such file or directory
warning: exit 0 | warning: con --db se ignoran --ticks: no se resimula
```

Mutaciones verificadas:
- quitar `_migrar_telemetria` de `crear=False` → el test cae con `sqlite3.OperationalError: no such column: n_neutros`.
- anular el rechazo de `run --db` sobre existente → el test cae (`assert 0 == 2`) y la base se pisa.

```
uv run ruff check tribal/ tests/ agents/   -> All checks passed!
uv run ruff format --check tribal/ tests/  -> 82 files already formatted
uv run mypy tribal/ tests/                 -> Success: no issues found in 82 source files
uv run pytest -q                           -> 991 passed, 15 skipped in 298.48s
bash init.sh                               -> ENTORNO LISTO, 435 passed in 249.41s
harness gate                               -> success: true, ready: true, errors: 0, warnings: 0
```

## Qué falta

Nada de esta feature. No commiteado.
