# implementer · SAVE-001

- **Fecha:** 2026-11-20
- **Veredicto:** ok

## Matices del reviewer SAVE-001 — cerrados

1. **`.gitignore`** — añadido `data/save_meta.json`; `git check-ignore -v data/save_meta.json` → `.gitignore:81`. `*.db`, `*.db-wal`, `*.db-shm` ya cubrían la base.
2. **README** — eliminada la línea duplicada "Salida real de `report db`…" (845/847).
3. **`--fresh` borra la meta vieja** — `_run` elimina `save_meta.json` junto a la base antes de empezar; test `test_fresh_borra_la_meta_de_la_partida_anterior` (meta tick 60 → nueva partida tick 30).
4. **Fallo de meta no aborta** — `Repositorio.guardar` captura `OSError` de `_escribir_meta` y emite `warning: no pude escribir …/save_meta.json`; la base queda commiteada. Test `test_un_fallo_al_escribir_meta_no_aborta_ni_corrompe`: `run` termina en 120, `integrity_check=ok`, reabre y reanuda hasta 130.

README y arquitectura §2.5 actualizados con "un fallo al escribir la meta solo emite warning".

## Evidencia

```
uv run ruff check tribal/ tests/        -> All checks passed!
uv run ruff format --check              -> 88 files already formatted
uv run mypy tribal/ tests/              -> Success: no issues found in 88 source files
uv run pytest -q                        -> 1037 passed, 15 skipped in 394.25s
uv run python -m agents --json run harness gate
  -> success=true, ready=true, errors=0, pytest 481 passed in 320.53s
```

## Qué falta

Nada de estos cuatro matices. Sigue documentado que reanudar con LLM encendido no restaura la memoria indexada (garantía exacta con LLM off). RESET-001 es otra feature. No commiteado.
