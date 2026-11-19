# reviewer · HARD-2

- **Fecha:** 2026-11-19
- **Veredicto:** aprobado

# reviewer — HARD-2

- **Fecha:** 2026-11-19
- **Veredicto:** aprobado
- **Puerta (esta sesión):** `success: true` · `ready: true` · `errors: 0` · `warnings: 0` · pytest `397 passed in 209.02s`
- **Diff revisado:** `README.md`, `vault/01_PROYECTO/arquitectura.md`, `tribal/{cli,sim}.py`, `tribal/llm/{cliente,cola,esquema}.py`, `tests/test_endurecimiento.py`, `tribal.Modelfile` (+ estado de feature escrito por `harness`).

## Criterios

1. **10 semillas con backend falso, resumen reproducible y cierre sin fugas — CUMPLIDO.**
   `uv run pytest tests/test_endurecimiento.py -q` → `19 passed in 13.01s` (repetido 3 veces, incluida la última tras revertir mutaciones).
   Leído el test: `SEMILLAS = range(1, 11)`, dos `subprocess.run` de
   `-m tribal run --headless --json --llm stub --llm-sincrono --ticks 300 --seed N`
   y `assert primera == segunda` (stdout **byte-idéntico**), más
   `resumen["llm"]["peticiones"] > 0` (el stub sí decide) y `en_vuelo == 0`.
   El hilo: `test_cola_asincrona_se_cierra_sin_hilo_ni_peticiones_en_vuelo`
   arranca la cola asíncrona real, corre 300 ticks, cierra y comprueba
   `cerrada is True`, `en_vuelo == 0` y que `threading.enumerate()` no contiene
   `NOMBRE_HILO` (`tribal-llm`).
   Verificado además a mano el cierre que el test no cubre: `run_muestreado(...,
   cola=ColaLLM(...))` asíncrona → tras volver solo queda `MainThread`,
   `en_vuelo 0`.

2. **`report telemetry --json` con las 5 métricas — CUMPLIDO.**
   `uv run python -m tribal report telemetry --json --llm stub --ticks 600 --intervalo 60`
   → objeto con `llm: "stub"` y **10** muestras; cada una lleva
   `llm: {peticiones, aplicadas, descartadas, fallos, latencia_ms_media}`.
   Contadores acumulativos coherentes (tick 300 → `8/1/0/0/0.1`; tick 600 →
   `112/51/0/0/0.1`).
   Sin LLM: `report telemetry --json --ticks 120 --intervalo 60` → `llm: "off"`
   y ninguna muestra con bloque `llm` (test explícito, en verde).
   **Latencia real, no inventada:** no me fío del stub (≈0), así que inyecté un
   transporte falso que duerme 40 ms por inferencia y corrí la cola síncrona
   sobre 300 ticks: `peticiones 7`, `latencia_ms_media 40.6` — mide el reloj
   real alrededor de `decidir_con_candidatas` (`perf_counter` + `_cerrojo`).
   `--llm-sincrono` con `--llm http` se rechaza con exit 2 y mensaje en stderr.

3. **README y arquitectura documentan arranque, degradación y backend falso — CUMPLIDO.**
   README: sección «Arranque de Ollama y el modelo `tribal-llm`» con
   `ollama serve`, `ollama pull qwen2.5:3b-instruct-q8_0`,
   `ollama create tribal-llm -f tribal.Modelfile`, `selfcheck`, degradación sin
   backoff, backend falso (`--llm stub`, `backend_falso`, conftest bloquea red) y
   coste/latencia; `report telemetry` documenta el bloque `llm` y sus 5 campos.
   Arquitectura §2.3/§3/§8 actualizadas con `modelo_presente`, telemetría LLM y
   el modo reproducible.
   **`tribal.Modelfile` contrastado con stack §2:** `FROM qwen2.5:3b-instruct-q8_0`,
   `PARAMETER num_ctx 8192`, `temperature 0.7`, `top_p 0.9`, `repeat_penalty 1.1`
   — coincidencia exacta. Validación sin `ollama create` (ya existe el alias, no
   lo recreo): `ollama show tribal-llm --modelfile` devuelve ese mismo `FROM`
   (mismo blob `sha256-4420ccb0…` que el modelo base) y esos mismos cuatro
   `PARAMETER`. Sintaxis válida (FROM primero, solo `PARAMETER`, comentarios `#`)
   y el modelo base está instalado, así que `ollama create` es viable.

4. **`harness gate success=true` — CUMPLIDO.** Ejecutado en esta sesión:
   `success: true`, `ready: true`, `errors: 0`, `warnings: 0`,
   `pytest 397 passed in 209.02s` (gate corre `pytest tests/`; el total con
   `agents/tests` es el de abajo).

## Mutaciones (para comprobar que los tests muerden)

| Mutación aplicada | Resultado | ¿Muerde? |
|---|---|---|
| Quitar el rechazo de campos extra en `esquema.validar` | `test_validar_rechaza_campos_extra…` FAILED | **sí** |
| `_modelo_en_tags(...) → return True` siempre | 2 parametrizaciones de `test_selfcheck_reporta_si_el_modelo_esta_en_tags` FAILED | **sí** |
| `ColaLLM.latencia_ms_media → return 0.0` | `19 passed` | **no** (ver no bloqueante 1) |
| Quitar `cola.cerrar()` del `finally` de `run_muestreado` | `19 passed` | **no** (ver no bloqueante 2) |

Todas las mutaciones se revirtieron: `git diff --stat` vuelve a los 9 ficheros +
210/−58 del informe y `pytest tests/test_endurecimiento.py -q` → 19 passed.

## Regresiones y alcance (verificado por mí)

- `uv run pytest -q` → **953 passed, 15 skipped in 293.22s** (coincide con el informe).
- `uv run ruff check tribal/ tests/ agents/` → `All checks passed!`
- `uv run ruff format --check tribal/ tests/` → `74 files already formatted`
- `uv run mypy tribal/ tests/` → `Success: no issues found in 74 source files`
- 60 fps: `tests/test_cli_run.py::test_benchmark_cabe_en_el_presupuesto_de_frame`
  (`< 16.67 ms`) en verde; `tests/test_llm_cola.py` (tick < `MS_FRAME` con
  inferencia lenta) y `tests/test_diario.py` (400 ms/inferencia) dentro de los
  953 verdes. `MS_FRAME` intacto.
- F2-002/003/004/005/006 intactos: `git diff` no toca `tribal/core`,
  `tribal/agents`, `tribal/culture` ni `tribal/ui`; los cambios en `llm/` son
  aditivos (latencia, `modelo_presente`, campos extra) y sus tests siguen en
  verde dentro de los 953. `tribal/llm/decision.py` y `gate_f2.py` sin tocar.
- Alcance: sin dependencias (`pyproject.toml`/`uv.lock` fuera del diff), sin
  `.tmp-*` (búsqueda recursiva vacía), sin `opencode.json`, `docs/` ni `art/` en
  el diff. `harness/featureslist.json` y `current.md` llevan el formato que
  escribe `harness start`/`CURRENT_TEMPLATE`, no edición manual visible.
- `doctor checkup` → `7/7 verificaciones superadas`.
- Cobertura dirigida (`tests/test_endurecimiento.py tests/test_llm_cola.py
  --cov=tribal/llm`): 72 % total; `cliente.py` 74 %, `cola.py` 83 %,
  `esquema.py` 91 %.

## Bloqueantes

_(ninguno)_

## No bloqueante

1. **La latencia no está protegida por test.** Cambiar `latencia_ms_media` por
   `0.0` deja los 19 en verde; el test solo exige `isinstance(..., float)`.
   Funciona (medí 40.6 ms con transporte que duerme 40 ms), pero un test con un
   transporte que duerma >1 ms y `assert latencia >= 1.0` cerraría la regresión.
2. **El cierre automático de `run_muestreado` tampoco.** Quitar `cola.cerrar()`
   del `finally` no rompe ningún test: el test de hilos cierra la cola a mano.
   En ejecución sí cierra (lo comprobé: solo `MainThread`, `en_vuelo 0`), pero
   un `assert all(h.name != NOMBRE_HILO ...)` tras `run_muestreado`/`report
   telemetry --llm stub` (asíncrono) lo blindaría.
3. Ramas de cuerpo roto de `/api/tags` (`_modelo_en_tags`) sin cubrir: el test
   solo inyecta JSON válido. `cliente.py` queda al 74 % en la corrida dirigida.
4. `secrets scan` → 13 hallazgos, **todos** en `agents/tests/test_redaction.py` y
   `agents/tests/test_secrets_agent.py` (cadenas de prueba del propio detector):
   preexistente y fuera del diff de HARD-2.
5. `test coverage_report` agotó los 600 s del agente (suite completa con `--cov`);
   no es un fallo del código. Cobertura dirigida arriba como sustituto.
6. `review review_package` → 20 hallazgos (10 estructurales + 10 deep scan), todos
   en funciones preexistentes (`build_parser` 357 líneas, `step`, `resumen`,
   `validar` de `config.py`…). Esta feature añade dos argumentos a `build_parser`
   y ~40 líneas a `resumen`; no introduce funciones nuevas largas.
7. Matiz de doc: el README mantiene «Es determinista: mismos `--seed`…» para
   `report telemetry`; con `--llm stub` **asíncrono** los contadores dependen del
   planificador. El propio README fija `--llm-sincrono` como modo reproducible dos
   párrafos antes, pero la frase genérica invita a confusión.

## Cómo lo verifiqué

```bash
uv run python -m agents --json run harness gate                    # success=true, 397 passed
uv run pytest tests/test_endurecimiento.py -q                      # 19 passed
uv run pytest -q                                                   # 953 passed, 15 skipped
uv run ruff check tribal/ tests/ agents/                           # All checks passed!
uv run ruff format --check tribal/ tests/                          # 74 files already formatted
uv run mypy tribal/ tests/                                         # Success (74 files)
uv run python -m tribal report telemetry --json --llm stub --ticks 600 --intervalo 60
uv run python -m tribal report telemetry --json --ticks 120 --intervalo 60
uv run python -m tribal llm selfcheck --json                       # modelo_presente true, exit 0
uv run python -m tribal llm selfcheck --json --endpoint http://127.0.0.1:9   # null, exit 0
uv run python -m tribal llm selfcheck --json --modelo modelo-que-no-existe   # false, exit 0
ollama show tribal-llm --modelfile                                 # FROM/params == tribal.Modelfile
ollama show qwen2.5:3b-instruct-q8_0 --modelfile                   # mismo blob FROM
uv run python -m agents --json run review review_package
uv run python -m agents --json run secrets scan
uv run python -m agents --json run doctor checkup                  # 7/7
```
