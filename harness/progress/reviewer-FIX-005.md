# reviewer · FIX-005

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

# reviewer · FIX-005

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado
- **Puerta:** `uv run python -m agents --json run harness gate` → `"success": true, "message": "ENTORNO LISTO — se puede trabajar."` (0 errores, 0 avisos, 14 checks ok)

Todo lo de abajo se ha **reejecutado**: tests en el repo, CLI real en el repo para
dry-run (md5 antes/después) y el resto en una copia completa del repo
(`%TEMP%\opencode\fix005-copy`, con .git e index reales) para no dejar el árbol sucio.
HEAD del repo real sigue en `63aa68e`; no se ha creado ningún commit.

## Criterios

1. **Commit fallido no deja sección nueva ni bump a medias; el reintento no duplica — CUMPLIDO.**
   Test `test_commit_feature_no_duplica_tras_dos_fallos_y_cierra_al_tercero` (verde).
   En copia, con el CHANGELOG **real** (que ya tenía contenido, caso que el test no
   cubre porque allí no existe CHANGELOG): dos `commit_feature` con hook `pre-commit`
   `exit 1` → `pyproject.toml` md5 `C886F1F9…` idéntico, `CHANGELOG.md` md5 `CA61038F…`
   idéntico al de partida, `version = "0.1.5"` intacta, `0` entradas `(FIX-005)`,
   `0` secciones nuevas, sin commit (`git log` sigue en `63aa68e`).

2. **`uv lock` + `uv lock --check` antes de commitear; `success=false` con `needs` si no cuadra — CUMPLIDO.**
   `git_agent.py:398-407` está entre `update_changelog` y `git add -A`/`commit`.
   Sonda con espías sobre `run_command`/`GitTool.commit` en copia:
   `RUN uv lock | pyproject=version = "0.1.1"` → `RUN uv lock --check | pyproject=0.1.1`
   → `COMMIT | pyproject=0.1.1` (prueba de que corre **después del bump** y antes del commit).
   Fallo de lock: test `test_commit_feature_devuelve_needs_si_el_lock_no_cuadra` (verde).
   Caso `--check` en rojo (que el test no toca) verificado a mano forzando
   `run_command(["uv","lock","--check"])` a `returncode=1`: `success=false`,
   `needs=["Corrige el lock ('uv lock') …"]`, `pyproject` byte a byte intacto,
   CHANGELOG inexistente.

3. **Dos fallos → N secciones, no N+2; con éxito exactamente una — CUMPLIDO.**
   Test: tras cada fallo `CHANGELOG.md` no existe (N=0) y `version = "0.1.0"`; tras el
   éxito `changelog.count("(FIX-005)") == 1` y `count("## [Unreleased]") == 1`.
   En copia con CHANGELOG real: 1 sección antes → 1 tras dos fallos → 1 tras el éxito;
   entradas `(FIX-005)`: 0 → 0 → 1.

4. **`--dry-run true` no escribe nada — CUMPLIDO.**
   Test `test_commit_feature_dry_run_no_escribe_nada` (verde) y CLI real **en este repo**:
   md5 de `pyproject.toml` `C886F1F9…`, `README.md` `48D5B4F0…`, `CHANGELOG.md`
   `CA61038F…`, `uv.lock` `9ACBD2C5…` idénticos antes y después; `git status --short`
   idéntico; sin commit. Propuesta: bump a `0.1.6`, misma versión que el cierre real de la copia.

5. **`uv run pytest -q` verde y gate success=true — CUMPLIDO.**
   `551 passed, 15 skipped in 62.16s`; gate `success=true` (línea arriba).
   Extra: `ruff check agents/` → *All checks passed*; test nuevo ya formateado;
   `python -m agents.prompts_sync` → exit 0; `review review_package` → 0 hallazgos;
   `doctor checkup` → 7/7.

## Rollback en copia (lo que más importaba)

Escenario: añadido `nota_feature.py` sin trackear + `agents/README.md` modificado
(trackeado, ajeno al cierre), hook `pre-commit` `exit 1`, CLI real
(`HARNESS_ASSUME_YES=1 python -m agents run git commit_feature`).

| Tras 1er fallo | Resultado |
|---|---|
| `pyproject.toml` / `README.md` / `CHANGELOG.md` / `uv.lock` | md5 idénticos a antes de la llamada |
| `nota_feature.py` | presente, intacto |
| `agents/README.md` (fichero tocado por la feature) | md5 `82C40F5F…` idéntico, trabajo conservado |
| `git status --short` de los 4 ficheros del cierre | vacío (fuera del índice, contenido restaurado) |
| resto del árbol | sigue staged tal cual (`agents/*`, `harness/*`, `nota_feature.py`), sin alterar |
| commit | no creado |
| `needs` | `"Corrige lo que tumbó 'git commit' (hook: tests rojos) y reintenta el cierre de FIX-005."` |

Segundo fallo: mismos md5, `version = "0.1.5"`, 0 entradas. Tercer intento sin hook:
`success=true`, `versión 0.1.6` (un solo patch), 1 sección, 1 entrada, `uv lock --check`
exit 0, árbol limpio.

**Camino feliz commitea TODO lo de la feature:** `git show --stat HEAD` incluye
`nota_feature.py`, `CHANGELOG.md`, `README.md`, `pyproject.toml`, `uv.lock` y los 10
ficheros de la feature (15 ficheros, 827 inserciones). `git add -A` sigue ahí, no se
acotó a los 4 del cierre.

## `_next_patch_version` desde HEAD

- HEAD normal → `HEAD:pyproject.toml`; dry-run y ejecución real dan **el mismo** `next_version`
  (0.1.6 en el repo real, 0.1.6 en el cierre de la copia).
- **Sin HEAD** (repo recién inicializado, sin commits): `git show` falla → `None` → fallback
  al worktree. Probado: dry `0.1.1`, real `0.1.1`, commit inicial creado, `needs=[]`.
  Consistente.
- **pyproject de HEAD sin `version`** (`dynamic = ["version"]`): devuelve `None`; dry-run
  avisa "se omite el bump" y real hace lo mismo (commitea solo la entrada del CHANGELOG,
  `success=true`, `pyproject` sin tocar). Coherente entre los dos caminos.

## Tests nuevos contra el código viejo

En copia, `git checkout 63aa68e -- agents/agents/git_agent.py agents/agents/documentation_agent.py
agents/tools/git_tool.py` y el test nuevo tal cual:

```
FAILED test_commit_feature_no_duplica_tras_dos_fallos_y_cierra_al_tercero   (needs == [])
FAILED test_commit_feature_devuelve_needs_si_el_lock_no_cuadra              (commitea igual)
FAILED test_update_changelog_es_idempotente_por_feature                     (2 entradas FIX-005)
3 failed, 1 passed in 2.07s
```

El de dry-run pasa también con el código viejo (antes tampoco escribía), como era de esperar.
Los tres restantes fallan por el motivo correcto, no por un import roto.

## Alcance

- `tribal/` **no** se toca (`git diff --numstat`: solo `agents/*` + `harness/*`).
- `git_tool.py`: `show_file`, `restore_staged`, `indexed_files` nuevos; cobertura
  verificada con `--cov` sobre los tests de la feature (sin líneas huérfanas en 107-121).
- `prompts_sync` exit 0; `agents/README.md` y `agents/prompts/git_agent.md` describen
  exactamente lo que hace el código (lock, rollback al contenido previo, versión desde HEAD).
- `git status --short` en el repo real: los ficheros de la feature + `reviewer-FIX-005.md`
  (este informe). HEAD en `63aa68e`.

## Bloqueantes

_(ninguno)_

## No bloqueante

1. **Cerrar dos veces con éxito no es idempotente del todo.** En copia, segundo cierre del
   mismo `FIX-005` ya commiteado: no duplica entrada ni sección (correcto), pero sube
   `0.1.6 → 0.1.7` y crea un segundo commit `feat(FIX-005): …` que solo toca
   `pyproject/uv.lock`. Si un cierre llegó a commitear y se perdió la respuesta, el
   reintento deja un commit espurio. Los AC no lo piden; merece feature aparte
   (p. ej. no cerrar si el último commit ya es `feat(<id>)`).
2. **`_next_patch_version` puede degradar una versión.** Con HEAD en `0.1.0` y el worktree
   ya en `0.2.0` sin commitear, el cierre escribe `0.1.1` (verificado). Es el precio de leer
   HEAD; conviene dejarlo escrito en el prompt porque un bump manual previo se pierde.
3. **La rama `uv lock --check` en rojo (git_agent.py:505) no tiene test.** El test fuerza el
   fallo en `uv lock` (pyproject inválido), no en `--check`. Lo he verificado a mano; añadir
   el caso con `run_command` parcheado es barato.
4. **El fallback sin HEAD de `_next_patch_version` (454-456) tampoco tiene test**, solo
   verificación manual (arriba).
5. **Rollback en repo sin HEAD:** los ficheros se restauran en disco, pero
   `git restore --staged` falla sin HEAD y el código ignora el resultado → los 4 quedan en
   el índice (`AD CHANGELOG.md`, `AM pyproject.toml`…). No se pierde trabajo ni queda bump
   en el worktree, pero el índice no queda limpio en ese caso límite (primer commit de un
   repo, con hook que falla). Arreglo: comprobar `git rev-parse --verify HEAD` antes del
   restore, o `git rm --cached` para las rutas que no existen en HEAD.
6. **`restore_staged`/`indexed_files` ignoran el `ProcessResult`:** un fallo del restore solo
   se detecta mirando `git status`. Devolver el fallo en `warnings` lo haría visible.
7. **`staged_paths` es un nombre engañoso** (son las 4 rutas del cierre, no lo que está staged).
8. **`harness/featureslist.json` trae +386 líneas / 23 features de backlog** (FIX-002,
   HARD-0…3, F1/F2/F3) además de FIX-005. Todo aditivo y con schema válido, pero no es
   trabajo del implementer (no lo menciona) sino expansión del backlog del líder:
   confirmar que es intencional antes de commitear.
9. Pre-existente: `BaseAgent.run()` crea `agents/workspace/audit/audit.jsonl`; en el repo
   real está ignorado (el commit de la copia no lo arrastró), pero en un proyecto sin
   `.gitignore` `git add -A` lo metería en el commit.
