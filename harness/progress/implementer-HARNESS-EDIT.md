# implementer · HARNESS-EDIT

- **Fecha:** 2026-11-19
- **Veredicto:** ok

## Corrección de la ronda 2: muté el backlog real

En la ronda 2 reproduje los bloqueantes del reviewer con la CLI en PowerShell, pero **contra el repo real, no contra una copia** — y mi informe afirmó lo contrario. Consecuencia concreta: `HARD-1` pasó de `depends_on: ["F1-004"]` a `[]` (audit 01:43:09Z), porque `--depends_on ""` llega como `True` (PowerShell descarta el argumento vacío) y la semántica elegida para `True` es limpiar. Es decir: la prueba del caso «limpiar» limpió una feature de verdad.

Lo hice creyendo que estaba aislado: copié `featureslist.json` a `%TEMP%` y ejecuté desde ahí con `PYTHONPATH` al repo, pero la raíz del contexto no sale del cwd sino del paquete instalado, así que `edit` escribió en el backlog real. El aislamiento que creía tener no existía.

Restaurada en esta ronda con el propio comando:

```
$ uv run python -m agents --json run harness edit --id HARD-1 --depends_on "F1-004"
success: true · "'HARD-1' corregida (depends_on)." · changes.depends_on before [] → after ["F1-004"]

$ git diff --numstat harness/featureslist.json
4       2       harness/featureslist.json
```

`git diff harness/featureslist.json` vuelve a tener **un único hunk** — el `start` de HARNESS-EDIT (`pending` → `in_progress`, `started`, `review_rounds`) — y `HARD-1` vuelve a `["F1-004"]`. `F2-001` nunca se tocó (`["F1-004"]`).

## Qué cambié (ronda 2 — bloqueantes del reviewer)

- `agents/agents/harness_agent.py`:
  - `edit` valida tipos **al entrar**, antes de tocar nada: `title`, `description`, `criteria`, `depends_on` deben ser `str` o `None`. Cualquier otro tipo (`True`, `3`…) → `success=false` con `needs` y el fichero sin reescribir. Ningún `AttributeError` posible.
  - Semántica elegida y documentada: **`depends_on is True` = limpiar** (equivale a `""`). Es lo que llega al CLI cuando PowerShell descarta `--depends_on ""`, y es la única lectura posible de ese flag. Los demás campos no tienen interpretación: un flag olvidado no es un texto.
  - `--criteria ";"` (lista vacía tras el split) → rechazo con `needs`: una feature sin criterios pasa la puerta por vacuidad.
  - De paso, el mensaje de ciclo recorta el camino de entrada (`SAVE → SAVE` en vez de `F2 → SAVE → SAVE`).
- `agents/tests/test_harness_edit.py`: 9 tests nuevos, todos vía `run()` (camino de la CLI): `title`/`description`/`criteria` en `True` → rechazo con `needs`, backlog byte-idéntico y `title` sigue `str`; `depends_on=True` → limpia con diff correcto; `3` en los cuatro campos → rechazo; `criteria=";"` → rechazo. Total 27.
- `agents/prompts/harness_agent.md`: sección «Flags sin valor (PowerShell)» — `--depends_on ""` funciona igual en bash y PowerShell; **`--depends_on=` no** (el parser no parte por `=`); `--title`/`--description`/`--criteria` sin valor se rechazan. Y los dos rechazos nuevos en la lista.

## Evidencia (ronda 3, tras restaurar)

```
$ uv run pytest -q
797 passed, 15 skipped in 205.85s (0:03:25)

$ uv run pytest agents/tests/test_harness_edit.py -q
27 passed in 5.95s

$ uv run ruff check tribal/ tests/ agents/
All checks passed!
$ uv run ruff format --check tribal/ tests/ agents/tests/test_harness_edit.py agents/agents/harness_agent.py
49 files already formatted
$ uv run mypy tribal/ tests/
Success: no issues found in 47 source files

$ uv run python -m agents.prompts_sync --write   → exit 0 ("Todo estaba ya al día.")
$ uv run python -m agents.prompts_sync           → exit 0

$ uv run python -m agents --json run harness gate
exit=0 · success true · "ENTORNO LISTO — se puede trabajar." · ready true · errors 0 · warnings 0
(pytest del gate: 241 passed)
```

## Qué falta

- `F2-001` y `HARD-1` siguen con `depends_on: ["F1-004"]`: el líder decide si reasignarlas a `F1-006` (done). Esta ronda **no** cambia eso.
- Lección para el arnés: una prueba que escribe no se hace con el contexto real; hay que usar el fixture de test o aislar la raíz de verdad, no confiar en el cwd.
- `add` tiene el mismo agujero de tipos (`--title` sin valor escribiría `True`); fuera del alcance de esta ronda.
