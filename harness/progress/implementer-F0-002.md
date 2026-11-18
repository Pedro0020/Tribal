# implementer · F0-002

- **Fecha:** 2026-11-18
- **Veredicto:** ok

# Implementer — F0-002 · ronda 3 (aislar supervivencia del depredador)

## Cambios

- `tests/test_motor.py` — supervivencia a 1200 ticks ahora corre con
  `depredador_activo=False` y recursos normales: `muertes == 0`,
  `poblacion_final == poblacion_inicial + nacimientos`, `nacimientos > 0`,
  `depredador.activos == 0`. Prueba que cubrir las necesidades no mata.
- `tests/test_puerta_f0.py` — el test de letalidad afirma la causa:
  `depredador.muertes > 0` y `muertes == depredador.muertes` (presa acorralada).
- `README.md` no cambia (ya no hablaba de este test).

## Mutaciones comprobadas (restauradas después)

Quitar el efecto de `beber` (necesidades sin cubrir) hace fallar la
supervivencia aislada:

```
>       assert resumen["muertes"] == 0
E       assert 12 == 0
FAILED tests/test_motor.py::test_la_tribu_sobrevive_y_se_reproduce_en_un_mundo_con_recursos
1 failed in 0.55s
```

Desactivar `_morder` (sin daño) hace fallar la letalidad:

```
>       assert simulacion.muertes == 1
E       assert 0 == 1
FAILED tests/test_puerta_f0.py::test_el_depredador_mata_a_una_presa_sana_acorralada
1 failed in 0.34s
```

## Evidencia final

`uv run pytest -q`:

```
592 passed, 15 skipped in 68.74s (0:01:08)
```

`uv run ruff check tribal/ tests/ agents/` → `All checks passed!`
`uv run ruff format --check tribal/ tests/` → `27 files already formatted`
`uv run mypy tribal/ tests/` → `Success: no issues found in 27 source files`

`bash init.sh` → `pytest 63 passed in 5.84s`, `━━ ENTORNO LISTO ━━ 0 aviso(s)`
`uv run python -m agents --json run harness gate` → `success: True`,
`ENTORNO LISTO — se puede trabajar.`

## Qué falta

Nada de código. No se tocaron prompts. Versión, CHANGELOG y commit, tras el reviewer.
