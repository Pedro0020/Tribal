# implementer · AMB-001

- **Fecha:** 2026-11-18
- **Veredicto:** ok

# Implementer — AMB-001 (ronda 2): arreglo del bloqueante B1 (bayas que no migraban)

## Qué cambié

- `tribal/core/recursos.py`: `_reubicar` ya no exige que **cada fuente** destino quede
  a ≥2 tiles de **cualquier otra** del mismo tipo. El filtro es ahora fuente-a-fuente con
  `DISTANCIA_ENTRE_FUENTES = 1.0` (prohíbe apilar dos fuentes en la misma casilla; deja
  pasar las vecinas), más las invariantes que ya había: centro en el terreno que toca,
  ≥6 tiles del centro viejo y **toda** fuente en casilla pisable (nunca agua ni fuera del
  mapa). Elegí esta opción, y no la de comparar centros, porque medí ambas: con centros a
  ≥`RADIO_PARCHE`=4 los candidatos válidos para las bayas eran **0** en las 6 semillas
  (los parches de bayas se tocan por construcción del enlace simple); con 1 tile hay
  entre 7 y 19 casillas válidas de 76 de bosque. Además el orden de las casillas se
  **baraja** con `Mundo.azar` y se toma la primera válida: determinista por semilla y sin
  el fallo probabilístico de 40 intentos al azar (`INTENTOS_REUBICAR` desaparece).
  Documentado en el docstring el porqué del criterio.
- `tribal/sim.py`: `_parches()` calcula `abundancia()` una sola vez por parche.
- `tests/test_ambiente.py`: 5 tests nuevos (bayas en mundo real, caza en mundo real, agua
  que no migra, destino con fuente en agua rechazado, partida normal que migra ambos
  tipos) y el test de mecanismo ahora arranca a los dos individuos **en la misma casilla,
  con el mismo genoma y el mismo sexo**, con `assert` de las tres cosas.
- `README.md`: corregida la descripción del filtro (fuente a fuente con 1 tile, no «sin
  pisar otras fuentes», y fuentes en casilla pisable) y regeneradas todas las salidas
  reales que cambian al consumir el azar de otra forma (JSON de 600 ticks, resumen legible
  de seed 7, ejemplo de estaciones, 3000 ticks de seed 2, telemetría de 2000 en crisis y
  los dos ejemplos de 5000).

## Criterios de aceptación

1. **Parches que se agotan y migran.** Bayas y caza migran por igual: la tabla del
   barrido lo enseña (todos los parches de comida de cada mapa, 0 de agua). Determinista
   por semilla (`test_la_migracion_es_determinista_y_depende_de_la_semilla`, y los dos
   subprocesos del criterio 4).
2. **Test de mecanismo.** `test_seguir_el_parche_sobrevive_mas_que_quedarse_en_la_zona_agotada`:
   mismo mundo, misma casilla de salida, mismo `Genoma()`, mismo sexo; el que sigue el
   parche sigue vivo a los 1200 ticks, el que patrulla la zona agotada muere en el 834.
3. **Resumen.** `estacion`, `parches` (id, tipo, activo, abundancia, x, y) y
   `migraciones`, en el JSON y en la línea legible.
4. **Dos subprocesos / otra semilla.** `test_dos_procesos_iguales_y_otra_semilla_migra_a_otro_sitio`.
5. **Verde.** Abajo: `pytest -q`, ruff, format, mypy, `./init.sh` y gate.

## Evidencia

### Barrido 6 semillas × 2 mapas (todos los parches agotados a mano, 10 ticks de `migrar`)

| mapa | seed | parches bayas | parches caza | migr. bayas | migr. caza | migr. agua | fuentes invalidas | max fuentes/casilla |
|---|---|---|---|---|---|---|---|---|
| 60x34 | 1 | 6 | 7 | 6 | 7 | 0 | 0 | 1 |
| 60x34 | 2 | 5 | 7 | 5 | 7 | 0 | 0 | 1 |
| 60x34 | 3 | 3 | 8 | 3 | 8 | 0 | 0 | 1 |
| 60x34 | 42 | 6 | 8 | 6 | 8 | 0 | 0 | 1 |
| 60x34 | 5 | 6 | 7 | 6 | 7 | 0 | 0 | 1 |
| 60x34 | 6 | 6 | 8 | 6 | 8 | 0 | 0 | 1 |
| 80x50 | 1 | 5 | 8 | 5 | 8 | 0 | 0 | 1 |
| 80x50 | 2 | 4 | 8 | 4 | 8 | 0 | 0 | 1 |
| 80x50 | 3 | 6 | 8 | 6 | 8 | 0 | 0 | 1 |
| 80x50 | 42 | 5 | 8 | 5 | 8 | 0 | 0 | 1 |
| 80x50 | 5 | 6 | 7 | 6 | 7 | 0 | 0 | 1 |
| 80x50 | 6 | 6 | 8 | 6 | 8 | 0 | 0 | 1 |

`migr. agua = 0` y `max fuentes/casilla = 1` en los 12 casos: el agua no se mueve y no se
apilan fuentes. Sin el arreglo, las migraciones de bayas eran 0 en 11 de los 12 casos.

Antes/después del mismo cálculo de candidatos para un parche de bayas (seed 1, 76 tiles
de bosque): filtro viejo **0** válidos; filtro nuevo **7**.

### Mutaciones

| Mutación | Test que cae |
|---|---|
| `migrar` salta `BAYAS` (`if parche.tipo in (AGUA, BAYAS): continue`) | `test_los_parches_de_bayas_migran_en_el_mundo_real` y `test_una_partida_normal_acaba_migrando_bayas_y_caza` |
| se quita el `continue` del agua (el agua migra) | `test_el_agua_no_migra_aunque_se_agote` → `assert [Parche(id=1, tipo=AGUA …)] == []` |
| se quita `if not all(mundo.pisable(...))` (destino en agua permitido) | `test_no_se_migra_a_una_zona_con_fuentes_en_agua` → el parche aterriza en `(6, 11)` con su segunda fuente en el lagо |

Las tres se revirtieron; `git diff` no contiene ninguna marca de mutación.

### Partida normal (seed 42, 1500 ticks, sin tocar nada)

`{AGUA: [0,0,0], BAYAS: [0,0,0,1,0,0], CAZA: [2,2,0,4,1,0,0,1]}` → bayas y caza migran
sin intervención (`test_una_partida_normal_acaba_migrando_bayas_y_caza`).

### Comandos

```
$ uv run pytest -q
735 passed, 15 skipped in 119.46s (0:01:59)

$ uv run ruff check tribal/ tests/ agents/
All checks passed!
$ uv run ruff format --check tribal/ tests/
45 files already formatted
$ uv run mypy tribal/ tests/
Success: no issues found in 45 source files

$ ./init.sh
  ✔ pytest                 206 passed in 58.13s
━━ ENTORNO LISTO ━━  0 aviso(s)

$ uv run python -m agents --json run harness gate
  "success": true,
        "check": "pytest",
        "status": "ok",
        "detail": "206 passed in 57.80s"
```

### Salidas del README regeneradas (medidas con este código)

- `run --headless --ticks 600 --json`: línea completa sustituida (7176 caracteres).
- `run --seed 7 --benchmark --headless --ticks 600`: `huidas 160`, `media energia 45.37`,
  `media sed 43.55`, `estacion sin estacion  parches 16  migraciones 5`.
- Estaciones de 150 (`{"seed": 42, "individuos": 12, "ticks_por_estacion": 150}`):
  `poblacion 12 -> 13`, `estacion primavera`, `migraciones 4`; ejemplo de parche de caza
  `abundancia 1.0` en `(15.0, 3.0)`.
- `--seed 2 --ticks 3000`: `poblacion_final 13`, `nacimientos 14`, `muertes 13`,
  6 ataques, `huidas 526`, `migraciones 13`, `agrupamiento_max 17`.
- `--ticks 2000 --crisis`: `descubridores [1, 2, 9]`, `supD 1.0`, `supN 0.938`,
  `diferencial 0.062`.
- `--ticks 5000 --crisis`: `migraciones 45`, `beneficios {"bayas": 1.0469, "caza": 1.0337,
  "dano_depredador": 0.9777, "tasa_sed": 0.9821}`, `escasez {"agua": 0.5, "bayas": 0.526,
  "caza": 0.125}`. `--ticks 5000` en calma: `migraciones 18`, `arbol 23`.

## Qué falta

- El cooldown (240 ticks) y el umbral (0.25) siguen siendo constantes de módulo, no
  config por tipo: es lo que pide el eje 3, no más perillas.
- La regeneración en invierno frena también el agua (el gancho de utilidad no): es
  inconsistente narrativamente pero inocuo; lo dejo anotado para cuando haya clima por
  bioma.
- `config.validar` sigue creciendo; si entra una validación más, toca partirla.
