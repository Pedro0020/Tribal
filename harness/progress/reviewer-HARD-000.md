# reviewer · HARD-000

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

## Criterios

1. **SimConfig con seed, individuos, mapa y tasas, serializable — CUMPLIDO.**
   `tribal/config.py`: `@dataclass(frozen=True, slots=True)` con 7 campos,
   `a_json()` / `desde_json()`. Defaults idénticos a Fase 0
   (`{42, 12, 60, 34, 0.16, 0.15, 0.6}`; `ANCHO_TILES/ALTO_TILES` = 60/34).
   Lo comprobé por comportamiento, no por lectura: con `docs/config-ejemplo.json`
   (`--ticks 600`) el resumen sale `media_energia 66.62, media_sed 42.32`, los
   mismos números que el README previo al cambio ⇒ los defaults no alteran nada.
   Validación ahora sí real:
   - tipos: `seed/individuos/ancho/alto` enteros y no `bool`, tasas `int|float`
     y no `str`/`bool` (`CAMPOS_ENTEROS` / `CAMPOS_TASA`);
   - rangos: `individuos` 8–15, `ancho`/`alto` ≥ `MIN_LADO = 9` (mínimo real de
     `_mancha`: `randint(4, lado - 5)`), tasas > 0;
   - todo error nombra clave y valor (`recibido {valor!r}`), sin `except TypeError`
     filtrando mensajes de Python.
   Round-trip cubierto por `test_json_ida_y_vuelta` y por el eco `config` del CLI.

2. **`run --headless --config cfg.json --json` usa y refleja la config — CUMPLIDO.**
   Ejecutado con el fichero del repo:
   `{"seed": 42, ..., "config": {"seed": 42, "individuos": 12, "ancho": 60, "alto": 34, "tasa_sed": 0.16, "tasa_energia": 0.15, "tasa_salud": 0.6}}`, exit 0.
   Precedencia CLI > fichero > defaults, verificada por CLI:
   `--config docs/config-ejemplo.json --seed 7 --individuos 9` →
   `"seed": 7, "poblacion_inicial": 9, "config": {"seed": 7, "individuos": 9, ...}`, exit 0.
   Config válida en el borde no rompe: `{"ancho": 9, "alto": 9, "seed": 3, "individuos": 8}`
   → exit 0 con resumen correcto (`9x9`, 8 individuos).

3. **Test: misma semilla+config ⇒ mismo resumen; cambiar un parámetro ⇒ resultado distinto — CUMPLIDO.**
   - Repetibilidad real: dos procesos distintos
     (`python -m tribal run --headless --json --ticks 60 --config cfg.json` con
     `{"seed": 4, "individuos": 9}`) dan stdout **idéntico** (`identicas=True`);
     lo cubre además `test_dos_ejecuciones_del_cli_con_la_misma_config_son_identicas` (subprocess).
   - Test de cambio de tasa ya **no es vacuo**: `_metricas()` excluye `config`
     y además asevera `media_sed`. Verificado por mutación propia: sustituido
     `necesidades.evolucionar(necesidades, genoma, tasa_sed, tasa_energia, tasa_salud)`
     por `necesidades.evolucionar(necesidades, genoma)` en `sim.step` →
     `1 failed, 21 passed`, fallando exactamente
     `test_cambiar_una_tasa_cambia_el_resumen` en
     `tests/test_config.py:148`. Fichero restaurado y
     `git diff --stat tribal/sim.py` vuelve a `34 insertions(+), 7 deletions(-)`.
   - El parámetro cambia el resultado de verdad: `tasa_sed 0.16 → 0.3`
     mueve `media_sed` y `media_energia` (ya comprobado en ronda 1 y de nuevo
     en el test).
   - La config no se cuela de forma no determinista: `asdict` de un frozen con
     orden de campos fijo, sin relojes; las dos corridas byte a byte lo confirman.

4. **README documenta la configuración y un ejemplo — CUMPLIDO.**
   Sección «Configuración y semilla» con JSON de ejemplo, comando, lista de
   errores actualizada (**9×9 mínimo**, tipos equivocados con ejemplo:
   `"ancho": 60.7`, `"seed": "hola"`, `"individuos": true`) y precedencia con
   ejemplo. `docs/config-ejemplo.json` = `SimConfig()`. El JSON de salida del
   README coincide con la ejecución real de esta sesión, incluido `config`, y no
   incluye `ms_tick_medio`.

5. **`harness gate success=true` — CUMPLIDO.**
   `"success": true`, `"ENTORNO LISTO — se puede trabajar."`, 14 checks ok,
   0 errores, 0 avisos, `pytest 48 passed in 2.46s`.

### Verificación adicional (ejecutada en esta sesión)

Los 8 casos de config inválida, por el CLI real (stderr, exit code, sin traza):

| fichero | exit | stderr |
|---|---|---|
| `{"ancho": 6}` | 2 | `ancho y alto deben ser al menos 9 tiles` |
| `{"ancho": 60.7}` | 2 | `ancho debe ser un entero (recibido 60.7)` |
| `{"tasa_sed": "0.2"}` | 2 | `tasa_sed debe ser un número (recibido '0.2')` |
| `{"seed": "hola"}` | 2 | `seed debe ser un entero (recibido 'hola')` |
| `{"individuos": true}` | 2 | `individuos debe ser un entero (recibido True)` |
| `{"individuos": 5}` | 2 | `individuos debe estar entre 8 y 15 (recibido 5)` |
| `{"tasa_salud": -0.1}` | 2 | `tasa_salud debe ser mayor que 0 (recibido -0.1)` |
| `{"gravedad": 9.8}` | 2 | `claves desconocidas: gravedad` |

Ninguno imprime `Traceback`. Todos nombran la clave.

- `uv run ruff check tribal/ tests/ agents/` → `All checks passed!`
- `uv run ruff format --check tribal/ tests/` → `25 files already formatted`
- `uv run mypy tribal/ tests/` → `Success: no issues found in 25 source files`
- `uv run pytest -q` → **`577 passed, 15 skipped in 61.81s`** (coincide con el informe)
- `uv run pytest -q tests/test_config.py` → `22 passed`
- Determinismo del motor intacto: un único `random.Random(seed)` en `Mundo.azar`;
  `mundo.py` solo parametriza dimensiones con los mismos defaults; no hay azar nuevo.
- Alcance: sin dependencias nuevas (`pyproject.toml` sin tocar), sin `.tmp-*`,
  `featureslist.json`/`current.md` con la transición legítima de `harness start`,
  ningún cambio en `harness/` a mano ni en `agents/`.

## Bloqueantes

Ninguno. Los dos de la ronda 1 están resueltos y verificados por mi propia
ejecución y por mutación.

## No bloqueante

- `validar()` solo se invoca desde `desde_json`. Un `SimConfig(ancho=6)`
  construido a mano en Python no se valida; es aceptable (el camino no confiable
  es el fichero), pero si algún día el motor acepta configs de otra fuente, la
  validación debería vivir en el constructor o en `crear()`.
- `MIN_LADO = 9` está justificado en comentario y respaldado por el caso borde
  que probé (9×9 funciona, 6 falla); si cambia el radio de `_mancha`, el número
  se queda obsoleto en silencio. Un test de borde 9×9 que genere el mapa
  cerraría ese hueco.
- `test_misma_semilla_y_config_dan_el_mismo_resumen` sigue siendo intra-proceso;
  ahora es redundante pero inocuo junto al test de subprocess.
- `resumen()` mantiene `dict[str, Any]`; un `TypedDict` conservaría el tipado
  del payload público. Cosmético.
- `seed` no tiene cota (negativa o enorme se acepta); es determinista igual, no
  rompe nada, pero contrasta con el resto de campos validados.
