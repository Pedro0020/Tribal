# implementer · DIVERGENCIA-002

- **Fecha:** 2026-11-18
- **Veredicto:** ok

## Qué cambié (ronda 2 — bloqueante del reviewer)

El código de producto **no cambia**: el bloqueante era de vigilancia. Todo lo de
esta ronda está en `tests/test_divergencia_calma.py` y en la frase que prometía
de más en `vault/01_PROYECTO/arquitectura.md` §9.2.

- `tests/test_divergencia_calma.py` (16 tests, antes 12):
  - **`test_beber_sacia_igual_a_los_dos_temperamentos`**: mismo mundo y misma
    agua, `acciones.beber` con sed 50 y con sed 90 para divergencia 0.1 y 0.9;
    la sed final y el agua consumida son idénticas. Con 90 el margen no se
    esconde en el suelo de 0.
  - **`test_el_temperamento_no_cambia_quien_puede_criar`**: la función real
    `Simulacion._puede_reproducir` con edad madura, cooldown 0 y energía
    `UMBRAL−1 / UMBRAL / UMBRAL+1` para 0.1 y 0.9 → `[False, False, True]` en
    los dos (mismo umbral, sin ajuste por rasgo).
  - **`test_el_genoma_no_cambia_en_una_partida`**: `crear(42, 12, crisis=True)`,
    snapshot del `Genoma` completo (dataclass `frozen`, igualdad campo a campo)
    al tick 1 y al 500 por id; los 12 fundadores siguen ahí y el genoma es
    idéntico.
  - **`test_el_rasgo_solo_se_lee_donde_es_conducta`**: guard nuevo por **lista
    blanca**, no por nombres. Recorre `tribal/**/*.py` con AST, entra en los
    cuerpos de funciones y recoge cada `Attribute(attr="divergencia")`; solo
    valen cinco sitios documentados en el test:
    `genoma.temperamento` (clasificar), `genoma.heredar` (copiar el gen),
    `instinto.radio_deambular` y `instinto._punto_errante` (paseo) y
    `sim._intentar_combinacion` (quién experimenta en crisis). Además rechaza
    `getattr(..., "divergencia")` por cadena fuera de `genoma.py`.
  - `test_no_reaparecen_los_canales_de_ventaja_directa`: mismos nombres
    prohibidos y mismo chequeo de tokens por línea, ahora sobre
    `tribal/core/acciones.py`, `tribal/core/modelos.py`, `tribal/core/genoma.py`,
    `tribal/agents/necesidades.py` y `tribal/sim.py`. (No existe
    `tribal/core/necesidades.py`: las necesidades viven en `agents/` con las
    tasas duplicadas en `config.py`; por eso entra `genoma.py`, que es donde de
    verdad podría esconderse un canal.)
  - Docstring del módulo corregido: ya no afirma «ni comida, ni sed, ni cría» a
    secas, dice qué test vigila cada vía.
- `vault/01_PROYECTO/arquitectura.md` §9.2: la frase ya no dice que el test
  «vigila los cuatro canales»; describe las dos mitades reales (lista blanca +
  tests de bocado, sed al beber, umbral de cría y genoma congelado).

## Verificación por mutación (las 4 caen)

Script temporal, `uv run pytest -q tests/test_divergencia_calma.py` por mutación,
restauración desde copia y sha256 idéntico en las cuatro:

```
M1 comer: divergente -20 % de energía
  pytest exit=1 · restaurado=sha256 igual
  cazada por: test_el_rasgo_solo_se_lee_donde_es_conducta
  cazada por: test_un_divergente_que_no_descubre_nada_rinde_igual_que_un_conformista
M2 beber: divergente sacia -20 % de sed
  pytest exit=1 · restaurado=sha256 igual
  cazada por: test_el_rasgo_solo_se_lee_donde_es_conducta
  cazada por: test_beber_sacia_igual_a_los_dos_temperamentos
M3b cría: umbral -10 al divergente
  pytest exit=1 · restaurado=sha256 igual
  cazada por: test_el_rasgo_solo_se_lee_donde_es_conducta
  cazada por: test_el_temperamento_no_cambia_quien_puede_criar
M4 plasticidad: divergencia += 0.01 por tick
  pytest exit=1 · restaurado=sha256 igual
  cazada por: test_en_calma_el_divergente_explora_mas_radio_que_el_conformista
  cazada por: test_el_rasgo_solo_se_lee_donde_es_conducta
  cazada por: test_el_genoma_no_cambia_en_una_partida
```

Las tres que el reviewer cazó a `passed` (M2, M3b y la forma exacta de
`VENTAJA_REPRODUCTIVA_DIVERGENTE`) ahora fallan dos veces: por contrato y por
conducta. M1 y M4 siguen cayendo.

## Criterios de aceptación

1. **Conducta en calma distinta** — 5 tests (radio, exploración en 8 semillas,
   determinismo, sesgo de cohesión, urgencia). Sin cambios en esta ronda.
2. **Sin ventaja directa** — lista blanca por acceso al dato (caza lectura en
   cuerpos de función, comparaciones, umbrales y `+=`) + nombres prohibidos en
   cinco módulos + 5 tests de conducta: `comer`, `beber`, homeostasis,
   `_puede_reproducir` y genoma congelado.
3. **Selección medible por mecanismo** — `descubridores`,
   `supervivencia_descubridores`, `supervivencia_no_descubridores`,
   `diferencial_seleccion`; aritmética, crías en el denominador, habilidad
   aprendida (90 vs 80 de energía) y calma = 0.
4. **`pytest -q` y gate** — abajo.

## Evidencia

```
uv run pytest -q                      -> 705 passed, 15 skipped in 90.40s
uv run ruff check tribal tests agents -> All checks passed!
uv run ruff format --check tribal tests -> 42 files already formatted
uv run mypy tribal                    -> Success: no issues found in 26 source files
harness gate                          -> success True · ready True · errors 0 · warnings 0
                                         (init.sh: 176 passed in 28.24s)
```

Conducta y mecanismo, ejecutados en esta ronda:

```
tests/test_divergencia_calma.py ................                            [100%]
16 passed in 2.91s
```

Telemetría (sin cambios: el motor no se tocó en esta ronda), `--ticks 2000`:

```
calma   : descubridores [] | supD 0.0 | supN 1.0 | diferencial 0.0
crisis  : descubridores [1, 2, 7, 9] | supD 1.0 | supN 0.895 | diferencial 0.105
```

## Qué falta

Sigue en pie el límite del informe anterior: la proporción de divergentes no
reacciona de forma sistemática (4/10 semillas a favor del descubridor); el
mecanismo es medible y está documentado, y subirlo es de EMER-001 / eje 3. El
`diferencial_seleccion` es foto del último tick, y el reviewer apunta dos
mejoras no bloqueantes que no toco aquí: `supervivencia_descubridores: 0.0` con
lista vacía se lee como extinción, y los ids deberían ser monótonos para que el
denominador no se corrompa si la población encoge.
