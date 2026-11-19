# reviewer · F2-002

- **Fecha:** 2026-11-19
- **Veredicto:** aprobado

## Veredicto: aprobado

## Criterios (verificados ejecutando en esta ronda)

1. **Hilo dedicado + colas acotadas + N configurable → CUMPLIDO.** Instrumentado el
   transporte: todas las llamadas asíncronas corren en `threading.current_thread().name
   == "tribal-llm"`; el bucle solo usa `put_nowait`/`get_nowait`. Martilleo con
   `max_en_vuelo ∈ {1,3,7}`: `en_vuelo_max` = 1/3/7 exactos, con rechazo en 0.19–0.57 ms
   cuando el cupo está lleno.
2. **Backend 200 ms → CUMPLIDO.** 1200 ticks en 0.91 s; entre el inicio y el fin de cada
   petición (0.218 s reales) avanzaron **318, 266 y 244 ticks**; por tick medio
   **0.754 ms**, máx **1.697 ms**, p99 1.20 ms (presupuesto 16.67).
3. **Decisión tardía → CUMPLIDO.** `drenar(16)` con petición de tick 10 y ventana 5 →
   `[]`, `descartadas=1`; respuesta inyectada a `tick-50` en la cola de resultados →
   descarte y `intencion_llm` vacía; `test_intencion_caducada_equivale_al_instinto`
   compara dos partidas completas.
4. **`run --headless --json --llm stub --ticks 1200` → CUMPLIDO.**
   `{"peticiones": 88, "aplicadas": 2, "descartadas": 1, "fallos": 0, "en_vuelo": 0}`.
   Sin `--llm`, el resumen no lleva `llm` y es **idéntico a HEAD** (extraído a un
   directorio temporal, mismos 1200 ticks).
5. **`harness gate` → CUMPLIDO.** `success: true`, `"ENTORNO LISTO — se puede trabajar."`,
   `errors: 0`, `pytest 298 passed in 159.39s`.

## Bloqueante de la ronda 1: cerrado

`cerrar()` con el worker dentro de la inferencia (transporte que consume el timeout
entero, `timeout=0.25`), 2 iteraciones por cada N:

```
n=1: encoladas=1 -> True en 250 ms | en_vuelo=0 | hilos=[] | descartadas=1
n=2: encoladas=2 -> True en 251 ms | en_vuelo=0 | hilos=[] | descartadas=2
n=4: encoladas=4 -> True en 250 ms | en_vuelo=0 | hilos=[] | descartadas=4
```

Cierre acotado a **una** inferencia (no a N), `en_vuelo=0`, ningún `tribal-llm` vivo,
segunda llamada `True` y contadores sin moverse, e invariante
`enviadas == aplicadas + descartadas + fallos + en_vuelo` en los tres casos.

Escape hatch cuando el transporte se pasa del plazo (bloquea 5 s con `timeout=0.1`):
`cerrar() → False` en 2.11 s, `en_vuelo=0`, hilo vivo; al liberar el transporte el hilo
muere. Es el comportamiento documentado.

## Verificaciones pedidas en esta ronda

- **`--llm http` sin servicio:** 3.97 s de pared, exit 0,
  `{"peticiones": 4, "aplicadas": 0, "descartadas": 3, "fallos": 1, "en_vuelo": 0}`.
  Antes daba `en_vuelo: 2` y `fallos: 0`; ahora el fallo se cuenta y el cierre es limpio.
  Repetido por la **API de librería**, dos partidas seguidas: 3.63 s y 3.32 s, `en_vuelo=0`,
  cero hilos huérfanos (sin fugas entre ejecuciones).
- **`--llm-sincrono --llm http`:** exit **2** con
  `error: --llm-sincrono solo vale con --llm stub: resolver http en el tick congelaría el
  bucle hasta el timeout`.
- **Guard de acciones sin parámetros:** con `intencion_llm` = `moverse`, `ensenar`,
  `cuidar` y `huir`, `step()` no lanza y el `resumen()` es **igual al de instinto puro**;
  con `descansar` sí se consume y se aplica. Cierra el `ValueError` latente.
- **Worker blindado:** hice que `cliente.decidir` lance en la primera petición; el worker
  la convierte en respuesta fallida (`fallos=1`), sigue consumiendo y resuelve la
  segunda (`beber`), y `cerrar()` devuelve `True` sin hilos vivos.
- **Documentación:** README y arquitectura §3 coinciden — `cerrar()` vacía lo no empezado,
  centinela, plazo `en_vuelo * (timeout + 1)`, `en_vuelo` a 0, `False` si el transporte se
  pasa, **no hay backoff**, y en asíncrono no son reproducibles ni los contadores `llm` ni
  el tick de llegada. El bullet antiguo de backoff ya no está.

## Regresiones

`uv run pytest -q` → **854 passed, 15 skipped** (228 s). `ruff check` All checks passed ·
`ruff format --check` 57 files · `mypy` Success · `run --headless --benchmark --ticks 600`
→ **0.63 ms/tick**, exit 0 · `import tribal.sim` no carga `pygame` · sin dependencias
nuevas (`pyproject.toml`/`uv.lock` intactos) · sin `.tmp-*` · `secrets scan` solo señala
fixtures previos en `agents/tests/` (nada de `tribal/`) · `review review_package` no
reporta nada en `cola.py` ni en `test_llm_cola.py` (los 14 hallazgos son funciones
preexistentes de `cli.py`, `sim.py`, `config.py`, `instinto.py` y `mundo.py`).

## No bloqueante

- El docstring de `sim.run` dice «al volver no queda hilo vivo» sin condicionar; con un
  transporte que se pasa del plazo eso es falso y solo el CLI avisa (el `False` de
  `cerrar()` se descarta dentro de `run`). La documentación larga sí lo matiza.
- `cerrar()` fuerza `en_vuelo=0` aunque devuelva `False`: una respuesta que llegue
  después de esa rendición no se cuenta en ninguna parte. Coherente con el `False`, pero
  conviene no olvidarlo si algún día se usa el retorno.
- `ACCIONES_SIN_PARAMETROS` repite el vocabulario de `core.acciones`: dos listas que hay
  que mantener en sintonía y ningún test que las compare.
- `_encolar_dilema` atiende siempre al primer individuo de la lista con dilema; la
  selección por saliencia es F2-003 y así está declarado.
- Los contadores `llm` hacen que el `resumen()` completo no sea reproducible en asíncrono
  (documentado ahora); con `--llm off` y `--llm-sincrono` sí lo es.

## Mutaciones

Ninguna en el repositorio. Los chequeos se ejecutaron desde scripts en
`%TEMP%\opencode\f2002\`.
