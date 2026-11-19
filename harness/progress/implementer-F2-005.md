# implementer · F2-005

- **Fecha:** 2026-11-19
- **Veredicto:** ok

## Ronda 2 — bloqueante del reviewer corregido

**Bloqueante: el diario se desordena con LLM asíncrono.** `Diario.ultimas(n)`
ordenaba por orden de append (`entradas[-n:]`) mientras `_drenar` anota un
diálogo con `respuesta.tick`, que puede ser anterior al último hito. Ahora
`ultimas` ordena por `tick` con `sorted` estable (empates: orden de llegada) y
corta las `n` mayores; el append no se toca. `resumen()["diario"]["ultimas"]` y
`report diary` usan esa misma función, así que ambos salen cronológicos.

Reproducción (cola asíncrona con transporte de 200 ms, decisión del tick 1 y
`primer_fuego` en el tick 5): `entradas` queda `[5, 1]` —el hecho de llegada— y
`ultimas(2)` / `resumen()["diario"]["ultimas"]` devuelven `[1, 5]`.

Tests nuevos:
- `test_ultimas_ordena_por_tick_aunque_el_append_llegue_tarde` (incluye empates).
- `test_una_decision_tardia_no_desordena_el_diario` (cola asíncrona lenta real).
- `test_report_diary_ordena_una_serie_desordenada` (CLI con `run_sim` monkeypatcheado).

**No bloqueante 1: `primera_palabra`.** Ya no se dispara con `gestos`: los hitos
por nodo son `observar_rayo`→`primer_fuego`, `proto_palabras`→`primera_palabra`,
`ritual`→`primer_rito` y `caza_cooperativa`→`primera_caza_grupo`
(`HITO_POR_NODO`, `sim.py`), porque `gestos` no es una palabra ni
`arte_rupestre` un rito. En la corrida real, `primera_palabra` pasa del tick 85
(gestos) al 86 (`proto_palabras`) y `primer_rito` del 3 al 6 (`ritual`). Tests
actualizados para comprobar que el escalón intermedio no genera entrada.

**No bloqueante 2: no bloquea, fijado por test.**
`test_la_cola_no_bloquea_el_tick_con_un_transporte_lento`: transporte de 400 ms,
10 ticks con un individuo en dilema → `mundo.tick == 10`,
`ms_tick_medio < 16.67` y `en_vuelo >= 1` al terminar.

**No bloqueante 3: documentación.** README y arquitectura §2.4 nombran el nodo de
cada hito, explican el orden por `tick` y cuantifican la narración best-effort
(comparte presupuesto en vuelo con las decisiones; lo que llega tras `cerrar()`
se descarta). `_drenar` deja explícito que un diálogo se anota aunque su emisor
haya muerto.

`opencode.json` no se ha tocado ni está en `git status`.

## Evidencia

```
uv run python -m tribal report diary --json --last 5
{"seed": 42, "ticks": 600, ..., "entradas": 5, "narradas": 0, "dialogos": 0,
 "ultimas": [{"tick": 2, "tipo": "primer_fuego", ...},
             {"tick": 6, "tipo": "primer_rito", ...},
             {"tick": 12, "tipo": "primera_tradicion", ...},
             {"tick": 13, "tipo": "primera_caza_grupo", ...},
             {"tick": 86, "tipo": "primera_palabra", "individuo_id": 11, ...}]}

uv run python -m pytest tests/test_diario.py -q
17 passed in 4.14s

uv run python -m pytest -q
924 passed, 15 skipped in 247.75s (0:04:07)

uv run ruff check tribal/ tests/          → All checks passed!
uv run ruff format --check tribal/ tests/ → 70 files already formatted
uv run mypy tribal/ tests/                → Success: no issues found in 70 source files

uv run python -m agents --json run harness gate
  success=true · ready=true · errors=0 · warnings=0
  pytest: 368 passed in 176.28s (0:02:56)
```

## Qué falta

Nada para los criterios ni para el bloqueante. La pérdida de frases en asíncrono
sigue siendo best-effort por diseño y está cuantificada en README; el modo
reproducible es `--llm stub --llm-sincrono`. No hay persistencia del diario
(`store` es Fase 3). Sin commit.
