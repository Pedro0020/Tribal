# implementer · F2-004

- **Fecha:** 2026-11-19
- **Veredicto:** ok

## Qué cambié (ronda 2, tras rechazo del reviewer)

- `tests/test_saliencia.py`: 4 tests nuevos que muerden —`test_la_saliencia_manda_frente_al_orden_de_la_lista` (B1: ids 1/2/3, saliencia en el 3, `max_pensando=1`), `test_el_motor_decae_la_saliencia_cada_tick` (B2: 200 `step()` sin hitos ≈ `5.0 * DECAIMIENTO**200`), `test_el_hito_de_crisis_llega_a_los_600_ticks_y_se_reinicia_al_salir` y `test_step_aplica_el_hito_de_crisis` (B3: 599 no, 600 sí, salir reinicia; la llamada del tick también se prueba)—. Total: 16 tests.
- `README.md`: el ejemplo numérico pasa a `--llm stub --llm-sincrono` (reproducible, dos corridas idénticas) y se advierte de que el asíncrono varía; se documenta que `max_en_vuelo` solo puede ser >0 con la cola asíncrona.
- `tribal/sim.py`: solo docstring de `_saliencia_json` (nota de `max_en_vuelo` en síncrono). Sin cambios de comportamiento.

## Criterios

1. **B1 — la saliencia manda, no el orden de la lista.** `test_la_saliencia_manda_frente_al_orden_de_la_lista`: las 40 peticiones van al id 3 y el id 1 recibe 0.
2. **B2 — decaimiento en el motor.** `test_el_motor_decae_la_saliencia_cada_tick`: `5.0 * 0.999**200 = 4.093244…` tras 200 `step()` sin hitos.
3. **B3 — hito de crisis.** `_hito_crisis`: 599 ticks no suben; el 600 suma `SUBIDA["crisis"]`; al salir de la crisis el contador se reinicia. `test_step_aplica_el_hito_de_crisis` comprueba además que `step()` llama al hito.
4. **Sin regresiones.** 907 passed / 15 skipped; ruff, format, mypy y gate en verde.

## Evidencia

Mutaciones sobre `tribal/sim.py` (sha256 final `F11DE7E4234E6847F4254236EDC7FBA98E44090C54FCEEE0C9DEF37D3BEBE248`, restaurado idéntico tras cada una):

```text
A  quitar con_dilema.sort(...)        -> FAILED test_la_saliencia_manda_frente_al_orden_de_la_lista  (1 failed, 15 passed)
B  quitar el bucle saliencia.decaer   -> FAILED test_el_motor_decae_la_saliencia_cada_tick            (5.0 != 4.093244)
C  quitar self._hito_crisis(en_crisis)-> FAILED test_step_aplica_el_hito_de_crisis                    (0.0 != 0.5)
C  cuerpo de _hito_crisis a no-op     -> FAILED test_el_hito_de_crisis... y test_step_aplica...        (2 failed, 14 passed)
hash restaurado tras cada mutación: F11DE7E4…EBE248
```

```text
$ uv run pytest -q tests/test_saliencia.py
................                                                         [100%]
16 passed in 3.73s

$ uv run python -m tribal run --headless --json --llm stub --llm-sincrono --ticks 1200
{"top": [[5, 0.657], [2, 0.455], [8, 0.304]],
 "pensamientos": {"2": 1, "3": 287, "5": 173, "6": 1, "9": 307, "10": 2,
                  "11": 360, "12": 298, "13": 4},
 "max_pensando": 4, "max_en_vuelo": 0}
dos ejecuciones: JSON byte-idéntico (iguales: True)

$ uv run pytest -q
907 passed, 15 skipped in 249.02s (0:04:09)

$ uv run ruff check tribal tests agents
All checks passed!
$ uv run ruff format --check tribal tests
68 files already formatted
$ uv run mypy tribal tests
Success: no issues found in 68 source files

$ ./init.sh   (Git Bash; PowerShell no trae make/bash)
  ✔ pytest                 351 passed in 178.45s (0:02:58)
━━ ENTORNO LISTO ━━  0 aviso(s)

$ uv run python -m agents --json run harness gate
  "success": true, "ready": true, "errors": 0, "warnings": 0   (351 passed in 178.22s)
```

## Qué falta / avisos

- Nada de F2-004. Sin commit.
- **Aviso, no lo toqué yo**: `git status` muestra `opencode.json` modificado con un servidor MCP `pixellab` que incluye un `Authorization: Bearer pixl_…`. Lo inyectó el entorno durante la sesión; no forma parte de esta feature y no debe commitearse tal cual (el token quedaría en el repo).
