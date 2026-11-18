# reviewer · QA-001

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

# reviewer · QA-001

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

Todo ejecutado en esta sesión, shell limpia (PYTHONUTF8 / PYTHONIOENCODING unset,
stdout cp1252), no leído del informe del implementer.

## Criterios

1. **make lint — CUMPLIDO.** `make` no existe en esta máquina Windows, así que se
   ejecutaron los comandos exactos del target `Makefile:123-125`:
   `uv run ruff check tribal/ tests/ agents/` -> `All checks passed!` (exit 0)
   `uv run ruff format --check tribal/ tests/` -> `23 files already formatted` (exit 0)

2. **make typecheck — CUMPLIDO.** `uv run mypy tribal/ tests/` ->
   `Success: no issues found in 23 source files` (exit 0).

3. **make test — CUMPLIDO.** `make test` = `uv run pytest` (Makefile:117). Ejecutado
   tal cual, sin variables de entorno especiales y con consola cp1252 de verdad
   (`sys.stdout.encoding == cp1252`, `locale.getpreferredencoding() == cp1252`):

       547 passed, 15 skipped in 58.50s        PYTEST_EXIT=0

   Incluye tests/ (26, contando el nuevo tests/test_version.py) y agents/tests.
   Los 15 skips son preexistentes (`test_rag_agent.py:27` skipif de chroma).

4. **CI = make check — CUMPLIDO.** `.github/workflows/ci.yml` ejecuta ruff check
   (tribal/ tests/ agents/), ruff format --check (tribal/ tests/), mypy
   (tribal/ tests/) y `uv run pytest -q`, igual que `make check: lint typecheck
   test harness-check`, y ademas `bash init.sh` completo (superset de
   `harness-check`, que usa `./init.sh --quick`). No hay `pre-commit run
   --all-files`. `uv run pre-commit run check-yaml --all-files` -> Passed (el
   workflow nuevo parsea). Tags de las actions verificados contra la API de
   GitHub: actions/checkout v7.0.1 y astral-sh/setup-uv v10.3.3 existen y son las
   releases actuales. `uv sync --frozen` es viable hoy: `uv lock --check` exit 0.
   `[project.optional-dependencies].dev` existe, así que `--extra dev` resuelve.
   `timeout-minutes: 15` y SDL dummy presentes.

5. **./init.sh — CUMPLIDO.** `uv run python -m agents --json run harness gate` ->
   `success: true`, `ready: true`, `errors: 0`, `warnings: 0`, `pytest 26 passed`,
   mensaje `ENTORNO LISTO — se puede trabajar.`

## Comprobaciones extra

- **PRODUCTO installer — correcto y arreglado en el producto.** `_repo_dir_name`
  parte por `[/\\:]` y quita `.git`: `C:\Users\pedro\workspace\repo_externo` ->
  `repo_externo`, `https://github.com/torvalds/linux(.git|/)` -> `linux`,
  `git@github.com:torvalds/linux.git` -> `linux`. `clone_dir = workdir / nombre`
  deja de colapsar a la ruta absoluta. `_rmtree_force` usa
  `shutil.rmtree(onexc=...)` + `os.chmod(target, stat.S_IWRITE)`: reproducido en
  temp que `shutil.rmtree` plano da `PermissionError: [WinError 5]` sobre
  `.git/objects/pack` y el helper lo borra. Es el unico `rmtree` de produccion
  (grep `rmtree` en agents/agents -> solo installer_agent). `onexc` exige 3.12 y
  `requires-python = ">= 3.12"`. El fixture no se toco: `test_installer_agent.py`
  solo tiene anadidos al final. Los tests nuevos fallarian con el codigo viejo
  (importan `_repo_dir_name` / `_rmtree_force`, inexistentes antes), y el
  comportamiento end-to-end lo cubren los 6 tests de installer que estaban en
  rojo por este bug.

- **TESTS sin debilitar.** `git diff` no anade ni un `skip`, `skipif` ni `xfail`.
  Las 7 lineas `assert` eliminadas estan re-anadidas identicas con
  `encoding='utf-8'`; `test_refactor_scope.py` solo cambia `str(...)` por
  `.as_posix()`, mismos asserts. `review review_package` -> 16 ficheros, 0
  hallazgos, 0 duplicacion.

- **CLI UTF-8 en consola real cp1252** (sin PYTHONUTF8): `python -m agents
  describe cicd` exit 0; `python -m agents.prompts_sync` exit 0; `--write` exit 0
  (`Todo estaba ya al dia`). Confirmado que escribir U+2192 en un
  `TextIOWrapper(cp1252)` revienta con UnicodeEncodeError, que es el test de
  regresion `test_cli_utf8.py`.

- **VERSION.** `import tribal; print(tribal.__version__)` -> `0.1.4` ==
  `pyproject.toml:3` == metadatos. `tests/test_version.py` exige las tres
  igualdades y entra en la puerta (26 passed).

- **harness --content-file.** Registrado un informe de prueba (id QATMP) con
  comillas dobles, tildes, `->`, `check`, pipes, `<tag>`, `&`, backtick, linea en
  blanco y bloque indentado: el .md guardado conserva el contenido byte a byte
  salvo CRLF de plataforma (`.gitattributes: * text=auto eol=lf` normaliza).
  Fichero inexistente -> `success: false` con la ruta en `needs`. Documentado en
  `agents/prompts/harness_agent.md` (tabla + bloque autogen) y `prompts_sync` en
  sincronia (exit 0). El informe de prueba se borro despues.

- **PRE-COMMIT.** bandit y mypy con `stages: [pre-push]`; `check-yaml` sigue con
  `exclude: ^project\.yml$`; `check-yaml --all-files` -> Passed.

- **ALCANCE limpio.** Solo los ficheros anunciados. `tribal/core`, `tribal/agents`
  y `tribal/sim.py` intactos. El diff de `harness/featureslist.json` es solo el
  `start` del arnés (pending -> in_progress, started, review_rounds), no una
  edicion a mano. Sin `.tmp-*` del implementer (solo `.tmp_backlog.py`, previo).
  `uv.lock` solo cambia `tribal 0.1.3 -> 0.1.4`, coherencia que faltaba de antes.

## Bloqueantes

_(ninguno)_

## No bloqueante

1. **Trampa de release:** `git commit_feature` / `documentation_agent.bump_version`
   NO ejecutan `uv lock`. Verificado en copia: subir pyproject a 0.1.5 con el
   `uv.lock` actual da `uv lock --check` exit 1 (`The lockfile needs to be
   updated`). Con `uv sync --frozen` en el CI, el primer push tras cerrar QA-001
   saldra en rojo si el cierre no re-lockea. Accion: el lider ejecuta
   `uv lock` antes del commit del bump (o se abre ticket para que commit_feature
   lo haga). No es criterio de esta feature, pero es el siguiente que se rompe.
2. Informe del implementer desactualizado en dos puntos: dice 546 passed (hoy
   547) y que `prompts_sync --write` sigue reventando con `check` (esta arreglado:
   exit 0). El codigo es el bueno; el texto no.
3. `_repo_dir_name` se prueba a nivel unitario; el end-to-end va por los tests de
   installer existentes. Aceptable, pero un test de `install_from_git` con ruta
   con separadores de Windows dejaria el bug clavado.
4. `harness start` reescribio la cabecera descriptiva de
   `harness/progress/current.md` (template del arnés, no de este cambio).
5. Preexistente y fuera de alcance: `refactor_agent._py_files` devuelve el campo
   `file` con el separador del SO, y `secrets scan` marca 13 fixtures en
   `agents/tests/test_redaction.py` / `test_secretos` (falsos positivos de test).

## Evidencia cruda

    uv run ruff check tribal/ tests/ agents/      -> All checks passed!
    uv run ruff format --check tribal/ tests/     -> 23 files already formatted
    uv run mypy tribal/ tests/                    -> Success: no issues found in 23 source files
    uv run pytest -q                              -> 547 passed, 15 skipped in 58.50s (exit 0)
    uv run pre-commit run check-yaml --all-files  -> Passed (exit 0)
    uv lock --check                               -> Resolved 141 packages (exit 0)
    uv run python -m agents --json run harness gate -> success true, ready true, errors 0, warnings 0
