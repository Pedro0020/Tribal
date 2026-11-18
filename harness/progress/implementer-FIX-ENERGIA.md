# implementer · FIX-ENERGIA

- **Fecha:** 2026-11-18
- **Veredicto:** ok

# FIX-ENERGIA — informe del implementer

## Qué cambié

- `tribal/sim.py` — `_nacer`: el pago de la madre es ahora **estructural**. Antes
  descontaba `ENERGIA_CRIA` con `max(0.0, ...)` y la cría nacía siempre con 50;
  con una madre de menos de 50 eso **creaba** energía (madre 30 → madre 0, cría
  50: +20). Ahora `aportado = min(ENERGIA_CRIA, madre.necesidades.energia)`, la
  madre pierde `aportado` y la cría nace con `aportado`: el nacimiento es neutro
  por construcción, no por confiar en que el umbral (65) esté por encima del
  coste (50). Docstring de `ENERGIA_CRIA` actualizado.
- `tribal/sim.py` — `resumen`: nuevo campo `coste_reproduccion` (la constante,
  determinista). `nacimientos` y `media_energia` ya estaban.
- `tests/test_reproduccion.py` — nuevo: conservación, madre sin para pagar,
  pareja bajo el umbral, guarda de código de «sin umbral por régimen» y test de
  población de 8000 ticks con auditoría de energía de cada nacimiento.
- `tests/test_cli_run.py` — la lista de claves del resumen acepta
  `coste_reproduccion`.
- `README.md` — la reproducción documenta el coste publicado en el resumen y
  que la cría nunca recibe más de lo que la madre tiene.

## Auditoría de la reproducción (antes del cambio)

- `ENERGIA_CRIA = 50.0`, `UMBRAL_REPRODUCCION = 65.0`, `DISTANCIA_PAREJA = 2.0`.
- La cría nacía con `Necesidades(energia=ENERGIA_CRIA)`; la madre pagaba
  `max(0.0, energia - 50)`; el padre no paga energía (solo cooldown).
- Total del sistema al nacer: **neutro** mientras la madre tuviera ≥ 50 (el
  camino normal, porque el umbral 65 > 50). El único agujero era la llamada
  directa con madre < 50, donde el `max` recortaba el pago y la cría sí creaba
  energía. Cerrado.
- No hay umbral de crisis: `_umbral_reproduccion()` devuelve la constante y
  `_puede_reproducir` no lee `config.crisis`. `UMBRAL_REPRODUCCION_CRISIS=30`,
  `ENERGIA_CRIA=80` y `VENTAJA_REPRODUCTIVA_DIVERGENTE` no existen ya.
- La crisis **no** es más fértil: 0.260 nacimientos por 1000 persona-ticks en
  sequía frente a 0.282 en calma (semillas 1-3, 8000 ticks). Barrido de 20
  semillas: media de nacimientos 24.05 (crisis) vs 26.2 (calma), 13/20 semillas
  con la crisis por debajo. La población final difiere por semilla (la
  simulación es caótica y la sequía dispara descubrimientos), pero **no por
  natalidad**: la tasa por persona-tick no es mayor, y ningún nacimiento crea
  energía (auditado tick a tick en las 6 corridas).

## Criterios de aceptación

1. **La cría no nace con más energía de la que su madre paga** —
   `uv run pytest tests/test_reproduccion.py::test_la_cria_nace_con_lo_que_paga_la_madre`
   (70/70 → madre 20, cría 50, suma de los tres ≤ suma de los dos) y
   `::test_la_madre_no_paga_mas_de_lo_que_tiene` (madre 30 → madre 0, cría 30,
   total igual). El segundo **falla** con el código anterior (comprobado:
   `assert 50.0 == 30.0`).
2. **Una pareja con energía baja no produce un hijo con energía alta** —
   `::test_una_pareja_sin_energia_suficiente_no_cria` (energía 64 = umbral − 1,
   misma posición, maduros, sin cooldown → 0 nacimientos en calma y en crisis).
3. **La población no crece en crisis por subsidio reproductivo** —
   `::test_la_crisis_no_es_mas_fertil_que_la_calma` (8000 ticks, semillas 1-3,
   nacimientos por 1000 persona-ticks con margen de ruido del 10 %) y
   `::test_la_crisis_no_tiene_umbral_de_reproduccion_propio` (AST: ninguna
   constante `UMBRAL…CRISIS` y ninguna de `_umbral_reproduccion`,
   `_puede_reproducir`, `_reproducir`, `_nacer` lee `crisis`).
4. **`uv run pytest -q` pasa y gate success=true** — 710 passed, 15 skipped;
   `harness gate` → `success: true`, `ENTORNO LISTO`.

## Evidencia

### Conservación y umbral (tests nuevos)

```
$ uv run pytest tests/test_reproduccion.py -q
.....                                                                    [100%]
5 passed in 17.03s
```

### El test caza la inyección del código anterior

```
$ uv run pytest tests/test_reproduccion.py::test_la_madre_no_paga_mas_de_lo_que_tiene -q
>       assert hijo.necesidades.energia == pytest.approx(30.0)
E       assert 50.0 == 30.0 ± 3.0e-05
E         Obtained: 50.0
E         Expected: 30.0 ± 3.0e-05
1 failed in 0.38s
```

(código anterior restaurado después; el árbol queda con el arreglo)

### 8000 ticks, calma vs crisis, misma semilla

```
ENERGIA_CRIA=50.0 UMBRAL_REPRODUCCION=65.0
seed=1 calma  nacimientos= 32 muertes= 32 poblacion_final=12 persona_ticks=105419 tasa=0.304 coste_reproduccion=50.0
seed=1 crisis nacimientos= 19 muertes= 29 poblacion_final= 2 persona_ticks= 76296 tasa=0.249 coste_reproduccion=50.0
seed=2 calma  nacimientos= 12 muertes= 24 poblacion_final= 0 persona_ticks= 54001 tasa=0.222 coste_reproduccion=50.0
seed=2 crisis nacimientos= 19 muertes= 29 poblacion_final= 2 persona_ticks= 72758 tasa=0.261 coste_reproduccion=50.0
seed=3 calma  nacimientos= 27 muertes= 34 poblacion_final= 5 persona_ticks= 92631 tasa=0.291 coste_reproduccion=50.0
seed=3 crisis nacimientos= 19 muertes= 26 poblacion_final= 5 persona_ticks= 70526 tasa=0.269 coste_reproduccion=50.0
```

Agregado de las tres semillas: calma 71 nacimientos / 252051 persona-ticks =
0.282; crisis 57 / 219580 = 0.260. La crisis no cría más.

### Suite completa

```
$ uv run pytest -q
710 passed, 15 skipped in 105.35s (0:01:45)
```

### Lint, formato y tipos

```
$ uv run ruff check tribal/ tests/ agents/
All checks passed!
$ uv run ruff format --check tribal/ tests/
43 files already formatted
$ uv run mypy tribal/ tests/
Success: no issues found in 43 source files
```

### Puerta

```
$ uv run python -m agents --json run harness gate
"success": true,
"message": "ENTORNO LISTO — se puede trabajar.",
"pytest": "181 passed in 47.87s"
```

(`./init.sh` no corre en este shell: no hay `/bin/bash`; el gate es el mismo
comando por la vía del agente, y es el que usa `harness finish`.)

## Qué falta

- `sed` y `salud` de la cría siguen naciendo a 0 y 100: es una inyección de agua
  y salud, no de energía. Fuera del criterio de esta feature; medido, no explica
  el resultado de población (probado copiando la sed de la madre: la crisis
  seguía por delante). Candidato a feature si se quiere conservar todo, no solo
  la energía.
- La población final por semilla sigue siendo muy ruidosa (extinciones a 1-2
  individuos en ambas ramas): cualquier criterio de población necesita ventana
  de varias semillas, como hace el test nuevo.
