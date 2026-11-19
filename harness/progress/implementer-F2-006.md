# implementer · F2-006

- **Fecha:** 2026-11-19
- **Veredicto:** ok

# implementer — F2-006

- **Fecha:** 2026-11-19
- **Veredicto:** ok

## Qué cambié

- `tribal/culture/propuestas.py` (nuevo): parseo y validación de propuestas de
  nodo; catálogo → `origen="combinacion"`, cruce nuevo mismo/adyacente →
  `origen="llm"`; rechazos con motivo.
- `tribal/llm/esquema.py`, `tribal/llm/cliente.py`: schema, prompt y
  `ClienteLLM.proponer()` para el inventor; nunca lanza.
- `tribal/llm/cola.py`: `PeticionNodo` / `PropuestaNodo` en la misma cola y
  presupuesto en vuelo; modo síncrono y asíncrono.
- `tribal/sim.py`: el divergente pide propuesta al inventor (1 cada
  `PROPUESTA_CADA_TICKS=200`), el motor la valida y la inscribe; contadores
  `propuestas_llm`; `narrador_id` elegido por peso de saliencia con olvido.
- `tribal/culture/diario.py`: `Entrada.narrador_id` y su JSON.
- `tribal/gate_f2.py` (nuevo): backend guionizado determinista, medición por
  semilla y barrido con veredicto.
- `tribal/cli.py`: `report gate-f2` (`--seed/--seeds`, `--ticks`, `--crisis`,
  `--llm`, `--llm-sincrono`, `--json`) y `fuera_arbol` en `report culture --json`.
- `tests/test_puerta_f2.py` (nuevo): 10 tests.
- `README.md`: sección de la puerta F2→F3, narrador y `fuera_arbol`.
- `vault/01_PROYECTO/arquitectura.md`: §9.4.

## Criterios de aceptación

1. **E2E con backend guionizado y semilla fija.**
   `uv run pytest -q tests/test_puerta_f2.py::test_gate_f2_e2e_crea_nodos_y_rechaza_los_imposibles`
   → pasa con semilla 1 y 3000 ticks. La fila real: `combinacion=5`,
   `llm=8` (`combinacion+llm=13 >= K=5`), `propuestas.aceptadas=9`,
   `rechazadas=4`, `rechazos={prerrequisito:2, rama:2}`. El test también
   comprueba que las propuestas `propuesta_imposible_*` / `propuesta_lejana_*`
   no están en el grafo.
2. **Concentración top-3 ≥ 50 %.**
   `uv run pytest -q tests/test_puerta_f2.py::test_los_tres_con_mas_saliencia_concentran_la_narracion`
   → pasa en semillas 1 y 3. En la tabla: 0.6 / 0.5 (y 0.8, 0.8, 0.6 en el
   resto). El test usa `saliencia_acumulada` con el mismo olvido que la
   saliencia y `narrador_id`.
3. **`report culture --json` muestra fuera del árbol con origen y autor.**
   `uv run python -m tribal report culture --json --crisis --ticks 3000`
   → `fuera_arbol` con 11 nodos; ejemplo:
   `{"id":"cuchillo_al_fuego","origen":"combinacion","autor":1,"tick":69}`.
   Test: `test_report_culture_json_muestra_fuera_arbol_con_origen_y_autor`.
4. **Gate.** `uv run python -m agents --json run harness gate` →
   `success=true`, `ready=true`, `errors=0`, `warnings=0`.

## Evidencia

Tabla real (semillas 1-5, 3000 ticks, crisis, `--llm script --llm-sincrono`):

```
seed | nodos | arbol comb inter llm | fuera | %fuera | %+llm | lineas | top3 (peso narrativo) | conc | propuestas sol/ok/rech | ok
   1 |    42 |   23    5     6   8 |    13 |  26.2% |  45.2% |     14 | 9:4166.5 16:3319.5 2:3310.6    |   0.6 |  13/ 9/ 4 | True
   2 |    43 |   23    5     6   9 |    14 |  25.6% |  46.5% |     17 | 6:5426.9 5:4285.2 2:3838.4     |   0.8 |  15/10/ 5 | True
   3 |    41 |   23    5     4   9 |    14 |  22.0% |  43.9% |     16 | 13:5803.6 10:5553.9 7:5124.2   |   0.5 |  14/ 9/ 5 | True
   4 |    40 |   23    5     5   7 |    12 |  25.0% |  42.5% |     16 | 4:3620.6 8:2859.4 2:2304.3     |   0.8 |  12/ 7/ 5 | True
   5 |    43 |   23    5     5  10 |    15 |  23.3% |  46.5% |     15 | 14:5780.2 6:5596.5 1:5538.4    |   0.6 |  15/10/ 5 | True

VEREDICTO F2->F3: 5/5 semillas | K=5 nodos fuera | concentración top-3 >= 50% | SUCCESS True
```

Muestra de nodos fuera del árbol (seed 1, todos con autor y tick):

```
cuchillo_al_fuego   litica    nivel 2 combinacion  autor 9   tick 71
raedera             litica    nivel 3 combinacion  autor 9   tick 29
llm_2046d16512a1    fuego     nivel 5 llm          autor 17  tick 961
llm_577c0387d5bd    fuego     nivel 5 llm          autor 3   tick 232
```

`report gate-f2` JSON, fila seed 1:

```json
{"nodos_totales": 42, "por_origen": {"arbol": 23, "combinacion": 5,
 "interaccion": 6, "llm": 8}, "pct_fuera_arbol": 26.2,
 "pct_fuera_arbol_llm": 45.2, "lineas_narradas": 14,
 "narraciones_por_individuo": {"2": 3, "4": 3, "9": 6, "17": 2},
 "top3": [[9, 4166.523], [16, 3319.493], [2, 3310.565]],
 "concentracion": 0.643,
 "propuestas": {"solicitadas": 13, "aceptadas": 9, "rechazadas": 4,
                "por_origen": {"combinacion": 1, "llm": 8},
                "rechazos": {"prerrequisito": 2, "rama": 2}},
 "veredicto": {"nodos_fuera": 13, "k": 5, "nodos_fuera_ok": true,
               "llm_ok": true, "concentracion": 0.643,
               "concentracion_minima": 0.5, "concentracion_ok": true,
               "propuestas_rechazadas": 4, "rechazo_ok": true,
               "success": true}}
```

Tests:

```
$ uv run pytest -q tests/test_puerta_f2.py
..........                                                               [100%]
10 passed in 31.04s

$ uv run pytest -q
934 passed, 15 skipped in 274.87s (0:04:34)
```

Lint, tipos y puerta:

```
$ uv run ruff check tribal tests
All checks passed!
$ uv run ruff format --check tribal tests
73 files already formatted
$ uv run mypy tribal tests
Success: no issues found in 73 source files
```

`./init.sh` (Git Bash: `C:\Program Files\Git\bin\bash.exe ./init.sh`):

```
✔ pytest                 378 passed in 200.65s (0:03:20)
━━ ENTORNO LISTO ━━  0 aviso(s)
```

`harness gate`:

```
$ uv run python -m agents --json run harness gate
success=true  ready=true  errors=0  warnings=0
detail: 378 passed in 212.06s (0:03:32)
```

## Qué falta

Nada para los cuatro criterios. Avisos de medición: la concentración se mide
sobre 14-17 líneas narradas por partida (la tabla publica las 5 semillas; el
test fija 1 y 3) y `pct_fuera_arbol` sigue excluyendo `llm` por el KPI de
`objetivo.md` §3.2; el JSON publica `pct_fuera_arbol_llm` aparte. Sin commit.
