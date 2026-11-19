# reviewer · HARD-1

- **Fecha:** 2026-11-19
- **Veredicto:** aprobado

# reviewer · HARD-1

- **Fecha:** 2026-11-19
- **Veredicto:** aprobado
- **Puerta (esta sesión):** `success: true` · `ready: true` · `errors: 0` · `warnings: 0` · pytest `255 passed in 153.95s`

## Criterios

1. **10 semillas reproducen su resumen exacto — CUMPLIDO.**
   `uv run pytest tests/test_semillas.py -q` → `10 passed in 14.98s`.
   Leído el test (`tests/test_semillas.py`): `SEMILLAS = range(1, 11)`,
   `@pytest.mark.parametrize("seed", SEMILLAS)`, dos `subprocess.run` de
   `-m tribal run --headless --json --ticks 600 --seed N` y
   `assert primera.stdout == segunda.stdout` (bytes, `check=True`), más
   `primera.stdout.decode().splitlines() == [json.dumps(run(600, N,
   headless=True).resumen())]` y comparación de objetos. No es "mismas claves":
   es stdout byte-idéntico entre dos procesos + identidad con el resumen
   en proceso.
   El par (semilla, config) queda cubierto además por
   `tests/test_config.py::test_misma_semilla_y_config_dan_el_mismo_resumen`
   (config no-default, preexistente).

2. **`report telemetry --json` por intervalo — CUMPLIDO.**
   `uv run python -m tribal report telemetry --json --seed 42 --ticks 600 --intervalo 60`
   → objeto con `seed`, `ticks`, `intervalo`, `crisis` y **10** `muestras`
   (ticks 60…600, no 600 filas). Cada muestra trae exactamente
   `tick`, `poblacion`, `divergentes`, `conformistas`, `neutros`, `nodos`,
   `aristas`, `media_energia`, `media_sed` (los 5 campos del criterio + neutros
   y medias).
   Coherencia con el resumen, comprobada por mí con seed 42:
   - tick 60 → 12/3/7/2/15/12/75.56/20.6 == `run(60, 42).resumen()`
     (`poblacion_final 12, n_divergentes 3, n_conformistas 7, n_neutros 2,
     len(nodos) 15, len(aristas) 12, media_energia 75.56, media_sed 20.6`).
   - tick 600 → 16/3/8/5/30/27/75.23/34.51 == `run(600, 42).resumen()`
     (`poblacion_final 16, 3/8/5, len(nodos) 30, len(aristas) 27,
     media_energia 75.23, media_sed 34.51`).
   Determinista: dos ejecuciones idénticas byte a byte ("DETERMINISTA: si,
   identico"). Sin `--json` imprime tabla legible con cabecera
   `tick pob div conf neut nodos aristas energia sed` y 10 filas.
   Bordes: `--ticks 130 --intervalo 60` → muestras 60/120/130 (último tramo
   parcial, como documenta el docstring); `--intervalo 0` y `--ticks 0` → exit 2
   con mensaje en stderr; `--crisis` propaga `crisis: true`.

3. **README y arquitectura al día — CUMPLIDO (números ejecutados, no leídos).**
   - README `{"seed": 42, "ticks": 600, ...}`: **byte-idéntico** al stdout real
     de `run --headless --ticks 600 --json` (comparado programáticamente).
   - README `--seed 7 --benchmark --headless --ticks 600`: reproducido →
     `12 -> 14`, `muertes 1`, `nacimientos 3`, `movidos 13`, `ataques 5`,
     `agrupamiento max 10`, `huidas 105`, `media energia 70.93`,
     `media sed 39.51`, `parches 17`, `migraciones 0`. Idéntico.
     (ms/tick salió 0.64 vs 0.56 en el doc; el propio README advierte que ese
     valor varía entre ejecuciones y no entra en el resumen.)
   - README `report culture --seed 42`: `nodos 30  aristas 27  pct 23.3
     nivel_max 2` y las 30 líneas de nodo, todas idénticas.
   - README partida larga seed 2 / 3000 ticks: `poblacion_final 17`,
     `nacimientos 16`, `muertes 11`, `0 ataques`, `huidas 1078`,
     `migraciones 0`, `agrupamiento_max 13`. Idéntico.
   - README tabla de telemetría: idéntica a la salida real (10 filas).
   - README y §9 "Estado tras Fase 1": `report gate-f1 --seeds 1-10 --ticks
     8000` ejecutado → `S crisis>0 7/10 | S calma<0 7/10 | PRIMARIA True` y
     `div% sube 4/10 | empata 3/10 | baja 3/10`. Coincide con el 7/10-7/10-4/10
     publicado. Tabla de 10 semillas del README idéntica a la salida real.
   - `docs/config-ejemplo.json` coincide con el JSON del README (incluye
     `ticks_migracion: 3000`) y `run --config docs/config-ejemplo.json
     --headless --json --ticks 600` → ok (poblacion_final 16).
   - Arquitectura §9 lista lo que existe (`cli.py` con `hello`/`run`/`culture`/
     `telemetry`/`gate-f1`, `config.py`, `core/`, `agents/`, `culture/`,
     `sim.py` con `run_muestreado`, `ui/`, `gate_f1.py`) y lo que no
     (`tribal/llm/` y `tribal/store/` no existen: comprobado). Los comandos del
     §9 se ejecutan sin error.

4. **Puerta en verde — CUMPLIDO.**
   `uv run python -m agents --json run harness gate` en esta sesión →
   `success: true`, `ready: true`, `errors: 0`, `warnings: 0`,
   `pytest 255 passed in 153.95s`. (`init.sh` corre `pytest tests/`, de ahí 255;
   el `811 passed` del informe es `pytest -q` con `agents/tests` incluido:
   lo ejecuté yo y da `811 passed, 15 skipped in 220.49s`. No hay
   contradicción.)

## Regresiones y alcance (verificado por mí)

- `uv run pytest -q` → `811 passed, 15 skipped in 220.49s` (coincide con el informe).
- `ruff check tribal/ tests/ agents/` → `All checks passed!`
- `ruff format --check tribal/ tests/` → `49 files already formatted`
- `mypy tribal/ tests/` → `Success: no issues found in 49 source files`
- `git diff --stat tribal/core tribal/agents tribal/culture` → **vacío**:
  no se ha tocado ningún mecanismo ni constante. En `tribal/sim.py` y
  `tribal/cli.py` el diff es inserción pura (`muestra`, `run_muestreado`,
  subparser y `_report_telemetry`/`_texto_telemetria`).
- 60 fps: `MS_FRAME = 16.67` intacto y `tests/test_cli_run.py` sigue exigiendo
  `benchmark < 16.67` (en verde). Motor sin pygame: `sim.py` solo importa
  `tribal.ui` de forma perezosa en `run()` con ventana; `tests/test_motor.py` y
  `tests/test_render.py` en verde (25 passed).
- Determinismo: `report telemetry` byte-idéntico en dos ejecuciones;
  `report gate-f1` reproduce la tabla de F1-006.
- `git diff tests/` → solo `tests/test_puerta_f1.py` (3 líneas: añade
  `("tribal/sim.py", "muestra")` a la lista blanca de `temperamento()`, con
  justificación escrita: contar temperamentos para telemetría, no conducta).
  No se ha relajado ninguna aserción.
- Cobertura: `test coverage_report` → 95.0 %, 0 archivos por debajo del 60 %.
- Alcance: sin dependencias nuevas (`git diff pyproject.toml uv.lock` vacío),
  sin ficheros `.tmp-*`, sin cambios en `agents/` ni en `harness/` a mano
  (`current.md` tiene el formato exacto de `CURRENT_TEMPLATE` de
  `harness_agent.start`; el `depends_on` F1-004→F1-006 de HARD-1/F2-001 viene
  de la decisión de `HARNESS-EDIT` ya documentada en `history.md`, no de esta
  feature).
- `doctor checkup` → `7/7 verificaciones superadas`.

## Bloqueantes

_(ninguno)_

## No bloqueante

1. `tribal/sim.py::Simulacion.muestra` vuelve a llamar
   `modulo_genoma.temperamento(...)` en vez de reutilizar `_tramo(individuo)`,
   que existe justo para eso. Reutilizarlo ahorraría la entrada nueva en la
   lista blanca de `test_puerta_f1.py`. Funciona y está justificado, pero es
   duplicación evitable.
2. `report telemetry` no acepta `--individuos` (sí `--config`, que lo lleva).
   No lo pide el criterio; anotado por si se quiere paridad con `run`.
3. `tests/test_telemetria.py` no cubre el último tramo parcial
   (`--ticks` no múltiplo de `--intervalo`). Lo he probado a mano
   (`--ticks 130 --intervalo 60` → 60/120/130) y funciona; falta el test.
4. `_texto_telemetria` imprime `crisis False`/`crisis True` (repr de bool) en
   la cabecera; legible, pero `crisis: no/sí` sería más de CLI.
5. `build_parser` de `tribal/cli.py` crece a 151 líneas (umbral 60 en
   `review review_package`) y `resumen`/`step` ya venían largos. Sigue el estilo
   existente de un subparser por bloque; no lo introduce esta feature, pero el
   subcomando nuevo lo engorda.
6. `README.md` mantiene el epígrafe `## Ejecutar (Fase 0)` justo debajo de
   `## Estado tras Fase 1`. Los números de dentro son correctos (verificados);
   solo el título quedó desfasado.
7. `secrets scan` devuelve 13 hallazgos, **todos** en
   `agents/tests/test_redaction.py` y `agents/tests/test_secrets_agent.py`
   (cadenas de prueba del propio detector). Ninguno en ficheros del diff de
   HARD-1: preexistente, fuera de alcance.
8. `doctor` reporta `tribal v0.1.0` (de `project.yml`) mientras
   `pyproject.toml` va por `0.1.19`. Desajuste preexistente, no lo toca esta
   feature.

## Cómo lo verifiqué (comandos)

```bash
uv run python -m agents --json run harness gate          # success=true, 255 passed
uv run pytest tests/test_semillas.py -q                  # 10 passed
uv run pytest -q                                         # 811 passed, 15 skipped
uv run ruff check tribal/ tests/ agents/                 # All checks passed!
uv run ruff format --check tribal/ tests/                # 49 files already formatted
uv run mypy tribal/ tests/                               # Success
uv run python -m tribal report telemetry --json --seed 42 --ticks 600 --intervalo 60
uv run python -m tribal report telemetry --seed 42 --ticks 600 --intervalo 60
uv run python -m tribal run --headless --ticks 600 --json
uv run python -m tribal run --seed 7 --benchmark --headless --ticks 600
uv run python -m tribal report culture --seed 42 --ticks 600
uv run python -m tribal run --seed 2 --headless --json --ticks 3000
uv run python -m tribal report gate-f1 --seeds 1-10 --ticks 8000
git diff --stat tribal/core tribal/agents tribal/culture   # vacío
uv run python -m agents --json run test coverage_report    # 95.0 %
uv run python -m agents --json run secrets scan            # solo tests de agents/
uv run python -m agents --json run doctor checkup          # 7/7
```
