# reviewer · DIVERGENCIA-002

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

## Criterios

### 1. Conducta en calma distinta — CUMPLIDO

Re-medido en esta ronda (el motor no cambió, pero no me fío del informe).
Pradera 60×34 vacía, un individuo, 120 ticks, misma semilla, sin depredador:

```
seed 1: 3.00 vs  8.60 | seed 5: 7.49 vs 11.98
seed 2: 3.90 vs 11.10 | seed 6: 6.94 vs  7.40
seed 3: 5.65 vs  6.60 | seed 7: 8.83 vs 11.05
seed 4: 6.71 vs 11.89 | seed 8: 6.66 vs 11.70
media conf 6.15 / div 10.04  ->  8/8 semillas a favor
```

- **8/8 semillas**, margen mínimo seed 3 (6.60 vs 5.65). No es azar.
- Urgencia: con sed 99 los tres (0.1 / 0.5 / 0.9) devuelven
  `Accion('moverse', destino=(6.0, 6.0))`.
- Determinista: dos corridas de 600 ticks dan el mismo `resumen()`.
- `paseo` sigue siendo estado de conducta: no está en `Genoma`, `heredar` no
  lo toca, `asdict` solo se usa en `config.py`, `resumen()` no lo publica.
- Sin cambios en esta ronda; el motor es el mismo (`git diff` de `tribal/`
  idéntico al de la ronda 1).

### 2. Sin ventaja directa — CUMPLIDO

Las **cuatro mutaciones del bloqueante caen**, cada una por el guard y por un
test de conducta (suite `tests/`, 176 tests, restauración con sha256 idéntico):

| Mutación | Fallos |
|---|---|
| M1 `comer`: divergente −20 % energía | `test_el_rasgo_solo_se_lee...`, `test_el_temperamento_no_cambia_la_ganancia_de_comer`, `test_un_divergente_que_no_descubre_nada...` (6 en total) |
| M2 `beber`: sacia −20 % sed | `test_el_rasgo_solo_se_lee...`, `test_beber_sacia_igual_a_los_dos_temperamentos` |
| M3b cría: umbral −10 al divergente | `test_el_rasgo_solo_se_lee...`, `test_el_temperamento_no_cambia_quien_puede_criar` |
| M4 plasticidad `+0.01`/tick | `test_el_rasgo_solo_se_lee...`, `test_el_genoma_no_cambia_en_una_partida` (+ `test_la_crisis_no_es_el_regimen_favorable`) |

La forma que pidió el líder —`if getattr(ind, "genoma").divergencia > 0.5:
energia += 1` en una función cualquiera— **cae** por
`test_el_rasgo_solo_se_lee_donde_es_conducta` (1 failed, 175 passed). El guard
mira el AST, no el texto: `getattr` no lo esquiva porque el nodo `.divergencia`
sigue estando.

Cobertura por conducta comprobada: bocado, sed al beber (50 y 90, para que el
suelo de 0 no oculte la diferencia), umbral de cría (`UMBRAL−1/UMBRAL/+1` con
0.1 y 0.9) y genoma congelado a 500 ticks. Los tests no son triviales.

### 3. Selección por conducta medible — CUMPLIDO (misma reserva de F1-005)

Motor sin tocar; re-verificado: seed 42 crisis → registrados 23 = 12+11 crías,
`supD=1.0`, `supN=17/19=0.895`, `dif=0.105`. `descubridores` == autores de
nodos `origen="combinacion"` en 6/6 semillas (1→[8], 2→[1,2], 3→[1,2,12],
8→[9], 9→[1,5,7], 42→[1,2,7,9]). Calma seed 42: `descubridores=[]`, `dif=0.0`.
La subida sistemática sigue siendo de F1-005/EMER-001, no de aquí.

### 4. pytest y gate — CUMPLIDO

```
uv run pytest -q                       -> 705 passed, 15 skipped in 89.43s
harness gate                           -> success=true · ready=true · errors 0 · warnings 0
                                          "ENTORNO LISTO — se puede trabajar." (176 passed)
uv run ruff check tribal tests agents  -> All checks passed!
uv run ruff format --check             -> 42 files already formatted
uv run mypy tribal                     -> Success: no issues found in 26 source files
```

## Mutaciones y sondas (todo restaurado, sha256 comprobado)

- M1, M2, M3b, M4: **caen** (tabla de arriba).
- E1 `getattr(...).divergencia` en `descansar`: **cae** por la lista blanca.
- E2b ventaja `+0.5` energía/tick en crisis **dentro de
  `_intentar_combinacion`** (función de la lista blanca): **pasa** (176/176).
- E4 `en_crisis and temperamento(genoma) == "divergente": energia += 0.5` en
  `sim.step`: **pasa** (176/176).
- E3 lectura ofuscada por `__dataclass_fields__` en `descansar`: **pasa**
  (176/176).

Los tres supervivientes están en "No bloqueante": los cuatro canales que nombra
el criterio están vigilados dos veces, y AGENTS.md ya avisa de que una lista de
patrones solo caza lo evidente. No los convierto en bloqueante en la ronda 2
para no mover el listón a "ningún guard estático es evadible", que es
imposible; pero quedan anotados con su arreglo.

## No bloqueante

1. **El whitelist es por función, no por línea.** Cualquier ventaja escrita
   dentro de `_intentar_combinacion` (o `_practicar`, `radio_deambular`,
   `_punto_errante`, `temperamento`, `heredar`) es invisible al guard. E2b lo
   demuestra con `+0.5` energía/tick que deja 176 verdes. Arreglo barato: un
   test que snapshotee `necesidades`/`genoma` antes y después de esas funciones
   y exija que no cambien (leen, no escriben), o marcas `# allow` por línea.
2. **`temperamento()` es una vía de lectura no vigilada.** El guard protege el
   atributo `.divergencia`, pero no las llamadas al clasificador; E4 (energía
   extra en crisis) pasa entero. Arreglo: añadir a la lista blanca las llamadas
   a `temperamento` (hoy solo 3, todas en `sim.py`: `_intentar_combinacion`,
   `_practicar`, `resumen`).
3. **§9.2 dice "cualquier otro acceso falla el test"**, y E4 es un acceso (vía
   `temperamento`) que no falla. La frase es exacta para lecturas del atributo;
   para que sea exacta del todo, o se añade (2) o se cambia "acceso" por
   "lectura del atributo". El resto de §9.2 coincide con lo que verifiqué:
   los 5 sitios, los tests de bocado, sed al beber, `UMBRAL±1` y genoma a 500
   ticks.
4. E3 (indirección sin atributo ni cadena) pasa: límite inherente de un guard
   estático; `AGENTS.md` ya lo dice. No merece una ronda.
5. Arrastres de la ronda 1, sin tocar y sin bloquear:
   `supervivencia_descubridores: 0.0` con `descubridores: []` se lee como
   extinción; ids reciclables (`max+1`) pueden corromper el denominador si la
   población encoge; el diferencial es foto del último tick; el test de radio
   compara solo medias con umbrales ajustados (8.0 / 1.4).
6. Alcance limpio: `git diff` toca solo `README`, `tests/test_cli_run.py`
   (4 claves), `instinto`, `modelos`, `sim`, `arquitectura` y el test nuevo.
   Sin reformateos. No hay `.tmp-diag*.py` ni scripts temporales en el árbol.
   `secrets scan` sigue dando 13 hallazgos, todos en fixtures preexistentes de
   `agents/tests`; ninguno en el diff.
