# implementer · F3-001

- **Fecha:** 2026-11-19
- **Veredicto:** ok

# Implementer — F3-001

## Qué cambié

- `tribal/store/esquema.py`: DDL de stack §5 (9 tablas), `TABLAS`, `PRAGMAS`;
  solo texto, sin importar `sqlite3`.
- `tribal/store/repositorio.py`: `Repositorio` (`guardar`, `cargar`,
  `instantanea`, `cerrar`), `Estado`, `IndividuoGuardado`, `BaseInvalida`.
  Único módulo con `import sqlite3`; volcado completo transaccional; grafo
  reconstruido con `origen`/`autor`/`tick`/`requisitos`.
- `tribal/store/__init__.py`: exporta la interfaz.
- `tribal/sim.py`: `Simulacion(..., db=None)`, volcado cada
  `config.ticks_guardado` ticks y al cerrar (`cerrar()`); `run(..., db=...)`
  cierra la conexión en `finally`.
- `tribal/config.py`: `ticks_guardado: int = 300` en `CAMPOS_ENTEROS` y
  validación > 0.
- `tribal/cli.py`: `run --db` y `report db --db ... [--json]` (0 válida, 2 no).
- `tests/test_store.py`: 7 tests (esquema, reapertura, CLI, intervalo,
  semillas, errores, único importador).
- `tests/test_config.py`: clave nueva en defaults.
- `tests/test_divergencia_calma.py` / `tests/test_puerta_f1.py`: whitelist del
  serializador (`_fila_individuo`); no lee el rasgo para decidir nada.
- `README.md` (BD, esquema, comandos, límite), `vault/01_PROYECTO/arquitectura.md`
  (§2.5 y §5.3) y `.gitignore` (`*.db*`).

## Criterios de aceptación

1. Tablas de stack §5 — `uv run pytest tests/test_store.py -v` →
   `test_el_esquema_crea_las_tablas_de_stack5 PASSED` (además comprueba
   `journal_mode=wal` y columnas `origen/autor/tick` de `nodos`).
2. `run --db` + reapertura — salida literal abajo: `report db` da
   `poblacion 16  nodos 30  aristas 27`, igual que el resumen del `run`;
   `test_run_db_escribe_la_partida_y_report_db_coincide PASSED`.
3. Un solo importador — grep abajo: exactamente 1 coincidencia,
   `tribal/store/repositorio.py:19`; `test_solo_el_repositorio_importa_sqlite3
   PASSED`.
4. Reapertura conserva nodos/aristas/origen —
   `test_cerrar_y_reabrir_conserva_nodos_aristas_y_origen PASSED` (compara
   `Nodo` completo, tuplas `(origen, autor, tick)`, aristas y población).
5. Gate — `"success": true`, `ENTORNO LISTO — se puede trabajar.`

## Evidencia

`uv run python -m tribal run --headless --ticks 600 --db tribu.db`:

```
seed 42  ticks 600  poblacion 12 -> 16
muertes 0  nacimientos 4  individuos movidos 16
depredadores 1  ataques 0  agrupamiento max 9  huidas 266
media energia 75.23  media sed 34.51
estacion sin estacion  parches 19  migraciones 0
diario entradas 5  narradas 0  dialogos 0
     12  primera_tradicion  (sin narracion)
     13  primera_caza_grupo (sin narracion)
     86  primera_palabra    (sin narracion)
RUN_EXIT=0
```

`uv run python -m tribal report db --db tribu.db`:

```
seed 42  tick 600  poblacion 16  estacion sin estacion
nodos 30  aristas 27  arbol 23  combinacion 0  interaccion 7  llm 0
diario 5  telemetria 2  recursos 89  recuerdos 0
REPORT_EXIT=0
```

`--json`: `{"db": "tribu.db", "tick": 600, "seed": 42, "estacion": null,
"poblacion": 16, "nodos": 30, "nodos_por_origen": {"arbol": 23,
"combinacion": 0, "interaccion": 7, "llm": 0}, "aristas": 27, "diario": 5,
"telemetria": 2, "recursos": 89, "recuerdos": 0}`

Único `import sqlite3`:

```
tribal\store\repositorio.py:19:import sqlite3
COINCIDENCIAS=1
```

`uv run pytest tests/test_store.py -v`:

```
tests/test_store.py::test_el_esquema_crea_las_tablas_de_stack5 PASSED    [ 14%]
tests/test_store.py::test_cerrar_y_reabrir_conserva_nodos_aristas_y_origen PASSED [ 28%]
tests/test_store.py::test_run_db_escribe_la_partida_y_report_db_coincide PASSED [ 42%]
tests/test_store.py::test_la_telemetria_se_escribe_por_intervalo_y_al_cerrar PASSED [ 57%]
tests/test_store.py::test_dos_semillas_producen_bases_distintas PASSED   [ 71%]
tests/test_store.py::test_report_db_sale_con_2_si_la_base_no_sirve PASSED [ 85%]
tests/test_store.py::test_solo_el_repositorio_importa_sqlite3 PASSED     [100%]
============================== 7 passed in 5.46s ==============================
```

`uv run pytest -q`: `966 passed, 15 skipped in 309.14s (0:05:09)`

Lint/typecheck (Makefile no existe en este Windows; mismos comandos):

```
All checks passed!
RUFF_CHECK=0
78 files already formatted
RUFF_FORMAT=0
Success: no issues found in 78 source files
MYPY=0
```

`bash ./init.sh`:

```
━━ init.sh · arnés de Tribal ━━
Entorno     ✔ python / ✔ uv / ✔ venv
Arnés       ✔ AGENTS.md ✔ featureslist.json ✔ current.md ✔ history.md ✔ subagentes
Backlog     ✔ featureslist  45 features · 13 pending · 1 in_progress · 27 done · 4 blocked
            ✔ siguiente tarea  F3-001 — Memoria colectiva como grafo persistido en SQLite [in_progress]
Proyecto    ✔ paquete tribal/ ✔ pyproject ✔ tests 34 ficheros
Verificación ✔ pytest  410 passed in 230.21s (0:03:50)
━━ ENTORNO LISTO ━━  0 aviso(s)
INIT_EXIT=0
```

`uv run python -m agents --json run harness gate`: `"success": true`,
`"message": "ENTORNO LISTO — se puede trabajar."`, `"ready": true`,
`"errors": 0`, `"warnings": 0` (pytest `410 passed in 216.64s`).

## Qué falta

- **Reanudar la partida es SAVE-001**, no esta feature: `cargar()` devuelve
  grafo + población + `mundo`/`seed`/`config` para leer y verificar; tiles,
  azar y contadores del motor no se rehidratan.
- `relaciones` y `recuerdos` se crean con su esquema pero se escriben vacías:
  el motor no modela vínculos y `IndiceRecuerdos` no expone los textos.
- `report telemetry --db` sigue sin leer la tabla: la telemetría persistida se
  cuenta con `report db`.
- Nota: `vault/01_PROYECTO/auditoria-llm.md` aparece modificado en `git status`
  y no lo toqué yo.
