# reviewer · FIX-002

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

## Criterios

1. **Cumplido.** `git grep -n '"app"' -- agents/tools/rag_tool.py` → 0 coincidencias.
   `FUENTES = _fuentes(_RAIZ)` (rag_tool.py:647) y `_fuentes` (l.288) toma
   `load_project_config(root).project_slug` (l.297). `ProjectConfig.project_slug`
   por defecto es `""`, así que no se inventa `app` en ningún camino. El literal
   solo sobrevive en el docstring/aserción del test nuevo, no en la tabla.

2. **Cumplido.** `agents/tests/test_rag_fuentes.py` (4 tests, 4 passed in 0.33s):
   - `test_fuentes_incluye_el_paquete_del_proyecto`: exige `tribal` y prohíbe `app`.
   - `test_fuentes_sale_de_project_slug`: escribe un `project.yml` **real** en
     `tmp_path` con `project_slug: otro_paquete` y comprueba `subs[0] == "otro_paquete"`
     y `"tribal" not in subs`. No es tautológico: si se hardcodea `tribal`, falla.
   - `test_fuentes_sin_project_slug_no_inventa_paquete`: sin fichero no hay fila
     vacía ni `app`; `subs[0] == "api"`.
   - `test_fuentes_no_duplica_el_slug`: slug `agents` → `count("agents") == 1`.
   Si se revierte a `("app", ...)`, el test 1 falla y el resto ni existe.

3. **Cumplido.** Ejecutado por mí:
   `uv run python -c "from agents.tools.rag_tool import RagTool; print([f[0] for f in RagTool.FUENTES])"`
   → `['tribal', 'api', 'chat', 'monitoring', 'tuning', 'agents', 'agents/prompts', 'docs', 'vault', 'harness/progress']`
   `tribal` primero, `app` ausente.

4. **Cumplido.** `uv run pytest -q` → 555 passed, 15 skipped in 62.08s (mi ejecución).
   `harness gate` → `"success": true`, `ready: true`, 0 errores, 0 warnings.

## Verificaciones extra (no del informe)

- **Indexación real:** `RagTool._documentos(Path.cwd())` enumera 230 documentos,
  **16 de `tribal/`** y **0 de `app/`**. No revienta sin chromadb porque `_documentos`
  es puro filesystem.
- **Llamadores:** `_documentos(root)` usa `RagTool.fuentes(root)` (l.672);
  `index_project`, `_recolectar`, `status` y `search` le pasan siempre `root`/`self.ctx.root`.
  `RagTool.FUENTES` no lo consume nadie más que el test nuevo: sigue siendo tupla de
  la misma forma, así que no rompe consumidores.
- **Repo sin `project.yml`:** `fuentes(tmp)` → 9 filas fijas, sin `app` ni fila vacía;
  `_documentos(tmp)` → `[]`, sin excepción. `FUENTES` sigue intacto (`tribal`).
- **Calidad:** `ruff check tribal/ tests/ agents/` → All checks passed;
  `ruff format --check tribal/ tests/` → 23 files already formatted;
  `mypy tribal/ tests/` → no issues (23 source files);
  `doctor checkup` → 7/7; `review review_package` → 0 hallazgos;
  `test coverage_report` → 95.25% total.
- **Secrets scan:** devuelve `success=false`, pero los 13 hallazgos están todos en
  `agents/tests/test_redaction.py` y `agents/tests/test_secrets_agent.py` — fixtures
  falsas, preexistentes, ficheros no tocados por este diff. Nada en el código nuevo.
- **Alcance:** `git status` solo muestra `agents/tools/rag_tool.py` modificado y
  `agents/tests/test_rag_fuentes.py` nuevo. `tribal/` intacto. `harness/featureslist.json`
  y `harness/progress/current.md` solo tienen el efecto de `harness start`
  (`pending→in_progress`, `started`, `review_rounds: 0`, plantilla rellenada).
  No existe `.rag-index`, luego no hubo reindexado.
- **Secretos/rutas absolutas:** ninguno; `_RAIZ` sale de `__file__`, no hay rutas hardcodeadas.

## Bloqueantes

_(ninguno)_

## No bloqueante

- `FUENTES` se calcula al importar desde `_RAIZ`. No sigue a un `project.yml` que
  cambie en caliente y, en una copia instalada (site-packages) sin `project.yml`,
  se quedaría sin fila de paquete. Sin consecuencia hoy porque el camino real
  (`_documentos`) usa `fuentes(root)`; el comentario de la clase ya lo dice.
- Dedup por subdirectorio: si el paquete se llamara igual que una fuente md
  (`docs`, `vault`, `harness/progress`), su fila fija se sustituiría por la fila
  `*.py` del paquete y se perderían esos `.md`. Solo alcanzable con un nombre de
  paquete muy improbable; el test de dedup cubre el caso seguro (`agents`).
- Test 1 fija `"tribal"`: un futuro renombrado del paquete exigirá tocar el test.
  Es el precio de que sea una regresión de verdad, no una tautología.
- **Preexistente, fuera de alcance:** `EXCLUIDOS` compara `"/tests/"` contra un
  `origen` construido con `os.sep`, así que en Windows se indexan
  `agents\tests\*.py` (230 docs los incluyen). Nada que ver con este diff; merece
  ticket propio.
- **Drift en mi propia definición** (`.opencode/agents/reviewer.md`): los comandos
  sugeridos `run test coverage_summary` y `run doctor` no existen tal cual — son
  `test coverage_report` y `doctor checkup`. Lo anoto sin editar a mitad de revisión
  para no ensuciar el diff de la feature.
- `agents/tools/agent_installer_tool.py:36` conserva el literal `app`; el
  implementer lo declaró fuera de alcance y el criterio no lo cubre.
