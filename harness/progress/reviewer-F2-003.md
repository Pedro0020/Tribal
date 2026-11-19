# reviewer · F2-003

- **Fecha:** 2026-11-19
- **Veredicto:** aprobado

## Criterios

1. **Interfaz + backend determinista + backend real opcional en CPU — CUMPLIDO.**
   `tribal/llm/embeddings.py`: `Embedder` (Protocol), `EmbedderHashing`
   (blake2b por token, 256 dims, L2) y `EmbedderOllama` (`POST /api/embed`,
   urllib, transporte inyectable) con `usa_gpu=False` en los tres.
   Verificado en esta ronda: norma L2 = 1.0, texto vacío → vector nulo,
   `dim<1` → `ValueError`, Ollama caído (`127.0.0.1:1`) → 1024 ceros con
   `ultimo_error` sin lanzar.

2. **Top-k por similitud y nunca en hilo de render ni del LLM — CUMPLIDO.**
   Orden `(-score, str(id))`. Guarda real: hilo `tribal-llm` (==
   `cola.NOMBRE_HILO`) y recorrido de la pila por `tribal.ui.render`; detecta
   render a 2 niveles vía helper de otro módulo. `app.bucle` hace `step()` y
   render sin anidar, así que no hay falso positivo. Mutación M3 (quitar la
   guarda) → la suite falla.

3. **Top-1 sintético + mismo orden en dos ejecuciones — CUMPLIDO.**
   10 consultas con top-1 exacto; subprocesos con `PYTHONHASHSEED` 1 y 2 con
   vector y orden idénticos; empates `alfa`<`zeta` con inserción invertida.
   Mutaciones M2 (`hash()`) y M4 (sin desempate) detectadas.

4. **`llm selfcheck --json` — CUMPLIDO.**
   `{"...", "embeddings": {"backend": "hashing", "usa_gpu": false, "dim": 256}}`.

5. **`harness gate` success=true — CUMPLIDO.** Ejecutado por mí en esta
   sesión: ver línea al final.

6. **Integración con red de tests (bloqueante de la ronda 1) — CUMPLIDO Y
   REPRODUCIDO.**
   `test_integracion_indexa_hitos_y_llena_el_contexto` usa el camino real
   (`crear` → `step` → `_encolar_dilema` → `ColaLLM.encolar`) sin mocks del
   motor: 300 ticks, `recuerdos > 0`, `recuperaciones > 0`, crecimiento 50→100,
   `contexto["memoria"]` con `{id, score}`, ids presentes en el índice y scores
   descendentes, y al menos una tradición indexada.
   Mutaciones reproducidas por mí, con el código restaurado después:
   - M1 (renombrar `contexto["memoria"]`) → **detectada** (1 failed).
   - M5 (`_registrar_recuerdo` no-op) → **detectada** (1 failed).
   - M-tradiciones (quitar el registro de tradición) → **detectada** (1 failed).
   - M-dim (`zip(..., strict=False)`) → **detectada** (1 failed).
   Evidencia independiente: 600 ticks, seed 7, `--llm stub` →
   `memoria={recuerdos: 22, recuperaciones: 337}` y **22 nodos** (4
   tradiciones); seed 42 por API → 24 recuerdos = 24 nodos, 287 peticiones, 0
   con memoria vacía, 0 ids fuera del índice en el momento de encolar, scores
   siempre descendentes. Con `--llm off`: `{0, 0}` e idéntico entre dos
   ejecuciones. Semillas 1/2/3/5/7 a 300 ticks: `recuerdos == len(nodos)` en
   todas y 0 peticiones sin memoria.

## Bloqueantes

Ninguno. El bloqueante de la ronda 1 está resuelto y verificado por mutación;
el resto de criterios siguen cumpliéndose.

## No bloqueante

- `_recuperar_memoria` sigue recibiendo `individuo` sin usarlo. Cosmético.
- `buscar` es O(n·dim) en Python puro; con el catálogo real (24–28 hitos)
  cuesta ~0.5 ms por consulta y el tick medido queda en 1.43 ms de media
  (p95 1.90, máx 2.83 en 600 ticks síncronos), muy por debajo de 16.67 ms.
- `zip(..., strict=True)` es lo pedido y ahora falla en voz alta si el backend
  cambia de dimensión a mitad de partida; con `EmbedderOllama` cableado habría
  que fijar la dimensión o reconstruir el índice. Hoy el default (hashing, 256)
  no cambia nunca.
- `tribal/llm/http.py` al 50% de cobertura con su propio test (el transporte
  real se ejercita indirectamente desde los tests del cliente); no es
  comportamiento nuevo de esta feature.
- `review_package`: solo quedan funciones largas y complejidad preexistentes; la
  duplicación de `_transporte_http` desapareció. El "TODO" que marca en
  `http.py:18` es el falso positivo de siempre por "méTODO".
- `secrets scan`: 13 hallazgos, todos fixtures preexistentes en
  `agents/tests/`, ninguno en `tribal/llm/http.py`, `cliente.py` ni
  `embeddings.py`. Sin dependencias nuevas, sin `.tmp-*`, sin rutas absolutas,
  sin canales de fitness. `tribal/llm/cola.py` intacto (F2-002).

## Regresiones

`uv run pytest -q` → **891 passed, 15 skipped** (230.71 s). `ruff check` /
`ruff format --check` / `mypy` → verde (66 ficheros). Cobertura dirigida:
`embeddings.py` 89%, `http.py` 50% (el agente `coverage_report` sigue agotando
su timeout de 600 s por infraestructura; usé cobertura dirigida).

## Mutaciones

| Mutación | Resultado |
|----------|-----------|
| M1 contexto sin `memoria` | detectada |
| M5 `_registrar_recuerdo` no-op | detectada |
| M-tradiciones sin indexar | detectada |
| M-dim `zip(strict=False)` | detectada |
| M2 `hash()` en vez de blake2b | detectada |
| M3 guarda de contexto eliminada | detectada |
| M4 desempate por orden de inserción | detectada |

## Línea de gate

`harness gate → success=true · ready=true · 0 errors / 0 warnings · "ENTORNO LISTO — se puede trabajar." · pytest 335 passed in 165.34s`
