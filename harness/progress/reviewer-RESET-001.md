# reviewer · RESET-001

- **Fecha:** 2026-11-20
- **Veredicto:** aprobado

## Gate (ejecutado en esta sesión)

```
$ uv run python -m agents --json run harness gate
"success": true
"message": "ENTORNO LISTO — se puede trabajar."
"pytest": "485 passed in 335.49s (0:05:35)"
errors 0 · warnings 0
```

Además, por mi cuenta: `ruff check` → All checks passed · `ruff format --check` → 90 files already formatted · `mypy` → Success: no issues found in 90 source files · `pytest tests/test_reset.py` → 4 passed.

## Criterios

1. **Nuevo mundo borra o archiva world.db y genera semilla nueva — CUMPLIDO.**
   Drill real en directorio temporal. Partida de 60 ticks con seed 7, luego
   `world reset --db world.db --seed 99 --yes`:
   ```
   nuevo mundo: archivado en ...\archivo\world-20261120T044509Z.db  seed 99  tick 0  -> ...\world.db
   md5 archivado == md5 del viejo: True
   archivo/: world-20261120T044509Z.db + world-20261120T044509Z.meta.json
   ```
   `--borrar` no deja `archivo/` y deja la base nueva (seed 5, tick 0). Los
   sidecars se archivan: con `world.db-wal` y `world.db-shm` plantados, ambos
   acaban como `*.db-wal` / `*.db-shm` en `archivo/` y desaparecen de la raíz.
   Semilla nueva: `random.SystemRandom().randrange(2**31)`, documentado en
   README, arquitectura §2.5 y el propio docstring; se imprime. Con `--seed` se
   respeta (99, 5, 42 verificados) y dos resets con la misma seed dan el mismo
   md5.

2. **Confirmación explícita antes de borrar — CUMPLIDO.**
   `world reset --db world.db` → `exit=2`, md5 de `world.db` y de
   `save_meta.json` idénticos antes y después, `archivo/` inexistente. El
   mensaje dice qué archivo toca, si archiva o borra, y pide `--yes`. La semilla
   se sortea *después* de confirmar, así que no anuncia una que no se usó.
   No es un flag ciego.

3. **Tras nuevo mundo tick=0 y 8-15 individuos — CUMPLIDO.**
   `report db` sobre la base nueva: `seed 99  tick 0  poblacion 12`. Los cuatro
   tests leen `Repositorio.instantanea()` y comprueban `tick == 0` y
   `MIN_INDIVIDUOS <= poblacion <= MAX_INDIVIDUOS`. `save_meta.json` coherente:
   `seed 99 · tick 0 · poblacion 12 · version 1`.

4. **Gate — CUMPLIDO.** Ver arriba, `success=true` en esta sesión.

### Extra pedido: ¿la base archivada sirve para reanudar?

Sí, es una copia fiel y reanudable:
```
$ run --headless --resume --db archivo\world-<marca>.db --ticks 5
{"seed": 7, "ticks": 65, ...}          # conserva seed 7 y sigue desde el tick 60

$ report db --db archivo\world-<marca>.db
seed 7  tick 65  poblacion 12  estacion sin estacion
nodos 18  aristas 15  arbol 18 ...
```
La cultura también continúa (aparecen `vocabulario`, `mito`, `identidad_grupo`),
así que archivar no solo conserva el fichero: conserva una partida viva.

### Extra pedido: colisión de nombres

Dos resets reales dentro del mismo segundo:
```
archivado en ...\archivo\world-20261120T044542Z.db
archivado en ...\archivo\world-20261120T044542Z-2.db
```
Ambos `.db` y sus `.meta.json` conviven; no se pisan. El sufijo `-2`, `-3`…
funciona (también probado con un `.db` ocupado de antemano).

## Bloqueantes

Ninguno.

## No bloqueante

1. **El mensaje de éxito miente cuando no había nada que archivar.** `world
   reset --db <ruta> --yes` sobre una base inexistente imprime «nuevo mundo:
   archivado en ...\archivo\world-<marca>.db» aunque `archivo/` queda **vacío**
   (y se crea el directorio para nada). No hay pérdida de datos —no había
   partida—, pero el mensaje afirma un archivo que no existe. Fix de dos líneas:
   que `archivar()` devuelva `None` si no movió nada y que `_world_reset`
   distinga «archivado en X» de «no había partida que archivar».

2. **`.gitignore` no cubre `archivo/*.meta.json`.** El README documenta
   `world reset --db data/world.db --yes`; `*.db` y `data/save_meta.json` están
   ignorados, pero `data/archivo/world-<marca>.meta.json` **no**:
   ```
   $ git check-ignore -v data/archivo/world-20261120T044542Z.meta.json
   exit=1   (no ignorado)
   ```
   Quien siga la receta del README deja un fichero commiteable en `git status`.
   Basta con añadir `data/` o `*.meta.json` al `.gitignore`.

3. **Los sidecars `-wal`/`-shm` se archivan y borran, pero ningún test lo
   cubre** (lo verifiqué a mano). El README lo promete explícitamente; un test
   con `world.db-wal` y `world.db-shm` plantados lo dejaría fijado. Igual para
   el sufijo `-2` de colisión, que tampoco tiene test.

4. **El mensaje previo a confirmar no menciona los sidecars ni que se creará
   `archivo/`**, solo `world.db` y `save_meta.json`. Menor, pero es justo lo que
   el usuario lee antes de autorizar algo destructivo.

5. **`--yes` sin `--db` cae en `data/world.db` relativo al cwd**: en un repo
   limpio crea `data/world.db` y un `archivo/` vacío sin avisar. Coherente con
   el resto de la CLI, pero es un default que escribe.

6. **concepto §17 pide el menú de ventana «Continuar / Nuevo mundo»**; esta
   feature entrega solo la vía CLI. Está declarado honestamente en el apartado
   «Estado» que se añade a `concepto.md` y en el informe del implementer, así
   que no contradice al usuario: archivar por defecto es además *menos*
   destructivo que lo que §17 describe.

## Fuera de alcance (correcto)

- No se añaden dependencias (`pyproject.toml` intacto). `tribal/reset.py` es
  stdlib y reutiliza `tribal.sim.run(0, …)` en vez de escribir SQLite a mano,
  así que el esquema y el volcado siguen teniendo un solo dueño.
- Sin `.tmp-*`, sin `data/` en el repo, `opencode.json` fuera del diff.
- `harness/featureslist.json` y `current.md` aparecen modificados, pero es
  `harness start` (status `pending`→`in_progress` + `started` + `review_rounds`),
  no una edición a mano del implementer.
- `secrets scan` solo marca fixtures preexistentes de
  `agents/tests/test_secrets_agent.py`; nada en `tribal/reset.py` ni en
  `tests/test_reset.py`.
