# implementer · HARD-000

- **Fecha:** 2026-11-18
- **Veredicto:** ok

# implementer · HARD-000

- **Fecha:** 2026-11-18
- **Veredicto:** ok

## Qué cambié (ronda 2, bloqueantes del reviewer)

- `tribal/config.py`: `validar()` ahora exige tipos antes de mirar rangos — `seed`/`individuos`/`ancho`/`alto` enteros y **no** `bool`, tasas `int|float` y **no** `str`/`bool`; `ancho`/`alto` con mínimo real `MIN_LADO = 9` (`_mancha` pide `randint(4, lado - 5)`). Todo error nombra clave y valor (`f"{nombre} ... (recibido {valor!r})"`). Eliminado el `except TypeError` que filtraba el mensaje crudo de Python: con los tipos validados no hay `TypeError` que traducir.
- `tests/test_config.py`: parametrizado `test_cli_rechaza_config_invalida_sin_traza` con 8 casos (ancho 6, ancho 60.7, tasa_sed "0.2", seed "hola", individuos 5, individuos true, tasa negativa, clave desconocida) que comprueba `exit 2`, `error:` en stderr, el nombre de la clave y `"Traceback" not in stderr`; `test_el_error_de_validacion_nombra_clave_y_valor`; `test_evolucionar_aplica_la_tasa_recibida`.
- `tests/test_config.py`: `test_cambiar_una_tasa_cambia_el_resumen` compara **métricas** (`_metricas()` quita `config`) y además `media_sed`; `test_cli_seed_y_individuos_mandan_sobre_el_fichero` añade `poblacion_inicial == 10`; nuevo `test_dos_ejecuciones_del_cli_con_la_misma_config_son_identicas` (dos `subprocess` con `-m tribal run --headless --json --config ...`, stdout byte a byte).
- `README.md`: la lista de errores ya dice 9×9 mínimo y tipos equivocados, no «mapa no positivo».

## Criterios

1. Validación real (tipos + mínimo 9 + mensaje con clave/valor) → parametrizado CLI de 8 casos (abajo).
2. Test de cambio de parámetro no vacuo → mutación ejecutada: sin pasar tasas en `sim.step`, `test_cambiar_una_tasa_cambia_el_resumen` **falla** (`1 failed, 4 passed`); restaurado, verde.

## Evidencia

```
$ uv run python -m tribal run --headless --json --ticks 30 --config %TEMP%\tribal-cfg-ancho6.json      # {"ancho": 6}
error: ...\tribal-cfg-ancho6.json: ancho y alto deben ser al menos 9 tiles (recibido 6x34)
exit=2

$ ... --config %TEMP%\tribal-cfg-ancho-float.json    # {"ancho": 60.7}
error: ...\tribal-cfg-ancho-float.json: ancho debe ser un entero (recibido 60.7)
exit=2

$ ... --config %TEMP%\tribal-cfg-tasa-str.json       # {"tasa_sed": "0.2"}
error: ...\tribal-cfg-tasa-str.json: tasa_sed debe ser un número (recibido '0.2')
exit=2

$ ... --config %TEMP%\tribal-cfg-seed-str.json       # {"seed": "hola"}
error: ...\tribal-cfg-seed-str.json: seed debe ser un entero (recibido 'hola')
exit=2

$ ... --config %TEMP%\tribal-cfg-bool.json           # {"individuos": true}
error: ...\tribal-cfg-bool.json: individuos debe ser un entero (recibido True)
exit=2

# mutación: sim.step -> necesidades.evolucionar(individuo.necesidades, individuo.genoma)
$ uv run pytest -q tests/test_config.py -k "tasa"
FAILED tests/test_config.py::test_cambiar_una_tasa_cambia_el_resumen - Assert...
1 failed, 4 passed, 17 deselected in 0.52s
# restaurado el cableado

$ uv run pytest -q tests/test_config.py
22 passed in 1.28s
```

## Desbloqueo del commit: una sola versión de ruff

**Causa del fallo del commit (no del código):** `.pre-commit-config.yaml` fijaba
`ruff-pre-commit` en `rev: v0.11.0` (ruff 0.11.0) mientras el entorno dev usa
`ruff 0.16.1`. `UP038` (`isinstance(x, (A, B))` → `A | B`) existe en 0.11 y se
eliminó en las versiones nuevas, así que el hook la pedía y el local ni la
evaluaba: verde en `make lint`, rojo en el hook, sobre el mismo fichero.

**Arreglo:** `rev: v0.16.1` (tag exacto existente en
`astral-sh/ruff-pre-commit`), con comentario que explica por qué se ancla a la
versión de dev. Tras subir el rev **UP038 ya no se emite** (la regla no existe
en 0.16.1), así que no hizo falta tocar `config.py` ni desactivar nada: una
sola política, la de la versión instalada. Verificado que el entorno del hook
es la misma versión que el local:

```
C:\Users\pedro\.cache\pre-commit\repo91zm41gg\py_env-python3.12\Scripts\ruff.exe -> ruff 0.16.1
$ uv run ruff --version -> ruff 0.16.1
```

**Prueba de que hook y local coinciden sobre el conjunto real (sin modificar ficheros):**

```
$ uv run pre-commit run ruff --files tribal/config.py tribal/sim.py tribal/cli.py tribal/core/mundo.py tribal/agents/necesidades.py tests/test_config.py tests/test_cli_run.py
ruff (legacy alias)......................................................Passed

$ uv run pre-commit run ruff-format --files <mismos>
ruff format..............................................................Passed

$ uv run pre-commit run --files (git diff --cached --name-only)
ruff (legacy alias)......................................................Passed
ruff format..............................................................Passed
trim trailing whitespace.................................................Passed
fix end of files.........................................................Passed
check for added large files..............................................Passed
check for merge conflicts................................................Passed
```

```
$ uv run ruff check tribal/ tests/ agents/
All checks passed!

$ uv run ruff format --check tribal/ tests/
25 files already formatted

$ uv run mypy tribal/ tests/
Success: no issues found in 25 source files

$ uv run pytest -q
577 passed, 15 skipped in 63.51s (0:01:03)

$ uv run python -m agents --json run harness gate
  "success": true,
  "message": "ENTORNO LISTO — se puede trabajar.",
```

## Qué falta

- Nada de los dos bloqueantes, del no bloqueante pedido ni del fallo del commit.
  No commiteado: el bump de versión y el commit los hace `git commit_feature`.
