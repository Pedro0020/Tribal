# reviewer · F3-004

- **Fecha:** 2026-11-19
- **Veredicto:** aprobado

## Criterios

1. **Fila cada N ticks (población, divergentes, conformistas, nodos, aristas)** — CUMPLIDO.
   Partida de 6000 ticks por CLI (`run --fresh --db`): 100 muestras, ticks `60..6000`
   exactos, ninguna por frame. `n_divergentes+n_conformistas+n_neutros != poblacion` → 0 filas.
   Nodos/aristas de la última muestra (27/24) == `COUNT(*)` del grafo guardado.

2. **`report telemetry --db … --csv` con cabecera y una fila por muestra** — CUMPLIDO.
   Fichero: 0 bytes CR, 101 LF, sin BOM, UTF-8, cabecera exacta de 9 columnas, 100 filas,
   parseable por `csv.reader`. **stdout: 0 bytes CR, 101 LF y bytes idénticos al fichero**
   (medido con `subprocess` sobre `sys.stdout.buffer`; el test lo cubre con `capsysbinary`,
   ya no con `splitlines()`). `--json` reconstruye las mismas 100 filas.

3. **Test: muestras para 6000/60 y no una por frame** — CUMPLIDO.
   `test_db_escribe_una_muestra_por_intervalo_y_no_por_frame`: `len == 100`, `!= 6000`,
   ticks exactos. Sigue teniendo dientes (mutación per-frame ya tumbaba 4 tests en ronda 1
   y el código de `step` no cambió).

4. **gate** — CUMPLIDO (esta sesión): `harness gate` → `success: true`, `ready: true`,
   `errors: 0`, `warnings: 0`, `pytest 435 passed in 229.38s (0:03:49)`.

## Bloqueante de la ronda 1 — resuelto

Reproduje de cero una BD de F3-003 (partida real de 6000 ticks y luego `DROP TABLE telemetria`
+ recreación con el esquema de 6 columnas + las 100 filas heredadas):
- `report telemetry --db vieja.db --json` y `--csv` → **exit 0**, 100 filas `60..6000`,
  poblaciones heredadas intactas (12, 13, 14, 15…), `neutros`/`media_energia`/`media_sed` a 0,
  columnas añadidas por `ALTER`. **Ninguna fila perdida.**
- `run --db vieja.db` → **exit 2** («la base … ya existe; usa --fresh…») y la base queda
  idéntica: mismo SHA de las filas de `telemetria` antes y después, 100 muestras.
- `run --db vieja.db --fresh` → exit 0, quedan las 2 muestras nuevas `[60, 120]`; repetido
  sobre base ya creada, con base inexistente y con base de 0 bytes → exit 0 en los tres.
- `--fresh` sin `--db` → exit 2. `report db --db` y `export obsidian --db` sobre la base
  migrada → exit 0 (F3-001/002/003 intactos también por lectura).
- Errores: tabla vacía / sin tablas / fichero no-SQLite / ruta inexistente → exit 2 con
  `error: …`, sin traceback.

Resto de lo pedido:
- **Aviso de flags ignorados**: `--seed`, `--ticks`, `--intervalo`, `--config`, `--crisis`,
  `--llm-sincrono` → warning por stderr y exit 0; sin banderas → stderr vacío; `--llm off`
  no avisa (es el valor por defecto). Correcto.
- **CSV a directorio inexistente** → exit 2, `error: no puedo escribir el CSV …`, sin traza.
- **Mutaciones**: quitar `_migrar_telemetria` de la rama `crear=False` → cae
  `test_db_vieja_por_cli_migra_al_leer_y_run_no_borra_el_historico` con
  `sqlite3.OperationalError: no such column: n_neutros`; anular el rechazo
  (`elif False and args.db.exists()`) → cae el mismo test y la base se pisa.
  `repositorio.py`/`cli.py` restaurados con **hash idéntico** al original.
- **Suite**: `uv run pytest -q` → **991 passed, 15 skipped in 295.07s**;
  `ruff check` → All checks passed; `ruff format --check` → 82 files already formatted;
  `mypy tribal/ tests/` → no issues in 82 files.
- **Alcance**: `pyproject.toml`/`uv.lock` intactos, sin `.tmp-*`, sin BDs en el repo,
  `opencode.json` sin tocar; untracked = solo los informes de `harness/progress/`.
  README (líneas 553-604) y `arquitectura.md` describen migración en lectura, rechazo y
  `--fresh` tal como se comporta.

## No bloqueante

- **Base F3-003 + fichero de solo lectura**: `report telemetry` sale 2 con «no es una base
  SQLite válida (attempt to write a readonly database)». No crashea ni pierde datos, pero el
  mensaje engaña: merece detectar el caso y decir que la base necesita escritura para migrarse
  (o leer con `COALESCE` cuando no se pueda migrar). Una base ya migrada sí se lee en solo
  lectura, exit 0.
- `run --db <directorio inexistente>/x.db --fresh` → traceback `sqlite3.OperationalError:
  unable to open database file`, exit 1. **Preexistente** (el `sqlite3.connect` no lo toca este
  diff) y fuera de criterio; lo anoto porque `_run` ya valida otras entradas con `error:` + 2.
- El guard vive en el CLI: `tribal.sim.run(db=…)` desde Python sigue volcando sobre la base
  existente. Coherente con la frontera deliberada (los automatismos pasan por el contrato; el
  código escrito a propósito no), pero conviene que no sorprenda a quien lo llame.
- `--csv` + `--json` a la vez: gana CSV en silencio; `--db` con una ruta que es un directorio
  dice «ya existe».
- `--fresh` borra sin confirmación: el nombre del flag y el README lo dicen; no hay contrato de
  permisos para la CLI del producto.
- `review_package`: duplicación AST entre `_migrar_apagado` y `_migrar_telemetria` (patrón ya
  establecido en el módulo). `secrets scan`: sin hallazgos nuevos (los 10 son fixtures
  preexistentes de `agents/tests/`).
