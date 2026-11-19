# implementer · F2-003

- **Fecha:** 2026-11-19
- **Veredicto:** ok

## Qué cambié (ronda 2)

- `tribal/llm/http.py` (nuevo): `Transporte` + `transporte_http`, compartidos por cliente y embeddings; se eliminan las dos copias idénticas.
- `tribal/llm/cliente.py` y `tribal/llm/embeddings.py`: usan el helper; en embeddings el coseno pasa a `zip(..., strict=True)`.
- `tribal/sim.py`: también indexa las tradiciones (`origen=interaccion`) al registrarse; docstring de `_registrar_recuerdo` acotado a árbol, combinación y tradición.
- `tests/test_embeddings.py`: test de integración de 300 ticks con `ColaLLM(ClienteLLM(transporte=backend_stub()), sincrona=True)` que captura las `Peticion`; test de dimensiones distintas en el coseno.
- `README.md` y `vault/01_PROYECTO/arquitectura.md`: qué se indexa (hitos del árbol, combinaciones y tradiciones).

## Criterios

1. **Integración con red de tests** — `test_integracion_indexa_hitos_y_llena_el_contexto`: 300 ticks, `recuperaciones > 0`, `recuerdos > 0`, crecimiento 50→100 ticks, `contexto["memoria"]` en toda petición con `{id, score}`, ids presentes en el índice y scores ordenados. Incluye al menos una tradición indexada.
2. **Mutaciones detectadas** — M1 (renombrar `contexto["memoria"]`): `KeyError: 'memoria'`; M5 (`_registrar_recuerdo` no-op): `assert 0 > 0`; M-dim (`strict=False`): `DID NOT RAISE ValueError`. Código restaurado tras cada prueba.
3. **Dimensiones distintas** — `test_coseno_con_dimensiones_distintas_lanza` exige `ValueError`.
4. **Transporte compartido** — una sola `transporte_http` en `tribal/llm/http.py`.

## Evidencia

```text
$ uv run pytest -q tests/test_embeddings.py
.............                                                            [100%]
13 passed in 1.44s

$ uv run pytest -q
891 passed, 15 skipped in 233.41s (0:03:53)

$ uv run ruff check tribal/ tests/ agents/
All checks passed!
$ uv run ruff format --check tribal/ tests/
66 files already formatted
$ uv run mypy tribal/ tests/
Success: no issues found in 66 source files

$ ./init.sh
  ✔ pytest                 335 passed in 164.45s (0:02:44)
━━ ENTORNO LISTO ━━  0 aviso(s)

$ uv run python -m agents --json run harness gate
  "success": true, "ready": true, "errors": 0, "warnings": 0
```

Mutaciones (aplicadas, test en rojo, restauradas):

```text
M1 contexto["recuerdos"] -> KeyError: 'memoria' en test_integracion...
M5 _registrar_recuerdo return -> assert 0 > 0
M-dim zip(strict=False) -> Failed: DID NOT RAISE ValueError
```

## Qué falta

Nada de F2-003. Sin commit.
