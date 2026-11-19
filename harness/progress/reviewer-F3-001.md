# reviewer · F3-001

- **Fecha:** 2026-11-19
- **Veredicto:** rechazado

## Puerta (esta sesión)

`uv run python -m agents --json run harness gate` → `success: true` · `ready: true` ·
`errors: 0` · `warnings: 0` · pytest `410 passed in 218.32s`.
`uv run pytest -q` → `966 passed, 15 skipped in 285.82s`.

## Criterios

1. **Esquema con las 9 tablas de stack §5 — CUMPLIDO.** Creé la BD con
   `run --headless --ticks 600 --db` y la inspeccioné con `sqlite3`: están
   `individuos, relaciones, recursos, mundo, nodos, aristas, recuerdos, diario,
   telemetria` (+ `sqlite_sequence` interno). Columnas cotejadas con
   `stack-tecnologico.md` §5: coinciden, y las extras están justificadas
   (`nodos.origen/autor/tick/nivel/requisitos` —el KPI no se reconstruye sin
   ellas—; `mundo.seed/ancho/alto/config`; `diario.individuo_id/narrador_id/narrada`).
   `PRAGMA journal_mode=wal`, `integrity_check=ok`. `esquema.py` es solo texto y
   no importa `sqlite3`.

2. **`run --db` escribe y al reabrir grafo y población coinciden — CUMPLIDO.**
   `report db --json` da `poblacion 16  nodos 30  aristas 27` con
   `arbol 23 / combinacion 0 / interaccion 7 / llm 0`, `diario 5`, `telemetria 2`,
   `recursos 89`, idéntico al JSON del `run` (comparado campo a campo por script,
   no a ojo: seed, tick, población, n.º de nodos, orígenes, aristas, diario,
   recursos y telemetría → todo `True`). Reabrí con `Repositorio(crear=False)`:
   los 30 nodos iguales, las 27 aristas iguales, `veces_usado` igual (23),
   `config` igual y los 16 individuos comparados **campo a campo**
   (edad, sexo, energía, salud, sed, genoma, habilidades, saliencia, vivo) con
   0 diferencias.

3. **Un único módulo importa `sqlite3` — CUMPLIDO.** `grep` en `tribal/`:
   exactamente `tribal/store/repositorio.py:19`. `store/esquema.py` no lo importa.
   Mutación: añadí `import sqlite3` a `tribal/cli.py` → el test cae con
   `{'cli.py', 'repositorio.py'} == {'repositorio.py'}`.

4. **Test de reapertura conserva nodos, aristas y origen — CUMPLIDO.**
   `tests/test_store.py` (7 tests) pasa. `test_cerrar_y_reabrir...` compara
   `Nodo` completo, la terna `(origen, autor, tick)`, la lista de aristas y la
   población. Mordida comprobada con tres mutaciones (abajo).

5. **Gate — CUMPLIDO.** Ver línea de arriba (`success=true`).

## Mutaciones (aplicadas y revertidas; hashes restaurados)

| Mutación | Resultado | ¿Muerde? |
|---|---|---|
| No escribir `origen` (`nodo.origen` → `""`) | FAILED en `assert ('', 3, 1) == ('arbol', 3, 1)` (`guijarro`) | **sí** |
| `grafo.aristas` → `grafo.aristas[:1]` | FAILED en la comparación de aristas | **sí** |
| `mundo.individuos` → `[:5]` | FAILED en la comparación de población | **sí** |
| `import sqlite3` añadido a `tribal/cli.py` | FAILED en el test del importador único | **sí** |

`tribal/store/repositorio.py` y `tribal/cli.py` quedaron byte-idénticos
(sha256 comprobado) y `git diff --stat` volvió al estado del informe.

## Verificaciones adicionales (hechas por mí)

- **Exit 2:** fichero de texto → 2 (`no es una base SQLite válida`); SQLite vacía
  → 2 (`faltan tablas de la partida`); ruta inexistente → 2. Y `report db` no
  ejecuta DDL: tras el intento sobre la BD vacía sigue con **0 tablas**.
- **Lote por intervalo:** instrumenté `Repositorio.guardar` → **3 llamadas en 600
  ticks** (tick 300, tick 600 y el cierre), no por frame.
- **COMMIT con excepción:** `run` con un `step` que revienta en el tick 37 →
  la BD queda escrita y reabrible (tick 36, 15 nodos, 12 aristas, 12 individuos),
  sin `-wal` colgando. `guardar` usa `with conexion:` (commit/rollback) y
  `cerrar()` cierra en `finally`.
- **WAL:** `journal_mode=wal` en la BD recién creada; `foreign_keys=ON` se aplica
  por conexión en cada apertura (en una conexión externa sale 0, es lo esperado).
- **`.gitignore`:** `git check-ignore` confirma `*.db`, `*.db-wal`, `*.db-shm`.
  Tras la suite completa no queda ninguna `*.db` en el repo (solo `.mypy_cache`).
- **60 fps:** `run --headless --ticks 600 --benchmark` → `0.62 ms/tick`, cabe en
  16.67. `MS_FRAME` intacto.
- **F2 intacto:** el diff no toca `tribal/core`, `tribal/agents`, `tribal/culture`
  ni `tribal/ui`; los cambios de `test_divergencia_calma.py` y `test_puerta_f1.py`
  son 3 líneas de whitelist cada uno y solo autorizan `_fila_individuo`, que
  serializa el genoma, no decide conducta.
- **Lint/tipos:** `ruff check tribal tests` → `All checks passed!`;
  `ruff format --check tribal tests` → `78 files already formatted`;
  `mypy tribal tests` → `Success: no issues found in 78 source files`.
- **Cobertura:** `tests/test_store.py --cov=tribal/store` → 98 % (solo faltan
  `cerrar()` idempotente, `_conexion()` tras cerrar y `_leer_mundo()` sin fila).
- **Secretos:** `secrets scan` → 13 hallazgos, **todos** preexistentes en
  `agents/tests/test_redaction.py` (9) y `test_secrets_agent.py` (4); ninguno en
  `tribal/` ni en los ficheros nuevos.
- **`doctor checkup`:** 7/7. **Sin dependencias:** `pyproject.toml`/`uv.lock`
  fuera del diff. Sin `.tmp-*`. `opencode.json` existe pero está trackeado sin
  cambios; `docs/`, `art/` y `auditoria-llm.md` no los reclama el informe.

## Bloqueantes

1. **`vault/01_PROYECTO/auditoria-llm.md` está sucio en el árbol (+376/−5) y
   `commit_feature` lo barrería.** No es código de F3-001 (catálogo de modelos
   §9/§10, nada que ver con persistencia) y el implementer dice con razón que no
   lo escribió él, pero `git add -A` en `agents/agents/git_agent.py:411` mete
   **todos** los cambios del árbol en el commit de F3-001. Aprobar ahora rompe
   la trazabilidad «una feature, un commit».
   **Qué haría que aprobara:** dejar el árbol con solo lo de F3-001 — revertir
   ese fichero si no es de nadie (`git restore --worktree
   vault/01_PROYECTO/auditoria-llm.md`) o commitearlo aparte en su propia
   feature. **No hay que tocar código de F3-001**; repetir el gate no es
   necesario si no cambia `tribal/` ni `tests/`.

## No bloqueante

1. `guardar()` reescribe la BD entera también al cerrar cuando el último volcado
   ya era el tick final (3 llamadas en 600 ticks). El docstring dice que el
   cierre «no duplica la fila»: es cierto para `telemetria`, pero el volcado se
   repite. Inofensivo.
2. El test de población solo compara **ids** (y que todos estén vivos). Los
   valores hacen round-trip exacto (lo comprobé campo a campo), pero corromper
   `energia`/`salud` en el guardado no rompería ningún test. Un `assert` sobre
   dos o tres campos lo blindaría, igual que se hizo con `Nodo`.
3. El COMMIT con excepción funciona (verificado a mano) pero no tiene test; hoy
   lo único que lo protege es el `try/finally` de `run`, que nadie fija.
4. `sqlite3.connect()` queda fuera del `try` de `Repositorio.__init__`: una ruta
   no abrible (un directorio, un directorio inexistente) sale con traceback y
   exit 1 en vez de `BaseInvalida`/exit 2. Los tres casos del criterio sí dan 2.
5. `review_package`: `guardar` 95 líneas y `run` 7 argumentos cruzan umbrales.
   El volcado es lineal (9 tablas), partirlo sería artificial; lo dejo anotado.
6. `ruff format --check .` a nivel repo falla en 91 ficheros de `agents/` y
   `docs/` — preexistente y fuera del diff (el implementer acotó a `tribal/
   tests`, que es lo correcto).
7. `relaciones` y `recuerdos` se crean vacías y `report telemetry --db` no lee la
   tabla. Ambos están documentados como límites deliberados (SAVE-001 y otra
   feature), no como deuda oculta.
