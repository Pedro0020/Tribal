# implementer · HARD-2

- **Fecha:** 2026-11-19
- **Veredicto:** ok

## Qué cambié

- `tests/test_endurecimiento.py` — cierra los tres huecos del reviewer con 6 tests nuevos (sin tocar producto):
  - `test_latencia_media_mide_el_tiempo_del_transporte`: transporte que duerme 40 ms, cola síncrona, `assert latencia_ms_media >= 20.0`.
  - `test_run_muestreado_cierra_la_cola_asincrona`: `run_muestreado(..., cola=ColaLLM(backend_stub()))`; al volver exige `en_vuelo == 0` y ningún hilo `tribal-llm` en `threading.enumerate()`.
  - `test_selfcheck_sobrevive_a_un_cuerpo_de_tags_roto` (4 parametrizaciones): JSON corrupto, `models: []`, `models` no lista y objeto vacío → `disponible=true`, `modelo_presente=false`, exit 0.

## Mutaciones (verificación de que muerden)

| Mutación | Resultado | ¿Muerde? |
|---|---|---|
| `ColaLLM.latencia_ms_media → return 0.0` | `test_latencia_media_mide_el_tiempo_del_transporte` FAILED (`assert 0.0 >= 20.0`) | **sí** |
| Quitar `cola.cerrar()` del `finally` de `run_muestreado` | `test_run_muestreado_cierra_la_cola_asincrona` FAILED (`assert 4 == 0` en `en_vuelo`) | **sí** |

Ambas mutaciones revertidas; `git diff --stat` vuelve a los 9 ficheros con 210/‑58 y el producto queda intacto.

## Evidencia

```
$ uv run pytest tests/test_endurecimiento.py -q
25 passed in 15.10s

$ uv run pytest -q
959 passed, 15 skipped in 373.10s (0:06:13)

$ uv run ruff check tribal/ tests/ agents/
All checks passed!
$ uv run ruff format --check tribal/ tests/
74 files already formatted
$ uv run mypy tribal/ tests/
Success: no issues found in 74 source files

$ uv run python -m agents --json run harness gate
{"success": true, "message": "ENTORNO LISTO — se puede trabajar.",
 "data": {"ready": true, "errors": 0, "warnings": 0, ...,
          "checks": [..., {"status": "ok", "check": "pytest", "detail": "403 passed in 373.69s (0:06:13)"}]}}
```

## Qué falta

Nada. Sin cambios de producto ni dependencias; sin commit.
