# implementer · EMER-001

- **Fecha:** 2026-11-18
- **Veredicto:** blocked

# EMER-001 · Selección real de la divergencia

## Qué cambié

- `tribal/culture/beneficios.py` (nuevo): efectos de las combinaciones y `HABILIDAD_POR_COMBINACION`; `conocidos(grafo, habilidades)` aplica el efecto a quien sabe la técnica, sin mirar el temperamento.
- `tribal/culture/tradiciones.py` (nuevo): tradiciones de nivel 2 (`origen: interaccion`) por imitación repetida.
- `tribal/culture/grafo.py`: `imitadores`, `ultimo_imitador`, `imitaciones_tick`, `agregar()` y `nivel_max`; `registrar_uso` recibe `tick`.
- `tribal/culture/arbol.py`: `NIVEL_ORIGEN` (arbol 0, combinacion 1, interaccion 2, llm 2).
- `tribal/core/acciones.py`: `comer`/`aplicar` aceptan `bonus_bayas`/`bonus_caza`; no hay penalización por temperamento.
- `tribal/core/depredador.py`: factor de daño por presa para que la técnica de vigilia la disfrute quien la sabe.
- `tribal/core/recursos.py`: la sequía baja la capacidad de carga de agua y bayas a la mitad y espacia la regeneración 1.25x.
- `tribal/sim.py`: se borraron los cuatro canales; el divergente gasta el tick experimentando, aprende la habilidad al descubrir y el nodo queda como cultura tribal; `ENERGIA_CRIA=50` la paga la madre; umbral de cría único (65) en calma y crisis; tradiciones y beneficios por individuo.
- `tribal/cli.py`: `report culture --crisis` y `nivel_max` en el informe.
- `tests/test_tradiciones.py` (nuevo), tests de mecanismo en `tests/test_divergencia.py`, ajustes de `test_arbol`, `test_cli_run` y `test_puerta_f0`.
- `README.md`: mecanismo honesto, tabla de beneficios, reproducción y resultado medido del barrido.

## Criterios de aceptación

- [x] **No queda ningún canal que premie el rasgo.** `grep` sin coincidencias para `PENALIZACION_CONFORMISTA`, `VENTAJA_REPRODUCTIVA`, `_plasmar_divergencia`, `_moldear_divergencia`, `UMBRAL_REPRODUCCION_CRISIS`; `acciones.py` no menciona `divergencia` ni `UMBRAL_DIVERGENTE`. Tests: `test_el_temperamento_no_cambia_la_ganancia_de_comer`, `test_el_temperamento_no_cambia_la_sed_en_crisis`, `test_el_genoma_no_se_edita_en_runtime`.
- [x] **La crisis baja la capacidad de carga y el bonus es igual para quien la conoce.** Test: `test_la_crisis_baja_la_capacidad_de_carga_del_agua_y_las_bayas`, `test_el_bonus_de_una_tecnica_es_igual_para_quien_la_sabe`.
- [x] **Reproducción sin subsidio y sin energía neta.** `UMBRAL_REPRODUCCION=65` en ambos regímenes, `ENERGIA_CRIA=50` pagada por la madre. Tests: `test_el_umbral_de_reproduccion_es_el_mismo_en_calma_y_crisis`, `test_la_cria_no_inyecta_energia_neta`, `test_la_crisis_no_es_el_regimen_favorable` (nacimientos/1000 ticks, 4000 ticks, seed 3).
- [x] **Mecanismo: el descubridor rinde más bajo escasez, con independencia del rasgo; un divergente sin descubrimiento rinde como un conformista.** Tests: `test_bajo_escasez_quien_descubrio_la_tecnica_rinde_mas` (dos individuos con divergencia 0.9, uno sabe `fabricar` y el otro no), `test_un_divergente_que_no_descubre_nada_rinde_como_un_conformista`.
- [ ] **Barrido 1..10 x 8000 ticks.** NO se alcanza el umbral: div% sube en 2/10, empata en 7, baja en 1; la crisis no es más poblada que la calma en 5/10 (se pedían 6/10). Tabla real abajo.
- [x] **`pytest -q` verde y gate success=true.**

## Barrido real (10 semillas x 8000 ticks, 12 individuos)

```
seed | div% calma->crisis | media calma/crisis | sigma calma/crisis | nacidos calma/crisis | nodos calma/crisis | poblacion calma/crisis | extinciones
   1 |  0.0 ->  0.0 | 0.460/0.431 | 0.025/0.026 | 29/34 | 1/2 |  5/15 | 0/0
   2 |  0.0 -> 23.5 | 0.486/0.545 | 0.036/0.056 | 36/40 | 1/2 | 13/17 | 0/0
   3 | 10.0 ->  0.0 | 0.545/0.508 | 0.040/0.022 | 92/40 | 1/2 | 50/13 | 0/0
   4 |  0.0 ->  0.0 | 0.400/0.412 | 0.030/0.029 | 34/17 | 1/2 | 11/ 4 | 0/0
   5 |  0.0 ->  0.0 | 0.564/0.000 | 0.024/0.000 | 38/13 | 1/2 | 16/ 0 | 0/1
   6 |  0.0 ->  0.0 | 0.357/0.301 | 0.100/0.014 | 56/28 | 1/1 | 26/12 | 0/0
   7 |  0.0 ->  0.0 | 0.420/0.000 | 0.020/0.000 | 25/ 5 | 1/2 |  8/ 0 | 0/1
   8 |  0.0 ->  0.0 | 0.000/0.447 | 0.000/0.017 | 16/26 | 1/1 |  0/ 7 | 1/0
   9 |  0.0 ->  0.0 | 0.000/0.407 | 0.000/0.020 |  2/31 | 1/2 |  0/10 | 1/0
  10 |  0.0 -> 31.9 | 0.534/0.587 | 0.023/0.031 | 62/90 | 1/1 | 17/47 | 0/0
```

`nodos` = `nodos_por_origen["combinacion"] + ["interaccion"]` (en calma siempre nace al menos una tradición; en crisis, además, `raedera`).

**Conclusión honesta:** con un solo cruce alcanzable (`raedera`), la ventaja es un evento único; la habilidad se transmite a los conformistas y `heredar` promedia `divergencia` hacia 0.5, así que el rasgo se descuelga de la aptitud. La crisis tampoco es consistentemente menos poblada porque el +25 % de bayas compensa la capacidad de carga recortada. Para pasar la puerta hacen falta más combinaciones alcanzables (rama roles/fuego/lenguaje) o un mecanismo de selección que no edite el genoma, no una ventaja por decreto.

## Evidencia literal

```text
$ uv run pytest -q
665 passed, 15 skipped in 85.96s (0:01:25)

$ uv run pytest -q tests/test_divergencia.py tests/test_tradiciones.py
34 passed in 16.00s

$ uv run ruff check tribal/ tests/ agents/
All checks passed!

$ uv run ruff format --check tribal/ tests/
40 files already formatted

$ uv run mypy tribal/ tests/
Success: no issues found in 40 source files

$ ./init.sh
━━ ENTORNO LISTO ━━  0 aviso(s)
pytest 136 passed in 21.83s

$ uv run python -m agents --json run harness gate
"success": true, "message": "ENTORNO LISTO — se puede trabajar.", "ready": true, "errors": 0, "warnings": 0
```

## Qué falta

- Criterio 5 (barrido): no se alcanza. La implementación cumple 1-4 y 6; la puerta F1 no.
- Decisión de diseño pendiente: ampliar las combinaciones alcanzables o aceptar que la selección cultural no mueve la proporción del rasgo en 8000 ticks.
- No se tocó `heredar` (F1-001), ni `agents/`, ni `harness/`, ni se commiteó nada.
