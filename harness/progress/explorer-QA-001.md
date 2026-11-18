# explorer · QA-001

- **Fecha:** 2026-11-18
- **Veredicto:** ok

# explorer Â· QA-001

- **Fecha:** 2026-11-18
- **Veredicto:** ok

# QA-001 diagnostico (explorer, solo lectura, 2026-11-18)

## Respuesta

`uv run pytest -q` NO deja 7 fallos: deja 16 (523 passed, 15 skipped, ~56 s). Los 7
del informe son solo test_installer_agent.py (6) + test_refactor_scope.py (1) lanzados
sueltos; el resto de agents/tests aporta 9 fallos mas que aparecen en la suite completa.

Causas raiz, en orden de gravedad:

1. installer (6 fallos, misma causa, DOS capas, ambas en codigo de producto)
   - Capa A, bug real: agents/agents/installer_agent.py:111-115 calcula
     `repo_dir_name = resolved_url.rstrip('/').rsplit('/', 1)[-1]` Ã¢â‚¬â€ solo parte por `/`.
     Con una ruta local de Windows (`C:\...\repo_externo`) devuelve la ruta ABSOLUTA
     entera y `workdir / repo_dir_name` colapsa al origen: `clone_dir` == el repo que el
     usuario queria instalar. Verificado: `Path(r'C:\proj\agents\workspace\installer') /
     r'C:\tmp\x\repo_externo'` -> `C:\tmp\x\repo_externo`. El `shutil.rmtree(clone_dir)`
     de la linea 115 borra el repo ORIGEN (y el traceback del test lo confirma: el path
     del rmtree es `.../pytest-xxx/repo_externo`, no `.../agents/workspace/installer/...`).
   - Capa B, tambien produccion: aunque el path fuera correcto, `shutil.rmtree` de un
     `git clone` recien hecho falla en Windows con WinError 5 porque git marca
     `.git/objects/**` como ReadOnly. Verificado en temp: atributos ReadOnly, rmtree
     directo -> PermissionError; rmtree con `onexc` que hace chmod(S_IWRITE) y reintenta
     -> OK. Es decir `install_from_git` no puede reinstalar sobre un clone previo en Windows.
   - Arreglo correcto: en el agente (no en el fixture)
     a) `repo_dir_name = Path(resolved_url).name.removesuffix('.git')` Ã¢â‚¬â€ funciona con
        `/`, `\`, URLs y `git@host:a/b.git` (verificado con PureWindowsPath/PurePosixPath).
     b) helper de borrado tolerante (`onexc`/`onerror` con `os.chmod(path, stat.S_IWRITE)`;
        no existe ninguno hoy; installer_agent.py:115 es el unico rmtree de produccion).
     Justificacion: el fixture es honesto (repo git local real, como el del usuario); el
     fallo esta en el codigo. Parchear solo el fixture deja roto `installer install_from_git`
     con ruta local en Windows (borra el repo del usuario) y en cualquier reinstalacion.
   - En Linux es peor de lo que parece: `PurePosixPath('/proj/.../installer') /
     '/tmp/x/repo_externo'` tambien colapsa a `/tmp/x/repo_externo`, alli el rmtree NO
     falla (no hay ReadOnly) y borra el origen en silencio; luego el clone falla y los
     mismos 6 tests caen. O sea: el CI ubuntu con pytest completo tambien esta rojo.

2. refactor (1 fallo): agents/tests/test_refactor_scope.py:36 y :38 comparan
   `str(p.relative_to(root))` contra el literal `mi_paquete/propio.py`. `_py_files`
   (agents/agents/refactor_agent.py:49-64) es correcto; el fallo es del TEST (en Linux
   `str(Path)` da `/` y pasa, en Windows da `\`). Arreglo: `.as_posix()` en la linea 36.
   Nota (no bloquea): refactor_agent.py:69 devuelve `str(path.relative_to(root))` como
   campo `file` de los resultados -> separador del SO en salida parseable; hoy ningun
   test lo compara.

3. Los otros 4 fallos de installer: misma causa exacta (los 6 tracebacks acaban en
   installer_agent.py:115). No hay una segunda causa en ese fichero.

4. Los 9 fallos extra (no estaban en el informe) son encoding de TESTS, no del producto:
   - agents/tests/test_git_tag_release.py:10-12 y test_git_commit_feature.py:9-12 escriben
     README con `write_text()` sin encoding (cp1252 en Windows: 0xf3) y
     agents/agents/documentation_agent.py:205 lo lee con `encoding='utf-8'` estricto ->
     UnicodeDecodeError. Idem latente en test_git_commit_with_changelog.py:9.
   - agents/tests/test_harness_agent.py:259 `read_text()` sin encoding -> mojibake `Ãƒâ€šÃ‚Â·` y
     falla el assert de la 260.
   - agents/tests/test_prompts_sync.py:84, :94, :154 `read_text()` sin encoding.
   Arreglo: `encoding='utf-8'` en esos ~12 call sites. El producto ya escribe siempre
   utf-8 (verify: harness_agent.py:200, plan_agent.py:86, knowledge_agent.py:268 pasan
   encoding en la linea siguiente). Hay ~150 call sites sin encoding en agents/tests:
   latentes en Windows, invisibles en CI Linux. Por eso hay que arreglarlos, no confiar
   en que el CI los pille.

## Que impide make check verde

- `uv run ruff check tribal/ tests/ agents/` -> limpio (All checks passed).
- `uv run ruff format --check tribal/ tests/` -> limpio (22 files already formatted).
  `agents/` -> 88 ficheros se reformatearian: NO meterlo en el check (make lint
  tampoco lo hace; solo `ruff check` incluye agents/).
- `uv run mypy tribal/ tests/` -> limpio (22 source files).
- `uv run python -m agents --json run harness gate` -> ready true, errors 0, pytest
  25 passed (solo tests/). La puerta es verde porque init.sh:274 corre `pytest tests/`.
- `uv run pytest` (lo que hace `make test` / target test del Makefile, linea 117) ->
  16 fallos. Ese es el unico bloqueo de `make check`.
- Versiones: tribal/__init__.py:14 = 0.1.1 ; pyproject.toml:3 = 0.1.4 ;
  README.md:4 (badge) = 0.1.4 ; uv.lock:2885 = 0.1.4. Origen de la deriva:
  documentation_agent.bump_version (174-225) solo reescribe pyproject y el badge /
  linea `**Version:**` del README, nunca tribal/__init__.py; ademas el README ya no
  tiene linea `**Version:**` (solo badge), asi que avisa cada vez. Arreglo de raiz:
  `__version__ = importlib.metadata.version('tribal')` con fallback a '0.0.0' si el
  paquete no esta instalado + test de coherencia (metadata == badge README).
  Alternativa pobre: que bump_version tambien toque tribal/__init__.py (sigue habiendo
  tres fuentes de verdad).
- Trampa de CI verificada: `uv sync --frozen` revienta en cuanto commit_feature sube
  pyproject sin re-lockear. Probado en copia temp (0.1.4 -> 0.1.5, uv.lock intacto):
  `uv lock --check` -> exit 1, el lockfile necesita actualizarse. commit_feature debe
  ejecutar `uv lock`, o el step de sync falla justo despues de cerrar una feature.
- .pre-commit-config.yaml: `stages: [push]` en bandit y mypy es alias legacy;
  pre-commit 4.6.1 lo mapea a pre-push (clientlib.py:67) y emite
  'uses deprecated stage names' (clientlib.py:103/155). Valor correcto: `[pre-push]`.
  Aviso adicional: el hook ruff-format no filtra ficheros, asi que al commitear un
  fichero de agents/ lo reformatea (88 pendientes).

## CI

No existe `.github/` (Test-Path .github -> False). `init.sh` esta en modo 100644 en git
-> el step debe ser `bash init.sh`, no `./init.sh`.

Workflow minimo (.github/workflows/ci.yml), ubuntu-latest, un solo job:

    name: CI
    on:
      push: { branches: [main] }
      pull_request: { branches: [main] }
    jobs:
      gate:
        runs-on: ubuntu-latest
        timeout-minutes: 15
        env:
          SDL_VIDEODRIVER: dummy
          SDL_AUDIODRIVER: dummy
          PYTHONUTF8: '1'
        steps:
          - uses: actions/checkout@v7            # v4 sigue funcionando; v7.0.1 es la actual
          - uses: astral-sh/setup-uv@v10.3.3     # desde v8 solo hay tags inmutables vX.Y.Z
            with:
              enable-cache: true
              python-version: '3.12'             # igual que .python-version
          - run: uv sync --frozen --extra dev
          - run: uv run ruff check tribal/ tests/ agents/
          - run: uv run ruff format --check tribal/ tests/
          - run: uv run mypy tribal/ tests/
          - run: uv run pytest -q                 # SUITE COMPLETA (incluye agents/tests)
          - run: bash init.sh                     # la puerta local, tal cual

Notas:
- SDL dummy: tests/test_render.py ya hace monkeypatch de SDL_VIDEODRIVER, pero fijarlo a
  nivel de job protege del import de pygame. PYTHONUTF8=1 es redundante en ubuntu (locale
  UTF-8) y no tapa los fallos cp1252, que son solo de Windows local.
- agents/tests no necesita nada extra: usa git+config local, que el runner ya tiene.
  Nada de docker ni red. Duracion ~56 s de tests + ~10 s de la puerta.
- NO copiar de agents/tools/cicd_tool.py:38-72 (cicd_tool.py:33): pin `setup-uv@v8.1.0`
  (obsoleto, y el floating @v7 ya no sigue releases), `uv sync --extra dev` sin
  --frozen/--locked, sin python-version, y solo `make lint` + `make test` (sin format
  check, sin mypy, sin puerta). Tampoco `pre-commit run --all-files` (ruff-format
  reescribiria 88 ficheros de agents/).

## Fixtures y dependencias de cwd

- Unico conftest: agents/tests/conftest.py (fixtures `project_root` y `context`, ambas
  function-scoped sobre tmp_path). tests/ no tiene conftest y no importa nada de agents
  (grep `^from agents` en tests/ -> 0). No hay fixtures compartidas ni estado de sesion.
- Ningun test usa os.chdir/getcwd ni rutas absolutas literales. Dependencias de path:
  test_installer_agent.py:85 (repo_url=str(tmp_path/...) absoluta -> es lo que destapa el
  bug de separadores) y test_installer_agent.py:81 (Path(__file__).parents[2], portable).
  test_refactor_scope usa solo ctx.root (tmp_path).

## Sin verificar

- No ejecute los tests en Linux: el fallo de installer en ubuntu es deduccion a partir de
  la semantica de pathlib (absoluta reemplaza), no una ejecucion real.
- No ejecute `uv sync --frozen`: solo `uv lock --check` sobre una copia temporal en %TEMP%.
- Los 88 ficheros de agents/ que ruff-format reformatearia: conteo del propio comando,
  no revise el diff.

## Hallazgo posterior (verificado)

El uv.lock COMMITEADO estaba ya desincronizado: git diff muestra tribal 0.1.3 -> 0.1.4.
No lo edite a mano: cualquier uv run sin --frozen re-lockea el proyecto solo. Es el
mismo sintoma del punto anterior y confirma que el primer CI con uv sync --frozen`nhabria fallado sin tocar nada. commit_feature debe ejecutar uv lock y el repo debe
commitear el lock actualizado.
