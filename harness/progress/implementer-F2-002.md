# implementer · F2-002

- **Fecha:** 2026-11-19
- **Veredicto:** ok

## Qué cambié (ronda de correcciones al rechazo)

- `tribal/llm/cola.py`: `cerrar() -> bool` reescrito. Deja de aceptar, **vacía
  la cola de peticiones** (cada una `descartadas += 1`, `en_vuelo -= 1`), pone el
  centinela y hace `join` en tramos de 50 ms hasta que el worker sale, con plazo
  `en_vuelo * (cliente.timeout + 1) + 1`. `en_vuelo` a 0 siempre; devuelve `False`
  si el hilo siguiera vivo y el CLI avisa por stderr. El worker ya no puede morir
  por una excepción de `_resolver` (la convierte en respuesta con `error`) y su
  decremento de `en_vuelo` está acotado a 0.
- `_descartar_resultados()` separa contadores: `decision is None` → `fallos`,
  decisión → `descartadas` (aplica también al modo síncrono).
- `tribal/llm/cliente.py`: `construir_prompt` dentro del `try` de `decidir`
  (un prompt que reviente ya no mata al worker).
- `tribal/sim.py`: `ACCIONES_SIN_PARAMETROS` + guard en `_intencion_llm`; si una
  candidata futura fuese `moverse`/`ensenar`/`cuidar`/`huir`, se ignora en vez de
  lanzar `ValueError` desde el bucle.
- `tribal/cli.py`: `--llm-sincrono` + `--llm http` se rechaza con exit 2 y mensaje
  claro; si `cola.cerrar()` devuelve `False`, warning a stderr.
- Docs: arquitectura §3 quita el backoff inexistente y describe el cierre; README
  alinea backoff, coste del cierre y variabilidad de los contadores en asíncrono.
- `tests/test_llm_cola.py`: +3 tests (cierre rápido con 2 en vuelo, `--llm http`
  con servicio muerto, combinación síncrona+http rechazada). 12 en total.

## Criterios de aceptación

1. **Hilo dedicado + colas acotadas + N en vuelo.** Sin cambios en esa parte;
   `test_cola_llena_respeta_el_maximo_en_vuelo` sigue verde.
2. **Backend 200 ms sin frenar el bucle.** `test_backend_lento_200ms_no_frena_el_bucle`:
   1200 ticks, `en_vuelo_max >= 1`, `ms_tick_medio < 16.67`, < 10 s.
3. **Decisión tardía descartada y sigue por instinto.**
   `test_resultado_fuera_de_ventana_se_descarta`,
   `test_decision_rezagada_se_descarta_y_el_mundo_sigue_por_instinto` y
   `test_intencion_caducada_equivale_al_instinto`.
4. **`run --headless --json --llm stub --ticks 1200` reporta la capa.**
   Salida real: `llm: {"aplicadas": 1, "descartadas": 1, "en_vuelo": 0, "fallos": 0, "peticiones": 80}`.
5. **gate success=true.** `uv run python -m agents --json run harness gate` →
   `"success": true`, `"message": "ENTORNO LISTO — se puede trabajar."`.

Bloqueante del reviewer (cierre): **cerrado**. `cerrar()` vacía pendientes antes
del centinela, así que solo puede quedar **una** inferencia en vuelo (el worker
es único) y el join espera a que termine, acotado por `timeout + 1` por petición
aceptada. Reproducción del escenario (`max_en_vuelo` 1 y 4, transporte de 200 ms,
`timeout=0.2`, una inferencia ya empezada):

```
max_en_vuelo=1 antes en_vuelo=1 | cerrar=0.15s limpio=True en_vuelo=0 hilos=[]
max_en_vuelo=4 antes en_vuelo=4 | cerrar=0.15s limpio=True en_vuelo=0 hilos=[]
```

Y el caso degradado real (`--llm http` sin Ollama, 1200→600 ticks): cierra limpio
en 3.7 s totales (los 3 s son el timeout de la única inferencia en vuelo, no 4×3),
`fallos` cuenta el error de transporte y `en_vuelo` 0.

## Evidencia

```
$ uv run python -m tribal run --headless --json --llm stub --ticks 1200
exit 0 | ticks 1200 | poblacion 12 -> 19
llm: {"aplicadas": 1, "descartadas": 1, "en_vuelo": 0, "fallos": 0, "peticiones": 80}

$ uv run python -m tribal run --headless --json --llm http --ticks 600   (sin servicio)
transcurrido: 3.71s
llm {'peticiones': 4, 'aplicadas': 0, 'descartadas': 3, 'fallos': 1, 'en_vuelo': 0}

$ uv run pytest tests/test_llm_cola.py -v
test_cola_llena_respeta_el_maximo_en_vuelo PASSED
test_backend_lento_200ms_no_frena_el_bucle PASSED
test_resultado_fuera_de_ventana_se_descarta PASSED
test_cierre_no_deja_hilos_vivos PASSED
test_cierre_rapido_con_peticiones_en_vuelo PASSED
test_http_con_servicio_muerto_cierra_limpio PASSED
test_sincrono_con_http_se_rechaza PASSED
test_decision_rezagada_se_descarta_y_el_mundo_sigue_por_instinto PASSED
test_intencion_caducada_equivale_al_instinto PASSED
test_cli_json_con_stub_reporta_la_capa_llm PASSED
test_sin_llm_el_resumen_no_cambia PASSED
test_stub_sincrono_es_determinista_entre_procesos PASSED
============================= 12 passed in 3.91s ==============================

$ uv run pytest -q                       → 854 passed, 15 skipped in 224.46s
$ uv run ruff check tribal/ tests/ agents/  → All checks passed!
$ uv run ruff format --check tribal/ tests/ → 57 files already formatted
$ uv run mypy tribal/ tests/             → Success: no issues found in 57 source files
$ uv run python -m agents --json run harness gate → "success": true, "ENTORNO LISTO"
```

## Qué falta

- Si el transporte se saltara su propio timeout, `cerrar()` devuelve `False` y
  avisa; no hay forma en Python de matar el hilo (es daemon y muere con el
  proceso). Es el máximo alcanzable sin aislar la inferencia en un subproceso.
- `seleccion.py` por saliencia y `aplicar.py` siguen siendo F2-003/F2-004.
