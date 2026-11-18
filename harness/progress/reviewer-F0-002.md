# reviewer · F0-002

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

# reviewer · F0-002 · ronda 2

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado
- **Gate ejecutado en esta sesión (dos veces, la última tras restaurar las mutaciones):**
  `success=true` — `ENTORNO LISTO — se puede trabajar.`, 0 errores, 0 avisos,
  `pytest 63 passed in 6.04s`.

## Bloqueante de la ronda 1: resuelto

El orden real en `Simulacion.step()` (`tribal/sim.py:68-110`) es ahora
`regenerar → homeostasis (evolucionar, edad, cooldown) → depredador.mover (93) →
_enterrar (94) → decisiones → reproducir`, y el docstring de `step()` documenta el
porqué. El mordisco ya no puede deshacerse: `_morder` deja la salud a 0 y `_enterrar`
la comprueba **en el mismo tick**.

Comprobado por mi cuenta, no leyendo el informe:
- Presa sana acorralada en una isla de un tile, con depredador adyacente:
  salud `100 → 70 → 43.20 → 14.80 → 0.00` en los ticks 1, 161, 241 y 248; **muere en el
  tick 248** con `muertes=1`, `depredador.muertes=1`, `ataques=4`.
- Control idéntico sin depredador: **sigue viva a 300 ticks con salud 100.00**,
  `muertes=0`. La muerte no la causa la sed (a 300 ticks la sed está a 48).
- **Mutación del orden** (`_enterrar()` antes de `depredador.mover`): el test
  `test_el_depredador_mata_a_una_presa_sana_acorralada` cae con
  `assert 0 == 1` (`tests/test_puerta_f0.py:201`) y el control sigue pasando.
  Restaurado (SHA256 `807A118A…` verificado).
- **Mutación del mordisco** (`_morder` sin restar `DANO`, solo cooldown y ataque):
  el mismo test cae con `assert 0 == 1`. Restaurado (SHA256 `AA55C4CE…` verificado).

## Criterios

1. **Edad y reproducción con herencia mínima — cumplido.** Tests estables desde la
   ronda 1; sin cambios en esta ronda. Nada tocado en `_heredar`, `MUTACION`,
   `_puede_reproducir` ni `_longevidad`.
2. **Depredador que persigue, del que se huye y configurable — cumplido, ahora también letal.**
   Persigue con desempate estable por `id`, no entra al agua, y muerde y mata.
   `depredador_activo=False` + `depredadores=2` → `{"activos": 0, "ataques": 0,
   "muertes": 0}` y lista vacía (ejecutado; test nuevo en `test_puerta_f0.py:171`).
3. **Test determinista de nacimientos — cumplido.** En 6 semillas a 3000 ticks
   `final = inicial + nacimientos − muertes` exacto (seed 1: 12+2−12=2; seed 42:
   12+14−11=15; seed 123: 12+17−11=18).
4. **Agolpamiento — cumplido.** Seed 2: `agrupamiento_max=11` (antes 9; el orden nuevo
   deja vivir/morir distinto). El README ya no dice «bebiendo»: dice «a ≤2 tiles de un
   lago» y «no necesariamente bebiendo a la vez», que es lo que mide el criterio.
5. **Huida en manada — cumplido.** El test mide distancia euclídea real; sin cambios.
6. **CLI 3000 — cumplido.** `depredador` incluye ahora `muertes`, y el total cuadra.
   Seed 2 (ejecutado hoy): `final 10, nacimientos 10, muertes 12,
   depredador {activos 1, ataques 8, muertes 3}, agrupamiento_max 11, huidas 3688`,
   idéntico a lo que pega el README. Las 3 muertes acreditadas al depredador no son
   de vejez (edades 812/3085, 2734/3034, 2834/3102), así que el «3 de ellas por
   mordiscos» es correcto. Seed 42 a 600 ticks también coincide con el README
   (`final 12, nacimientos 1, muertes 1, ataques 4, muertes 1, agrupamiento 6, huidas 49`).
7. **Gate — cumplido.** Verde en esta sesión.

## Regresiones

`git diff tests/`: no se debilitó nada, al contrario.
- `test_la_tribu_sobrevive_y_se_reproduce_en_un_mundo_con_recursos` corre ahora con
  `depredador_activo=False` y vuelve a exigir **`muertes == 0`** (el `== 0` que la
  ronda 1 había perdido), más `poblacion_final == inicial + nacimientos`,
  `nacimientos > 0`, `activos == 0`.
- `test_sin_agua_el_individuo_muere_de_sed` y `test_sin_recursos_la_tribu_se_extingue`
  **sin tocar** y en verde.
- `test_cli_run.py` y `test_config.py` solo añaden claves a los conjuntos/validaciones.
- Tests nuevos: letalidad, control de la misma presa sin depredador y
  `depredador_activo=False`.

## Calidad

- `ruff check tribal/ tests/ agents/` → `All checks passed!`
- `ruff format --check tribal/ tests/` → `27 files already formatted`
- `mypy tribal/ tests/` → `Success: no issues found in 27 source files`
- `pytest -q` completo → `592 passed, 15 skipped in 66.60s`
- `run doctor checkup` → `success=true` (7/7)
- `review_package` → solo el `_mancha` de 7 argumentos, preexistente y ajeno a este diff
- `secrets scan` → los mismos 13 hallazgos de fixtures preexistentes en `agents/tests/`;
  ninguno en los ficheros de la feature

## Render

`docs/img/fase0-puerta.png` (480×286, sin cambios y coherente): el depredador está en
el borde del lago en (91-98, 133-138), pelaje oscuro y ojo rojo, y las crías son 4×5
frente a los adultos 6×8. Se distinguen.

## No bloqueante

- `_presa_mas_cercana` no excluye a quien va a morir de vejez ese mismo tick: como
  `_enterrar` va después, un anciano con salud < 30 mordido en su último tick se
  acredita como muerte del depredador. En seed 2 no ocurrió (las 3 acreditadas están a
  más de 200 ticks de su longevidad), pero es una atribución aproximada.
- La línea de texto del CLI no imprime las muertes del depredador (solo el JSON); el
  criterio se cumple por JSON y por `ataques`.
- `huidas` sigue contando también la rama «apartarse del vecino» con salud crítica
  (`tribal/agents/instinto.py:49-52`), 0-2 % del total. Sin cambios desde la ronda 1.
- El README sigue diciendo que el depredador «recorre el mapa»; pasa la mayor parte de
  los ticks quieto (digestión de 80 y orilla cuando la presa está al otro lado del lago).
- Alcance: sin dependencias nuevas, `agents/` sin tocar, `harness/` solo vía `harness`,
  sin `.tmp-*`, y las dos mutaciones restauradas con hash verificado antes del gate final.
