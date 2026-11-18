# implementer · FIX-005

- **Fecha:** 2026-11-18
- **Veredicto:** ok

## Qué cambié

- `agents/agents/git_agent.py` — `commit_feature`: snapshot de `pyproject.toml`/`README.md`/`CHANGELOG.md`/`uv.lock` antes de escribir; `uv lock` + `uv lock --check` antes de commitear (success=false con `needs` y rollback si no cuadra); en fallo de `git commit` restaura el contenido previo (no el HEAD), saca esos ficheros del índice y devuelve `needs` con la causa; `_next_patch_version` calcula desde `git show HEAD:pyproject.toml` (fallback al worktree).
- `agents/agents/documentation_agent.py` — `_insert_feature_entry`: idempotente por `feature_id` (si ya está, no escribe) y reutiliza la sección `[Unreleased] — <hoy>` existente en vez de abrir otra.
- `agents/tools/git_tool.py` — `show_file`, `restore_staged`, `indexed_files`.
- `agents/tests/test_commit_feature_idempotente.py` — 4 tests nuevos (dos fallos + éxito, lock que no cuadra, dry-run md5, dedup del documentation agent).
- `agents/prompts/git_agent.md` + `agents/README.md` — documentado el cierre idempotente y el lock.

## Criterios de aceptación

1. Si `git commit` falla, no queda sección nueva ni bump a medias → `test_commit_feature_no_duplica_tras_dos_fallos_y_cierra_al_tercero` + prueba real con hook (abajo).
2. `uv lock` antes de commitear y `success=false` con `needs` si no cuadra → `_sync_lock` en `git_agent.py` + `test_commit_feature_devuelve_needs_si_el_lock_no_cuadra`.
3. Dos fallos → N secciones, no N+2; éxito → exactamente una → mismo test.
4. `--dry-run true` no escribe nada (md5 idéntico) → `test_commit_feature_dry_run_no_escribe_nada` + CLI real sobre este repo (abajo).
5. `uv run pytest -q` verde y `harness gate` success=true → salidas abajo.

## Evidencia

Prueba real en copia temporal del repo (hook `pre-commit` con `exit 1`, CLI `python -m agents run git commit_feature`, `HARNESS_ASSUME_YES=1`):

```
run1: success=False needs=Corrige lo que tumbó 'git commit' (hook: tests rojos) y reintenta el cierre de FIX-005. msg='git commit' falló y se revirtió el bump: hook: tests rojos
  pyproject: version = "0.1.5"
  CHANGELOG existe: True
  status: A  nota_feature.txt
  commits: 1
run2: success=False needs=Corrige lo que tumbó 'git commit' (hook: tests rojos) y reintenta el cierre de FIX-005. msg='git commit' falló y se revirtió el bump: hook: tests rojos
  pyproject: version = "0.1.5"
  CHANGELOG existe: True
  status: A  nota_feature.txt
  commits: 1
(quitar hook)
run3: success=true, message="FIX-005 cerrada con commit 'feat(FIX-005): Cierre idempotente' (versión 0.1.6, CHANGELOG.md actualizado)."
pyproject: version = "0.1.6"
secciones [Unreleased] en TODO el CHANGELOG: 1
entradas FIX-005: 1
uv lock --check exit: 0
commits: 2 | status: ''
 CHANGELOG.md     | 1 +
 README.md        | 2 +-
 nota_feature.txt | 1 +
 pyproject.toml   | 2 +-
 uv.lock          | 2 +-
```

Dos fallos: versión intacta en 0.1.5, CHANGELOG sin tocar, sólo la feature sin commitear en stage. Tercero: 0.1.6 (un solo patch), una sección, una entrada, lock sincronizado y commiteado, árbol limpio.

Dry-run sobre este repo (md5 antes/después de la CLI real):

```
SAME pyproject.toml
SAME README.md
SAME CHANGELOG.md
SAME uv.lock
```

Tests:

```
$ uv run pytest agents/tests -q
525 passed, 15 skipped in 61.18s (0:01:01)

$ uv run pytest -q
551 passed, 15 skipped in 63.20s (0:01:03)

$ uv run ruff check tribal/ tests/ agents/
All checks passed!
$ uv run ruff format --check tribal/ tests/
23 files already formatted
$ uv run mypy tribal/ tests/
Success: no issues found in 23 source files

$ uv run python -m agents.prompts_sync
✔ Prompts y subagentes sincronizados con el código y con los contratos.   (exit 0)

$ uv run python -m agents --json run harness gate
"success": true, "message": "ENTORNO LISTO — se puede trabajar."

$ bash ./init.sh
✔ pytest 26 passed in 4.54s
━━ ENTORNO LISTO ━━ 0 aviso(s)
```

Nota: `ruff format --check agents/` no está limpio, pero ya lo estaba mal en HEAD (`git show HEAD:agents/agents/git_agent.py` → "1 file would be reformatted"); el Makefile sólo comprueba formato de `tribal/` y `tests/`. El fichero nuevo de test sí está formateado.

## Qué falta

- `tag_release` sigue encadenando `bump_version` sin `uv lock`: mismo fallo de lock, pero fuera del alcance de FIX-005 (anotado, no tocado).
- No he ejecutado un cierre real sobre el repo (prohibido commitear aquí): la prueba end-to-end es en copia temporal.
