# implementer · F2-CONTRATO

- **Fecha:** 2026-11-19
- **Veredicto:** ok

## Qué cambié (ronda 2: bloqueante del reviewer)

- `tribal/llm/candidatas.py` — invariante real: si tras el filtro queda 1, añade `moverse` a un tile pisable (con su `destino`) y, si no lo hay, `descansar`; en un mundo sin terreno pisable devuelve 1 y el borde queda documentado. Docstring corregido (nada de «siempre»).
- `tribal/sim.py` — `_hay_dilema(individuo, mundo, opciones=None)` exige además `len(candidatas) >= 2`; `_intencion_llm` resuelve `moverse` con `instinto.deambular` al aplicar.
- `tribal/llm/decision.py` + `cliente.py` — el prompt usa `cliente.ejemplos` (few-shot inyectable).
- `tribal/llm/cola.py` — `corregidas` se cuenta en `drenar` tras la ventana: una corrección tardía descartada ya no suma.
- `tribal/cli.py` — `--escenarios > 20` avisa por stderr y ejecuta la batería completa (20), sin truncar en silencio.
- `tests/test_llm_candidatas.py` — casos `(100,0)` sin recursos, `(45,60)` sin recursos y mundo sin tiles pisables; test renombrado.
- `tests/test_llm_decision.py` — few-shot inyectado por cliente.
- `tests/test_llm_cola.py` — corrección tardía no cuenta; corrección en ventana sí.
- `tests/test_llm_eval.py` — aviso de `--escenarios > 20`.
- `README.md`, `vault/01_PROYECTO/arquitectura.md` §2.3 — invariante verdadera y borde.

## Bloqueante: invariante 2–4

Reproducción corregida (mismo script que usó el reviewer):

```text
mundo 24×24 de hierba, sin recursos, vecinos ni depredadores
Necesidades(energia=100.0, sed=0.0):  ['moverse', 'descansar']   _hay_dilema=False
Necesidades(energia=45.0, sed=60.0):  ['descansar', 'moverse']   _hay_dilema=True
mundo todo agua (sin tiles pisables), (45,60): ['descansar']      _hay_dilema=False
```

Tests que lo muerden:

```
tests/test_llm_candidatas.py::test_sin_recursos_ni_vecinos_la_segunda_es_moverse
tests/test_llm_candidatas.py::test_el_dilema_sin_recursos_tambien_deja_dos_candidatas
tests/test_llm_candidatas.py::test_sin_tiles_pisables_queda_una_y_no_se_pide_decision
tests/test_llm_candidatas.py::test_candidatas_entre_dos_y_cuatro_con_dos_acciones_viables
```

La invariante documentada ahora es: **2–4 siempre que existan al menos dos
acciones viables**; sin ninguna salida física, 1 y no se pide decisión.

## No bloqueantes arreglados

- Few-shot inyectable: `decidir_con_candidatas` pasa `cliente.ejemplos` a `construir_prompt`; test `test_el_payload_usa_los_ejemplos_del_cliente`.
- `corregidas` al aceptar, no al resolver: `test_correccion_tardia_no_cuenta_como_corregida` (0) y `test_correccion_aceptada_cuenta_como_corregida` (1).
- `--escenarios > 20`: `test_llm_eval_avisa_si_se_piden_mas_escenarios_que_la_bateria` (stderr con el tope y 20 ejecutados).

## Evidencia

### `uv run pytest -q`

```
878 passed, 15 skipped in 225.45s (0:03:45)
```

F2-002 verde en la suite completa: `tests/test_llm_cola.py` (cola, ventana,
cierre sin hilos, 1200 ticks con backend de 200 ms, determinismo del stub entre
procesos) pasa dentro de esos 878.

### `--llm off` idéntico

```
uv run python -m tribal run --headless --json --ticks 120
```

El JSON no incluye la clave `llm` (misma salida que HEAD; el camino `off` no
toca `candidatas`). Stub síncrono:

```json
{"peticiones":20,"aplicadas":18,"descartadas":0,"fallos":0,"corregidas":0,"en_vuelo":0}
```

### `uv run ruff check` + `ruff format --check` + `mypy`

```
All checks passed!
63 files already formatted
Success: no issues found in 63 source files
```

### `uv run python -m tribal llm eval --json`

```json
{"escenarios": 20, "aciertos": 20, "acierto": 1.0, "corregidas": 0, "sin_decision": 0, "backend": "simulado"}
```

### Gate (equivalente a `./init.sh`, que no corre sin bash en Windows)

```json
{"success": true, "agent": "harness", "action": "gate", "message": "ENTORNO LISTO — se puede trabajar.", "data": {"ready": true, "errors": 0, "warnings": 0, "checks": [{"status": "ok", "check": "pytest", "detail": "322 passed in 158.27s (0:02:38)"}]}}
```

## Qué falta

- Medir `tribal-llm` real con `llm eval --backend http` (sin Ollama en este entorno).
- El `llm eval` con backend simulado es circular por diseño (mide contrato/filtrado, no precisión real); queda dicho también en README y `eval.py`.
