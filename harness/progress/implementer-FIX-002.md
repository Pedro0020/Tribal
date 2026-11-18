# implementer · FIX-002

- **Fecha:** 2026-11-18
- **Veredicto:** ok

## Qué cambié

- `agents/tools/rag_tool.py`: la fila del paquete del índice sale de `project_slug`.
  Tabla fija + helper `_fuentes(root)` (lee `project.yml` de esa raíz, sin slug
  no inventa paquete, deduplica el slug contra las filas fijas). `RagTool.FUENTES`
  queda como tabla del repo que contiene el fichero; `RagTool.fuentes(root)` es
  la que usa `_documentos(root)`, para que indexar otra raíz no dependa del repo.
- `agents/tests/test_rag_fuentes.py`: 4 tests (tribal presente / app ausente,
  slug de un `project.yml` falso en `tmp_path`, sin slug no hay fila vacía,
  slug repetido no se duplica).

## Criterios de aceptación

1. Sin el literal 'app' en FUENTES — `grep -n "app" agents/tools/rag_tool.py`
   no devuelve la tabla; `RagTool.FUENTES` se calcula con
   `_fuentes(_RAIZ)` → `load_project_config(root).project_slug`.
2. Test que exige tribal y que cambiar project_slug cambia la fuente —
   `uv run pytest agents/tests/test_rag_fuentes.py -q` → 4 passed.
3. One-liner lista tribal y no app →
   `['tribal', 'api', 'chat', 'monitoring', 'tuning', 'agents', 'agents/prompts', 'docs', 'vault', 'harness/progress']`
4. `uv run pytest -q` → 555 passed, 15 skipped in 60.62s;
   `harness gate` → `"success": true`.

## Evidencia

```
$ uv run python -c "from agents.tools.rag_tool import RagTool; print([f[0] for f in RagTool.FUENTES])"
['tribal', 'api', 'chat', 'monitoring', 'tuning', 'agents', 'agents/prompts', 'docs', 'vault', 'harness/progress']

$ uv run pytest agents/tests/test_rag_fuentes.py -q
....                                                                     [100%]
4 passed in 0.54s

$ uv run pytest -q
........................................................................ [ 12%]
........................................................................ [ 25%]
........................................................................ [ 37%]
........................................................................ [ 50%]
........................................................................ [ 63%]
...................................................................s.sss [ 75%]
sssssssss..s............................................................ [ 88%]
.................................................................        [100%]
555 passed, 15 skipped in 60.62s (0:01:00)

$ uv run ruff check tribal/ tests/ agents/ && uv run ruff format --check tribal/ tests/
All checks passed!
23 files already formatted

$ uv run mypy tribal/ tests/
Success: no issues found in 23 source files

$ uv run python -m agents --json run harness gate | grep success
  "success": true,
```

## Qué falta

- Nada del alcance. Fuera de alcance y documentado en DESIGN-001:
  `agents/tools/agent_installer_tool.py:36` sigue con el literal `app`;
  `make index-rag` no se ha ejecutado (reindexar es acción del líder/usuario,
  no cambia el código).
