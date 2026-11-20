# implementer · MEM-LOOP

- **Fecha:** 2026-11-20
- **Veredicto:** ok

## Qué cambié

- `tribal/llm/embeddings.py`: nuevo `Recuerdo(id, texto, individuo_id, tick, tipo, score)`;
  el índice guarda el texto y la metaindividual. `buscar` devuelve esos recuerdos (top-k por
  coseno) y `recuperar(consulta, individuo_id, k)` filtra propios + tribales (`None`).
  `a_contexto()` publica `{id, texto, score}` con el texto recortado a
  `MAX_TEXTO_RECUERDO=160`.
- `tribal/sim.py`: `_recuperar_memoria` usa `recuperar` y el contexto de la `Peticion` lleva
  `memoria: [{id, texto, score}]`. `_registrar_recuerdo` acepta `individuo_id`, `tipo` y
  `tick`. `_drenar` indexa la narración al entrar en el diario (`narracion_<i>`) y el diálogo
  de cada decisión (`dialogo_<i>`, individuo emisor). Hitos de cultura siguen siendo tribales.
- `tests/test_memoria.py` (nuevo): filtro por individuo, texto literal en la `Peticion`,
  narración y diálogo indexados y recuperables en ticks posteriores, determinismo.
- `tests/test_embeddings.py`: adaptado a `Recuerdo` y al contexto con `texto`.
- `README.md` (memoria por individuo y texto recuperado), `vault/01_PROYECTO/arquitectura.md`
  (§2.3) y `vault/01_PROYECTO/auditoria-llm.md` (D1-D3 marcados resueltos).

## Criterios de aceptación

1. **La recuperación inyecta el TEXTO del recuerdo en el contexto, no solo id y score.**
   `uv run pytest -q tests/test_memoria.py::test_el_contexto_lleva_el_texto_del_recuerdo`
   (captura la `Peticion` y comprueba `memoria[n]["texto"]`).
2. **La narración y el diálogo se indexan y son recuperables por similitud en ticks posteriores.**
   `uv run pytest -q tests/test_memoria.py::test_la_narracion_se_indexa_y_se_recupera_despues tests/test_memoria.py::test_el_dialogo_se_indexa_y_se_recupera_despues`.
3. **La memoria se asocia al individuo: no se recuperan recuerdos de otro sin vínculo.**
   `uv run pytest -q tests/test_memoria.py::test_recuperar_no_cruza_individuos` (A ve lo suyo,
   B no; ambos ven lo tribal).

## Evidencia

```
$ uv run ruff check tribal/ tests/ agents/
All checks passed!
$ uv run ruff format --check tribal/ tests/
92 files already formatted
$ uv run mypy tribal/ tests/
Success: no issues found in 92 source files
$ uv run pytest -q
1085 passed, 15 skipped in 399.44s (0:06:39)
```

Puerta `./init.sh`:

```
== init.sh · arnés de Tribal ==
Entorno   python 3.12 · uv 0.10.7 · venv presente
Arnés     AGENTS.md, featureslist.json, current.md, history.md, subagentes OK
Backlog   featureslist 54 features · 7 pending · 1 in_progress · 39 done · 7 blocked
Proyecto  tribal/ · pyproject · 43 ficheros de test
Verificación  pytest 503 passed in 335.24s
== ENTORNO LISTO ==  0 aviso(s)
```

## Qué falta

- Los vínculos que ampliarían la visibilidad de memoria (familia/alianzas) llegan con `SOCIAL`.
- `recuerdos` en SQLite sigue escribiéndose vacía: reanudar con LLM no reconstruye el índice.
