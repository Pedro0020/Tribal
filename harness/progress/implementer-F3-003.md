# implementer · F3-003

- **Fecha:** 2026-11-19
- **Veredicto:** ok

# Implementer F3-003 — matices del reviewer

## Qué cambié

- `tribal/store/export.py`: frontmatter incluye `motivo_apagado`; validación de
  aristas con extremo inexistente (`ExportInvalido`) antes de indexarlas;
  etiquetas direccionales «lo desbloquea» (saliente) y «requiere» (entrante).
- `tribal/store/__init__.py` y `tribal/cli.py`: reexportan/capturan
  `ExportInvalido`; `export obsidian` sale con 2 y mensaje, sin traza.
- `tests/test_export.py`: fixture con nodo apagado (`tick_apagado=650`,
  `motivo="sin portadores"`); frontmatter comparado campo a campo (id, rama,
  nivel, origen, estado, autor, tick, tick_apagado, motivo_apagado) contra el
  nodo de la base; test de arista colgante.

## Verificación de mutaciones (criterio 1)

Mutación aplicada en `export.py`: `estado` fijo a `"activo"` para todos.
`uv run pytest -q tests/test_export.py -k un_md_por_nodo_y_dos_wikilinks_por_arista`
→ `1 failed, 4 deselected`, con
`assert 'activo' == 'apagado'` en `eco-apagado.md`. Revertida después.

## Evidencia

```
$ uv run pytest -q
982 passed, 15 skipped in 292.78s (0:04:52)
$ uv run pytest -q tests/test_export.py
5 passed
$ uv run ruff check tribal/ tests/ agents/
All checks passed!
$ uv run ruff format --check tribal/ tests/
82 files already formatted
$ uv run mypy tribal/ tests/
Success: no issues found in 82 source files
$ uv run python -m agents --json run harness gate
"success": true, "ready": true, "errors": 0, "warnings": 0
```

## Qué falta

Nada. Sin commit ni cierre; sin cambios de docs (alcance tests/export).
