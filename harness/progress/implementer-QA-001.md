# implementer · QA-001

- **Fecha:** 2026-11-18
- **Veredicto:** ok

# QA-001 - implementer

## Que cambie

- `agents/agents/installer_agent.py` - `_repo_dir_name(url)` parte por `/`, `\` y `:`
  a la vez y quita el sufijo `.git`: ruta local de Windows, ruta POSIX, URL y scp
  `git@host:a/b.git`. Antes, con `rsplit('/')`, una ruta Windows devolvia la ruta
  absoluta entera, `workdir / <abs>` colapsaba al origen y `rmtree` borraba el repo
  del usuario. `_rmtree_force(path)` usa `shutil.rmtree(onexc=...)` con
  `os.chmod(stat.S_IWRITE)` y reintento: `git clone` deja `.git/objects/**` ReadOnly
  y en Windows fallaba con WinError 5 al reinstalar. Es el unico `rmtree` de
  produccion; el fixture no se toco.
- `agents/tests/test_installer_agent.py` - 3 tests nuevos: ruta local Windows,
  URL/scp (con y sin barra final y `.git`), y `_rmtree_force` sobre un arbol con
  fichero `S_IREAD`.
- `agents/tests/test_refactor_scope.py:36` - `relative_to(...).as_posix()` en vez de
  `str(...)`: el producto `_py_files` era correcto, fallaba el literal del test en
  Windows.
- `agents/tests/test_git_tag_release.py`, `test_git_commit_feature.py`,
  `test_git_commit_with_changelog.py`, `test_harness_agent.py`, `test_prompts_sync.py`
  - `encoding='utf-8'` explicito en los `read_text`/`write_text` de esos ficheros
  (los 12 sitios del informe mas los analogos que habia en los mismos ficheros).
  El producto ya escribia UTF-8; quien leia mal era el test.
- `agents/cli.py` - `_ensure_utf8_output()`: si `sys.stdout`/`sys.stderr` no son
  UTF-8, los reconfigura (`contextlib.suppress` para el caso de stream no
  reconfigurable). Se llama al principio de `main()`. En pipes y terminales ya
  UTF-8 no hace nada.
- `agents/tests/test_cli_utf8.py` - regresion: `sys.stdout` monkeypatcheado con un
  `TextIOWrapper` cp1252 sobre `BytesIO`; `main(['describe','cicd'])` debe salir 0 y
  la flecha `->` debe llegar intacta al buffer. Sin el arreglo revienta con
  UnicodeEncodeError (cp1252 no puede representar `U+2192`).
- `agents/prompts_sync.py` - `main()` llama a `_ensure_utf8_output()` (importado de
  `agents/cli.py` dentro de `main`, para que importar el modulo no arrastre el
  orquestador). `python -m agents.prompts_sync` moria al imprimir el resumen: lleva
  U+2714, U+2718 y U+2192, que cp1252 no puede representar.
- `agents/tests/test_prompts_sync.py` - regresion: `main()` con `sys.stdout` cp1252
  monkeypatcheado (y `sync`/`sync_assistants` sustituidos, sin tocar el repo real)
  devuelve 0 y escribe el resumen entero. No toca el stdout de capsys.
- `tribal/__init__.py` - `__version__ = importlib.metadata.version('tribal')` con
  fallback `0.0.0` si el paquete no esta instalado. Antes era el literal `0.1.1`
  mientras pyproject decia `0.1.4`.
- `tests/test_version.py` (nuevo, entra en la puerta) - exige
  `tribal.__version__ == importlib.metadata.version('tribal') == pyproject.toml`.
- `agents/agents/harness_agent.py` - `record` acepta `content_file` (`--content-file`),
  lo lee en UTF-8 y, si no existe, devuelve failure con la ruta en `needs`.
  `--content` sigue funcionando; si llegan los dos manda el fichero. Docstring
  actualizado.
- `agents/prompts/harness_agent.md` - tabla de acciones con `--content-file` y bloque
  autogen regenerado con `prompts_sync` (`--content_file`).
- `agents/tests/test_harness_agent.py` - test de `--content-file` con comillas
  dobles, tildes y saltos de linea (el .md resultante debe conservarlos enteros) y
  test de fichero inexistente.
- `.pre-commit-config.yaml` - `stages: [push]` -> `[pre-push]` en bandit y mypy.
  `check-yaml` sigue excluyendo `project.yml`.
- `.github/workflows/ci.yml` (nuevo) - ubuntu-latest, `actions/checkout@v7.0.1`,
  `astral-sh/setup-uv@v10.3.3` con python 3.12, `uv sync --frozen --extra dev`,
  ruff check (tribal/ tests/ agents/), ruff format --check (tribal/ tests/), mypy
  (tribal/ tests/), `uv run pytest -q` completo y `bash init.sh`. Env SDL dummy en
  video y audio + PYTHONUTF8=1, `timeout-minutes: 15`. Sin `pre-commit run
  --all-files`.

## Criterios

1. make lint -> EQUIVALENTE `uv run ruff check tribal/ tests/ agents/` (All checks
   passed) + `uv run ruff format --check tribal/ tests/` (23 files already
   formatted). `agents/` no entra en el format check, igual que en el Makefile.
2. make typecheck -> `uv run mypy tribal/ tests/` -> Success: no issues found in 23
   source files.
3. make test -> `uv run pytest -q` completo (tests/ + agents/tests) -> 546 passed,
   15 skipped.
4. CI = make check -> el workflow ejecuta los mismos cinco comandos y ademas
   `bash init.sh`. Validez del YAML: `uv run pre-commit run check-yaml
   --all-files` -> Passed (incluye el workflow nuevo). No ejecutable en local
   porque no hay runner; los comandos son los mismos que se acaban de verificar.
5. ./init.sh -> `uv run python -m agents --json run harness gate` -> success true,
   ready true, errors 0, warnings 0, pytest 26 passed (tests/).

## Evidencia

    === uv run ruff check tribal/ tests/ agents/ ===
    All checks passed!
    === uv run ruff format --check tribal/ tests/ ===
    23 files already formatted
    === uv run mypy tribal/ tests/ ===
    Success: no issues found in 23 source files

    === uv run pytest -q ===
    ........................................................................ [ 12%]
    ........................................................................ [ 25%]
    ........................................................................ [ 38%]
    ........................................................................ [ 51%]
    ........................................................................ [ 64%]
    ..............................................................s.ssssssss [ 77%]
    ssss..s................................................................. [ 90%]
    ........................................................                 [100%]
    546 passed, 15 skipped in 61.32s (0:01:01)

    === uv run python -m agents --json run harness gate (exit 0) ===
    success = True
    ready   = True | errors = 0 | warnings = 0
    - ok | python | ./.venv/Scripts/python.exe 3.12
    - ok | uv | uv 0.10.7 (08ab1a344 2026-02-27)
    - ok | venv | .venv presente
    - ok | AGENTS.md | presente
    - ok | featureslist.json | presente
    - ok | current.md | presente
    - ok | history.md | presente
    - ok | subagentes | lider, implementer, reviewer, explorer
    - ok | featureslist | 4 features - 0 pending - 1 in_progress - 3 done - 0 blocked
    - ok | siguiente tarea | QA-001 - Bateria de calidad en verde [in_progress]
    - ok | paquete | tribal/ presente (project.yml)
    - ok | pyproject | presente
    - ok | tests | 7 ficheros de test
    - ok | pytest | 26 passed in 2.84s

    === version ===
    tribal.__version__ 0.1.4 | metadata 0.1.4

    === uv lock --check / uv lock ===
    Resolved 141 packages in 1ms          (exit 0, no reescribe nada: el lock ya es 0.1.4)

    === uv run pre-commit run check-yaml --all-files ===
    check yaml...............................................................Passed

    === uv run python -m agents describe cicd (consola cp1252 real) ===
    ... JSON completo, exit 0. Antes moria con UnicodeEncodeError en el caracter
    U+2192 de la primera seccion del contrato.

    === uv run python -m agents.prompts_sync (consola cp1252) ===
    [U+2714] Prompts y subagentes sincronizados con el codigo y con los contratos.
    exit 0  (antes: UnicodeEncodeError en agents/prompts_sync.py:242)

    === uv run python -m agents.prompts_sync --write ===
    [U+2714] Todo estaba ya al dia.
    exit 0  (harness_agent.md ya sincronizado; --write no cambia ningun prompt)

    === uv run pytest -q (tras el cambio) ===
    547 passed, 15 skipped in 58.84s (0:01:01)

    === uv run python -m agents --json run harness gate (exit 0) ===
    success = True | ready = True | errors = 0 | warnings = 0
    - ok | pytest | 26 passed in 1.60s

## Que falta

- `.tmp_backlog.py` esta sin trackear y no es mio: no lo borro.
- El badge del README y el bump de version son del cierre (`git commit_feature`).
- El diff de `uv.lock` (0.1.3 -> 0.1.4) es previo a esta feature; `uv lock` lo deja
  coherente y no introduce mas cambios.

## Desbloqueo del commit (pre-commit)

- `.github/workflows/ci.yml` - el `name` del paso de pytest llevaba dos `:` dentro
  de un escalar plano y `check-yaml` fallaba. Ahora es
  `pytest - suite completa (tests y agents/tests)`. Parsea con PyYAML (1 job,
  8 pasos) y `check-yaml` Passed.
- `.pre-commit-config.yaml` - `ruff-format` con `files: ^(tribal|tests)/`, la misma
  politica que `make format`/`make lint`; el hook reformateaba 11 ficheros de
  `agents/` en cada commit. `ruff` (check) sigue cubriendo `agents/` y pasa limpio.
  Comprobado: `pre-commit run ruff-format --files agents/cli.py` responde
  (no files to check) Skipped.
- `CHANGELOG.md` - de 5 secciones `[Unreleased]` (DESIGN-001 duplicado) a 1 sola,
  con las cuatro entradas de la sesion en orden cronologico (SCOPE-001,
  DESIGN-001, CORE-001, QA-001) y la entrada previa del esqueleto del arnes
  conservada.
- `uv.lock` - `uv lock`: tribal 0.1.4 -> 0.1.5 (pyproject ya estaba en 0.1.5, no se
  toco ninguna version). `uv lock --check` exit 0. `uv run` re-sincronizo el
  editable: metadata 0.1.5, asi que `tests/test_version.py` sigue en verde.
- `harness/progress/explorer-QA-001.md` - `trailing-whitespace` recorto espacios
  sobrantes; lo hizo el hook, no a mano.
- Hecho con `git add` de esos ficheros para que el indice y el arbol coincidan; no
  se ha commiteado nada.

## Evidencia del desbloqueo

    === pre-commit run ruff --files (.py tocados) ===
    ruff.....................................................................Passed

    === pre-commit run ruff-format --files (mismos .py) ===
    ruff-format..............................................................Passed

    === pre-commit run ruff-format --files agents/cli.py (prueba de alcance) ===
    ruff-format..........................................(no files to check)Skipped

    === pre-commit run trailing-whitespace --files (tocados), 1a pasada ===
    trim trailing whitespace.................................................Failed
    - files were modified by this hook
    Fixing harness/progress/explorer-QA-001.md

    === pre-commit run trailing-whitespace --files (tocados), 2a pasada ===
    trim trailing whitespace.................................................Passed

    === end-of-file-fixer / check-toml / check-merge-conflict (tocados) ===
    Passed / Passed / Passed

    === pre-commit run check-yaml --all-files ===
    check yaml...............................................................Passed

    === PyYAML sobre .github/workflows/ci.yml ===
    job: ['gate'] | pasos: 8

    === uv lock --check ===
    Resolved 141 packages in 1ms   (exit 0, lock 0.1.5)

    === uv run pytest -q ===
    547 passed, 15 skipped in 59.61s (0:01:01)

    === uv run python -m agents --json run harness gate (exit 0) ===
    success = True | ready = True | errors = 0 | warnings = 0
    - ok | pytest | 26 passed in 4.50s
