# implementer · F3-005

- **Fecha:** 2026-11-19
- **Veredicto:** ok

## Qué cambié
- `tribal/culture/consulta.py` — vocabulario: `hasta`, `llegar` en `_PALABRAS_RUTA`; `murieron`/`murio`, `fallecieron`/`fallecio`, `desaparecieron`/`desaparecio` en `_PALABRAS_APAGADOS`; docstring alineado.
- `tribal/cli.py` — `culture ask` comprueba `args.db.is_file()`: un directorio da `error: ... no es un fichero` y exit 2.
- `tests/test_consulta.py` — +5 tests: vocabulario de ruta, vocabulario de apagados, arista inversa, desempate entre caminos iguales, `--db <directorio>`.
- `README.md` y `vault/01_PROYECTO/arquitectura.md` — listas de palabras clave actualizadas.

## Bloqueantes del reviewer

1. Vocabulario documentado — RESUELTO. La BD de 5000 ticks (semilla 2, crisis) responde:
   ```
   $ ... --query "hasta el fuego"
   intencion: ruta
   destino: ahuyentar_depredadores - Ahuyentar depredadores
   camino (5 pasos): ...
   $ ... --query "que nodos murieron con el anciano"
   intencion: apagados
   apagados (3): raedera, caceria_dirigida, turnos_de_vigilia
   ```
   Tests: `test_vocabulario_documentado_de_ruta` (hasta/llegar/llego) y
   `test_vocabulario_documentado_de_apagados` (murieron/fallecieron/desaparecieron).

2. BFS no dirigido — RESUELTO y anclado con dos tests:
   - `test_bfs_recorre_aristas_en_sentido_inverso`: única arista `lasca→guijarro`; desde la raíz `guijarro` exige camino `guijarro→lasca`.
   - `test_desempate_estable_entre_caminos_de_igual_longitud`: dos rutas de 2 aristas insertadas en orden `raiz→beta`, `raiz→alfa`; exige `raiz→alfa→fuego`.

## Mutaciones verificadas
Con el fichero mutado y restaurado (script temporal, hash final idéntico):
```
dirigido (sin la arista inversa):  1 failed, 11 passed — cae test_bfs_recorre_aristas_en_sentido_inverso
sin_sort (vecinos.sort() -> pass): 1 failed, 11 passed — cae test_desempate_estable...
vocabulario (sin hasta/murieron):  2 failed, 10 passed — caen los dos tests de vocabulario
```

## No bloqueante arreglado
`uv run python -m tribal culture ask --db .tmp-dir --query "hasta el fuego"` →
`error: .tmp-dir no es un fichero`, `exit=2`. Test `test_cli_ask_con_directorio_sale_con_dos`.

## Evidencia
- `uv run pytest -q` → `1003 passed, 15 skipped in 295.67s (0:04:55)`
- `uv run ruff check tribal/ tests/ agents/` → `All checks passed!`
- `uv run ruff format --check tribal/ tests/` → `84 files already formatted`
- `uv run mypy tribal/ tests/` → `Success: no issues found in 84 source files`
- `harness gate` → `"success": true`, `ready: true`, `errors: 0`, `warnings: 0`, `pytest 447 passed`.
- `tribu.db` de evidencia y temporales borrados; sin commit.

## Qué falta
Nada solicitado por el reviewer. Quedan solo sus no bloqueantes preexistentes
(persistir `ultimo_imitador` en `store`, renombrar `arista` de recorrido), fuera de F3-005.
