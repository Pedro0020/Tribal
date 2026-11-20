# reviewer · SAVE-001

- **Fecha:** 2026-11-20
- **Veredicto:** aprobado

# reviewer · SAVE-001

- **Fecha:** 2026-11-20
- **Veredicto:** aprobado
- **Puerta (ejecutada en esta sesión):**
  `uv run python -m agents --json run harness gate` → `success=true`,
  `"ENTORNO LISTO — se puede trabajar."`, `checks.pytest = 480 passed in 324.88s`,
  `ready=true`, `errors=0`.

## Criterios

1. **`data/world.db` + `save_meta.json` al cerrar con COMMIT coherente — CUMPLIDO.**
   - `guardar()` hace `COMMIT` (`with conexion`) y solo después `_escribir_meta()`;
     la meta se escribe con temporal + `os.replace` (atómica).
   - Verificado contra la base, no solo contra el test: tras 300 ticks,
     `meta.tick == Estado.tick == partida.mundo.tick == 300`,
     `meta.seed == config.seed`, `meta.config == config de la base`,
     `meta.rng == getstate()` del `Random` guardado (versión 3, 625 enteros,
     `gauss_next`), `meta.poblacion == len(mundo.individuos)`,
     `meta.nodos == len(grafo.nodos)`, `version=1`, `nombre` correcto.
     Sin `save_meta.json.tmp` residual tras guardados normales.
   - Fallo de escritura de meta simulado (tmp ocupado por un directorio):
     `OSError`, `PRAGMA integrity_check == ok`, la base reabre en el tick 120 y
     reanuda. Test `test_un_fallo_al_escribir_meta_no_corrompe_la_base`.
   - Muerte brusca real (subproceso que hace `_guardar()` y `os._exit(9)` sin
     cerrar la conexión, dejando WAL): `integrity_check == ok`, tick 300,
     reanuda a 350.
   - Meta obsoleta/falsa (tick=1, seed=999) no afecta al reanudar: la base es
     la fuente de verdad, y la meta se reescribe al siguiente guardado.
     `creado` se conserva.
   - Reanudar **sin** `save_meta.json` funciona: no es un error, por diseño la
     meta es un resumen y no la fuente de verdad (README §Persistencia y
     arquitectura §2.5). No es el "error claro" que pedía el guion, pero es el
     comportamiento documentado y más robusto; no lo considero fallo.
2. **Reanudar carga y sigue desde el tick guardado — CUMPLIDO.**
   - `run(250) → Repositorio.cargar().partida.mundo.tick == 250`; `run(…, resume=True)`
     termina en 300.
   - CLI: 60 + `--resume` 60 = `ticks=120`, seed y config de la base; sin
     `--resume` sobre base existente → rc 2 ("ya existe"); `--resume --fresh` →
     rc 2; `--resume --seed 9` → rc 2; `--resume` sobre base inexistente → rc 2
     ("no existe"); `--resume` con base sin volcado completo → `BaseInvalida`
     con mensaje claro ("no tiene volcado completo"); `--fresh` sigue borrando
     y empieza de cero (rc 0, ticks=30).
   - Telemetría: 300+300 produce exactamente las mismas filas que 600 seguidos
     (sin duplicados).
3. **Semilla y RNG guardados/restaurados (determinismo) — CUMPLIDO.**
   Matriz ejecutada por mí con LLM off, `resumen()` + `evaluar()` (report kpi) +
   `getstate()` final:
   | seed | crisis | 600 seguidos vs 300+reanudar 300 | dos reanudaciones | KPI | RNG final |
   |---|---|---|---|---|---|
   | 42 | no | idéntico | idéntico | idéntico | idéntico |
   | 42 | sí | idéntico | idéntico | idéntico | idéntico |
   | 7 | no | idéntico | idéntico | idéntico | idéntico |
   | 7 | sí | idéntico | idéntico | idéntico | idéntico |
   Además: 350 seguidos == muerte brusca en 300 + reanudar 50 (resumen idéntico).
   Las dos reanudaciones parten de copias de la misma base y dan el mismo
   `resumen()` y el mismo estado de RNG.
4. **Gate — CUMPLIDO.** `success=true` (arriba). Además ejecuté:
   `ruff check` → "All checks passed!"; `ruff format --check` → "88 files
   already formatted"; `mypy tribal/ tests/` → "Success: no issues found in 88
   source files"; `pytest -q` completo → **1036 passed, 15 skipped in 412.69s**
   (incluye `test_puerta_f1.py`, `test_puerta_f2.py` y las suites F3 de
   kpi/telemetría/export); `run --headless --ticks 300 --benchmark` → **0.70
   ms/tick, cabe en 16.67 ms**; `doctor checkup` → 7/7.

## Mutaciones que probé (fuera de los tests del implementer)

- Matriz semilla × crisis de arriba (4 configuraciones, 600 vs 300+300).
- Copia de la base con `sqlite3.backup` y dos reanudaciones independientes.
- Comparación `save_meta.json` ↔ SQLite campo a campo.
- Fallo de `_escribir_meta` con el `.tmp` ocupado; integridad y reapertura.
- Muerte brusca con `os._exit(9)` y WAL sin checkpoint; integridad y reanudación.
- Meta con tick/seed falsos; reanudación y reescritura.
- Borrado de la meta antes de reanudar.
- CLI completa de `--resume/--fresh` incluidos los rechazos.
- Ruta por defecto con ventana (`run` sin `--db`, `app.bucle` simulado): crea
  `data/world.db` y `data/save_meta.json`, rc 0.
- Reanudar con `--llm stub --llm-sincrono`: no rompe (60+60 = 120 ticks).

## Qué no se restaura (y si está documentado)

- **Paseo e intención LLM SÍ se restauran**: `paseo`, `ultimo_recurso`,
  `ultimo_parche`, `ultimo_parche_migracion` e `intencion_llm` tienen columna y
  se rehidratan en `_leer_individuos`.
- **No se restaura la memoria LLM**: `IndiceRecuerdos` se crea vacío al
  reanudar con cola (observado: `recuerdos` 15 → 7, se reindexa con lo nuevo);
  `relaciones` y `recuerdos` siguen vacías. Documentado en README
  ("reanudar con LLM encendido reconstruye el mundo pero no la memoria
  indexada; la garantía de partida exacta es con la capa LLM apagada") y en
  `vault/01_PROYECTO/arquitectura.md` §2.5.
- No se restaura `ms_acumulados` (tiempo de reloj de pared); no forma parte de
  `resumen()` ni del determinismo.

## Bloqueantes

Ninguno. Los cuatro criterios se cumplen con evidencia ejecutada en esta sesión.

## No bloqueante

- **`.gitignore` no cubre la meta**: `*.db` ignora `data/world.db`, pero
  `git check-ignore data/save_meta.json` falla. La primera sesión con ventana
  deja `data/save_meta.json` sin trackear (no está en el repo ni en el diff).
  Fix de una línea: añadir `data/` o `save_meta.json` al `.gitignore`.
- **README duplica una línea**: "Salida real de `report db` sobre la partida de
  600 ticks:" aparece en las líneas 845 y 847.
- **Telemetría en saves no alineados**: cerrar en un tick que no es múltiplo de
  `ticks_telemetria` deja una muestra extra (250+50 → `[…240, 250, 300]` frente
  a `[…240, 300]`). No hay duplicados y no afecta a `resumen()`/KPI; es el
  comportamiento preexistente de conservar el estado final como última muestra.
  Si se quiere paridad exacta de `report telemetry` en cualquier punto de
  guardado, habría que marcar/omitir esa muestra de cierre.
- **Un fallo de meta aborta la sesión**: `_escribir_meta` propaga `OSError`
  desde `guardar()`/`cerrar()` aunque la base ya está commiteada y la meta sea
  no autoritativa (el test lo consagra). Un warning en vez de excepción sería
  más coherente con "resumen, no fuente de verdad".
- **`--fresh` no borra `save_meta.json`**: hasta el primer guardado del nuevo
  proceso, la meta puede describir la partida anterior (la base manda).
- **`Repositorio.__init__` crea el directorio padre incluso con `crear=False`**:
  una ruta errónea en `evaluar()`/uso de librería puede dejar un directorio y
  una base vacía. La CLI ya valida `is_file`/`exists` antes.
- Estilo: `guardar` mide 142 líneas y `_par`/`_intencion` son casi idénticas
  (review_package). Sin impacto funcional.
- `secrets scan` devuelve 13 hallazgos, todos en `agents/tests/*` (fixtures de
  los tests de redacción/secretos), ninguno en el diff; además avisa de que
  `detect-secrets` no está instalado.
- `test coverage_report` agotó su timeout de 600 s (suite completa con
  cobertura), no un fallo del código. Cobertura dirigida de `tests/test_save.py`:
  `tribal/store/repositorio.py` 90 %, `tribal/sim.py` 68 %.
- `opencode.json` está versionado desde el commit inicial `6b96627` y no se ha
  tocado en SAVE-001; no aparece en el diff. Si se quería "fuera", es un cambio
  aparte.
- Sin dependencias nuevas (`pyproject.toml`/`uv.lock` sin cambios), sin rutas
  absolutas en el diff, sin ficheros `.tmp-*`, sin `data/` en el repo.
