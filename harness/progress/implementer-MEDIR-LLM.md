# implementer · MEDIR-LLM

- **Fecha:** 2026-11-20
- **Veredicto:** ok

# MEDIR-LLM — segunda pasada del implementer

## B1 — ancla de la intención caducada

Añadido `test_una_intencion_caducada_cuenta_instinto_no_llm` (cola stub, un
individuo, `intencion_llm = ("descansar", 0)` y `step()` sube el reloj a 1). Aserta
el bloque completo:

```python
acciones == {"llm": 0, "instinto": 1, "total": 1, "pct_llm": 0.0,
             "por_tramo": [{"tramo": 0, "llm": 0, "instinto": 1, "pct_llm": 0.0}]}
```

## Mutaciones verificadas (las tres)

| Mutación en `tribal/sim.py` | Resultado |
|---|---|
| `decidida_llm = intencion is not None` (contar no aplicable/corregida) | cae `test_una_intencion_no_aplicable_cuenta_instinto_no_llm` |
| `self._contar_accion(True)` al drenar la cola (contar encoladas) | cae `test_el_resumen_publica_acciones_llm_e_instinto_por_tramo` |
| quitar `if tick > hasta: return None` (contar caducada) | cae `test_una_intencion_caducada_cuenta_instinto_no_llm` |

Salida literal de cada corrida mutada:

```
FAILED tests/test_medir_llm.py::test_una_intencion_no_aplicable_cuenta_instinto_no_llm
1 failed, 7 passed in 4.88s

FAILED tests/test_medir_llm.py::test_el_resumen_publica_acciones_llm_e_instinto_por_tramo
1 failed, 7 passed in 4.93s

FAILED tests/test_medir_llm.py::test_una_intencion_caducada_cuenta_instinto_no_llm
1 failed, 7 passed in 4.99s
```

Las tres mutaciones se revirtieron; el árbol final es el limpio (8 passed en
`tests/test_medir_llm.py`).

## No bloqueantes cerrados

- **`por_tramo` sin huecos.** `_acciones_json` recorre `range(tramos)` con
  `tramos = (tick - 1) // ticks_telemetria + 1`, así que los tramos sin acciones
  aparecen con `llm=0, instinto=0, pct_llm=0.0`. Docstring y README actualizados.
  Test: `test_los_tramos_sin_acciones_se_incluyen` (tribu sin individuos, 120
  ticks → tramos `[0, 1]` con total 0).
- **SAVE.** `test_los_contadores_de_acciones_sobreviven_a_reanudar`: 600 ticks con
  stub a `db`, reanudar otros 600; los contadores parciales se conservan
  (`llm >= parcial`, `instinto >= parcial`), `total == llm + instinto` y hay 20
  tramos.
- **§2.12 de auditoria-llm.md.** El «cubre el 95 %» pasa a «el resto de las
  acciones … 100 % real y ≈90,5 % con el stub», con la referencia a MEDIR-LLM §1.

## Evidencia

`uv run ruff check tribal/ tests/ agents/`
```
All checks passed!
```
`uv run ruff format --check tribal/ tests/`
```
91 files already formatted
```
`uv run mypy tribal/ tests/`
```
Success: no issues found in 91 source files
```
`uv run pytest -q`
```
........................................................................ [  6%]
........................................................................ [ 13%]
........................................................................ [ 20%]
........................................................................ [ 26%]
........................................................................ [ 33%]
........................................................................ [ 40%]
........................................................................ [ 47%]
........................................................................ [ 53%]
........................................................................ [ 60%]
........................................................................ [ 67%]
........................................................................ [ 74%]
........................................................................ [ 80%]
..............................................................s.sssssssss [ 87%]
ssss..s................................................................. [ 94%]
............................................................             [100%]
1054 passed, 15 skipped in 419.07s (0:06:59)
```
`uv run python -m agents --json run harness gate`
```json
{"success": true, "message": "ENTORNO LISTO — se puede trabajar.",
 "data": {"ready": true, "errors": 0, "warnings": 0,
          "checks": [..., {"status": "ok", "check": "pytest",
                           "detail": "498 passed in 342.37s (0:05:42)"}]}}
```

## Qué falta

Nada bloqueante. Sin commit.
