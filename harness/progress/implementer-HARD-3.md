# implementer · HARD-3

- **Fecha:** 2026-11-20
- **Veredicto:** ok

## Qué cambié

- `README.md` — B1: reordenadas §5 (export), §6 (`culture ask`) antes de la
  brecha del modelo real (§7), etiquetadas «sobre la partida de 1200 ticks del
  §3»; §3 avisa de que §4-§6 leen esa base y §7 la pisa con `--fresh`. Las
  salidas publicadas (27/24/28 y «no hay nodos apagados») son las de esa base
  stub, verificadas hoy. §7 ya no publica números de export/consulta.
  Contadores LLM formulados como «en la corrida publicada» (el timing varía).
- `tests/test_final.py` — B2: añadidos `assert kpi["pct_fuera_arbol"] > 0.0` y
  `assert kpi["veredicto"] == (all(hitos) and pct >= umbral)`, con comentario
  del ancla.
- `vault/01_PROYECTO/arquitectura.md` — contadores LLM como «en la corrida
  publicada»; el estado final y los límites no cambian.
- `project.yml` — `project_version: 0.1.34`, alineado con `pyproject.toml`.

## Criterios de aceptación

1. **10 semillas reproducen la partida.** `uv run pytest tests/test_final.py -q`
   → `10 passed in 60.11s`. Dos procesos por semilla, DB en `tmp_path`; resumen
   y `report kpi --json` idénticos.
2. **KPI anclado.** Las 10 semillas dan `pct_fuera_arbol > 0` (8.0-18.2) y el
   veredicto coincide con `4/4 hitos && pct >= 50`. Mutación verificada:
   forzando `"arbol"` en `tribal/store/repositorio.py` (línea del INSERT de
   nodos), el test de la semilla 1 cae con `assert 0.0 > 0.0`; revertida.
3. **README §1-§9 coherente.** Flujo §1→§7 ejecutado: la base stub da
   27 nodos/24 aristas/28 ficheros y ningún apagado; la base real de la raíz da
   32/34/33 y 5 apagados, pero §7 ya no publica esos números. §5 export y §6
   consulta quedan antes de §7 con la etiqueta de la partida de 1200 ticks.
4. **RAG.** `uv run python -m agents run rag index` → aviso
   `✘ [rag.index] chromadb no está instalado. Ejecuta: uv sync --extra rag`;
   documentado en README §9. No se instaló el extra.
5. **Gate.** `harness gate` → `"success": true`, ENTORNO LISTO, 472 passed;
   `./init.sh` → ENTORNO LISTO, 472 passed.
6. **Doctor.** `project_config` → `tribal v0.1.34 (python 3.12)`, 7/7 OK.

## Evidencia

```
$ uv run pytest -q
1028 passed, 15 skipped in 387.81s (0:06:27)

$ uv run pytest tests/test_final.py -q
10 passed in 60.11s (0:01:00)

$ uv run ruff check tribal/ tests/ agents/      All checks passed!
$ uv run ruff format --check tribal/ tests/     87 files already formatted
$ uv run mypy tribal/ tests/                    Success: no issues found in 87 source files

$ uv run python -m agents --json run harness gate
"success": true · "ENTORNO LISTO — se puede trabajar."
"check": "pytest", "detail": "472 passed in 319.57s (0:05:19)"

$ ./init.sh
━━ ENTORNO LISTO ━━  0 aviso(s)
pytest 472 passed in 320.29s (0:05:20)

# Mutación B2 (origen forzado a "arbol" al guardar), semilla 1:
$ uv run pytest "tests/test_final.py::test_la_partida_completa_se_reproduce_entre_procesos[1]" -q
>       assert kpi["pct_fuera_arbol"] > 0.0
E       assert 0.0 > 0.0
1 failed in 6.40s
# revertida: git diff tribal/store/repositorio.py vacío; test_final 10/10.

# B1, base stub de 1200 ticks del §3:
$ uv run python -m tribal report db --db <stub>
seed 1  tick 1200  poblacion 18  estacion sin estacion
nodos 27  aristas 24  arbol 23  combinacion 0  interaccion 4  llm 0
$ uv run python -m tribal export obsidian --db <stub> --out <tmp>
export obsidian: 27 nodos, 24 aristas, 28 ficheros
$ uv run python -m tribal culture ask --db <stub> --query "que nodos se apagaron"
no hay nodos apagados
```

## Qué falta

- Extra `rag` sin instalar: aviso exacto y `uv sync --extra rag` en README §9.
- El 14.8 % real (`False`) sigue siendo límite del modelo, documentado; no lo
  cubre ningún test porque depende de Ollama.
- D3 no incluido; la tabla N=50 de F1 se conserva como medición histórica.
