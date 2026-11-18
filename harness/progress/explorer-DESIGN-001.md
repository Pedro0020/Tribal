# explorer · DESIGN-001

- **Fecha:** 2026-11-18
- **Veredicto:** ok

## Respuesta

Renombrar `app/` -> `tribal/` toca 4 ficheros de producto/config (project.yml, pyproject.toml, Makefile, app/paths.py) + 3 tests + 2 docs + 1 pre-commit. El arnes NO esta cableado a `app`: todo lo deriva de `project_slug` salvo DOS sitios de `agents/` (rag_tool.py:601 y agent_installer_tool.py:36) y varios docstrings de ejemplo.

Inventario (P = producto, S = si editar a mano, N = no editar a mano):

| # | Ruta:linea | Que hay | S? |
|---|---|---|---|
| 1 | project.yml:10 | `project_slug: app` (comentario guia en :7) | SI |
| 2 | pyproject.toml:43 | `app = "app.cli:main"` en [project.scripts] | SI |
| 3 | pyproject.toml:50 | `packages = ["app"]` (hatch wheel) | SI |
| 4 | pyproject.toml:82 | `source = ["app"]` (coverage.run) | SI |
| 5 | pyproject.toml:5-6 | description/version; name ya es `tribal` (:2) | SI |
| 6 | Makefile:15 | `MODULE = app`; consumido en :26,35,95,106,110,124,125,128,131,135,141,150,253 | SI |
| 7 | app/paths.py:21 | `PACKAGE_DIR = ROOT_DIR / "app"` (literal; :18 comentario) | SI (producto) |
| 8 | app/__init__.py:2,:10 | docstring `app - paquete del proyecto` y receta de renombrado | SI (producto) |
| 9 | app/__main__.py:1,:5 | `python -m app` + `from app.cli import main` | SI (producto) |
| 10 | app/cli.py:2,:15,:19 | docstring `python -m app`, `from app import __version__`, `prog="app"` | SI (producto) |
| 11 | tests/test_cli.py:7 | `from app.cli import ...` | SI |
| 12 | tests/test_paths.py:7,:11 | `from app import paths` y `ROOT_DIR / "app" / "__init__.py"` | SI |
| 13 | tests/test_main_import.py:1,7,8,12,13,14 | `import app`, `app.__path__`, prefix `app.` | SI |
| 14 | .pre-commit-config.yaml:20 | `files: ^(app|tests)/` (hook mypy) | SI |
| 15 | docs/source/index.rst:6 | docstring `(app/)`; Makefile:150 `sphinx-apidoc ... $(MODULE)/` | SI |
| 16 | README.md:65 | arbol de estructura `app/ ...` | SI |
| 17 | vault/00_META/IA_index.md:9 | `Paquete: app/` | SI |
| 18 | vault/01_PROYECTO/stack-tecnologico.md:252 | nota historica (dice `app/` vacio) | SI (prosa) |
| 19 | vault/05_AGENTES/RefactorAgent.md:40, TestAgent.md:39 | `app/**/*.py`, `--cov=app` (doc generada) | SI (prosa) |
| 20 | AGENTS.md:333 | `el paquete (app/ por defecto)` | SI (prosa del arnes) |
| 21 | .opencode/agents/explorer.md:31, implementer.md:32; .claude/agents/explorer.md:39, implementer.md:39 | ejemplos `app/data/loader.py:42`, tabla `Codigo del producto -> app/` | OPCIONAL (config del asistente) |
| 22 | agents/tools/rag_tool.py:601 | `("app", "*.py", True, None, "py")` en FUENTES: TRAS EL RENOMBRADO EL RAG DEJA DE INDEXAR EL CODIGO | **SI (imprescindible)** |
| 23 | agents/tools/agent_installer_tool.py:36 | regex `(app|src|tests|...)` de heuristica de aviso | OPCIONAL (solo warning) |
| 24 | agents/agents/git_agent.py:5; test_agent.py:160; review_agent.py:166; agents/cli.py:8 | docstrings que dicen `app/` a modo de ejemplo (la logica usa project_slug) | OPCIONAL (cosmetico) |
| 25 | harness/featureslist.json:31 | criterio de DESIGN-001 (texto) | **NO** (dueno: harness) |
| 26 | harness/progress/current.md:17 | checklist de la feature | **NO** (dueno: harness) |
| 27 | harness/progress/history.md:34-38,68-72,185-198 | evidencia append-only con `app/` | **NO** (append-only) |
| 28 | harness/memory.md:15 | `make check -> ruff check app/ tests/ agents/` | **NO** (memoria, no se edita a mano) |

No existe `.github/` (solo hay que crearlo en QA-001). `.mcp.json` y `opencode.json` NO mencionan `app`. `.env.example` tampoco. `.gitignore` no tiene rutas a `app` (solo `**/__pycache__/`).

## Donde esta

- project.yml:10, pyproject.toml:43/50/82, Makefile:15
- app/paths.py:21 (unico literal del paquete dentro del producto)
- tests/test_paths.py:11
- agents/tools/rag_tool.py:601 (el unico hardcode funcional del arnes)

## Respuestas 2, 3, 4

**2. `agents/config.py` no asume `app`.** ProjectConfig.project_slug es un campo generico con default vacio (config.py:77). Todo lo consume via `ctx.package_dir = root / config.project_slug` (context.py:38): git_agent.py:104/134, cicd_agent.py:107, test_agent.py:101/178, review_agent.py:169, refactor_agent.py:50, documentation_agent.py:147, doctor_agent.py:109/194/198. `init.sh` SI lo deriva de project.yml (init.sh:234 `sed` sobre project_slug, :238 `ok` si `-d $SLUG`, :240 `fail` si no). O sea: la puerta protege el renombrado, pero NO comprueba pyproject (make check y coverage no los mira init.sh). Excepciones hardcodeadas: rag_tool.py:601 y agent_installer_tool.py:36.

**3. Dependencias del nombre.** Dejarian de funcionar (sin tocar los 4 sitios):
- `uv run python -m app hello` y `make run` / `make profile` (Makefile:106,110)
- el entry point de consola: `.venv/Scripts/app.exe` (generado desde pyproject.toml:43)
- `uv run pytest --cov=app` y `[tool.coverage.run] source` (pyproject.toml:82)
- `make lint/format/typecheck/security/complexity/docs/clean` (usan `$(MODULE)`)
- cualquier `from app... import` / `import app` (tests incluidos)
- `sphinx-apidoc -o docs/source/ app/` (Makefile:150)
- la indexacion RAG del codigo de producto (rag_tool.py:601)

**4. Stack real.** Python 3.12.12 (`.python-version`=3.12). `uv pip list`: NO hay pydantic ni chromadb. SORPRESA: `pygame-ce 2.5.8` SI esta instalado e importable (`pygame 2.5.8 (SDL 2.32.10)`) pero NO esta en pyproject (dependencies=[]) ni en uv.lock -> el proximo `uv sync` lo desinstala. Proyecto editable `tribal 0.1.1` apuntando a la raiz.

Para CORE-001, segun stack-tecnologico.md:260 (Fase 0 = Python + Pygame + Pydantic + config/semilla + opcional SQLite):
- `pygame-ce` (PyPI exacto; importa como `pygame`) - NO stdlib - ya presente en el venv, hay que declararlo
- `pydantic` (>=2; arrastra `pydantic-core` y `typing-extensions`) - NO stdlib - pydantic 2.13.4 ya esta en uv.lock como transitiva del extra rag, pero no instalado
- config/semilla: stdlib - `json` o `tomllib` (3.11+) + `random.seed` + `pathlib`
- SQLite (opcional Fase 0): stdlib `sqlite3`
- NO anadir `pydantic-settings` ni numpy (no los pide la Fase 0 en :260)

## Riesgos y sorpresas

1. **RAG se queda a ciegas.** rag_tool.py:601 lista `("app", "*.py", ...)`. Tras el renombrado, `make index-rag` indexa todo MENOS el codigo de producto, sin error. Es el unico cambio en `agents/` que es imprescindible.
2. **pygame-ce fantasma.** Esta en el venv, no en el lock. Cualquier `uv sync` (incluido el que haga el implementer) lo borra y `import pygame` empieza a fallar sin que nadie haya tocado codigo. Declararlo en el mismo PR del renombrado o antes.
3. **Entry point obsoleto.** `app.exe` en `.venv/Scripts` sigue existiendo hasta que se reinstale el proyecto editable; falla con ModuleNotFoundError. Hay que `uv sync` (o `uv pip install -e .`) DESPUES de cambiar pyproject.
4. **uv.lock ya esta sucio** (`git diff --stat`: uv.lock 2 lineas). Hay cambios sin commitear en harness/featureslist.json, harness/progress/current.md y uv.lock. Commitear o reconciliar ANTES del rename, o el diff mezcla dos cosas.
5. **Windows/git:** `git mv app tribal` funciona (no es cambio solo de mayusculas; `core.ignorecase` esta sin definir pero da igual). Riesgo real: `app/__pycache__` con .pyc de 3.12 Y 3.14 (hay ambos en el arbol) - borrar `app/__pycache__` antes del mv y `find . -name __pycache__ -exec rm -rf` despues; `.pytest_cache`/`.ruff_cache` guardan rutas viejas (`pytest --cache-clear`). Si un proceso tiene el directorio abierto (ventana pygame, antivirus, OneDrive: el repo esta bajo `Documents`) el `git mv` falla con Permission denied.
6. **`tribal/` como nombre de paquete no choca** con `agents/`, `harness/`, `vault/`, `docs/`, `tests/`, `models/`. Ojo: ya hay un directorio `models/` en la raiz (visto en el listado); si el motor va en `tribal/models/` no hay conflicto, pero conviene decidirlo en DESIGN-001 y no descubrirlo en CORE-001.
7. `app/__init__.py` documenta el rename como 4 sitios pero omite tests, Makefile y el script de consola; no fiarse de esa lista.

## Sin verificar

- No ejecute `git mv` ni `uv sync` (solo lectura): los efectos sobre `.venv` son deducidos del `.pth` (`_editable_impl_tribal.pth` -> raiz del repo, no el paquete) y de la ausencia de pygame en uv.lock.
- No comprobe si `make` funciona en esta maquina; harness/memory.md:11 dice que NO esta instalado y que se usan los equivalentes `uv run`. El Makefile igualmente hay que corregirlo.
- No abri todos los `vault/` (solo 00_META/IA_index.md, 01_PROYECTO/stack-tecnologico.md:252, 05_AGENTES/RefactorAgent.md, TestAgent.md); puede haber mas menciones de `app/` en notas no tocadas por el grep por usar otra grafia.
- `rag status` responde `success=false` (chromadb no instalado): no hay indice que reindexar hoy, asi que el riesgo 1 es latente, no inmediato.
