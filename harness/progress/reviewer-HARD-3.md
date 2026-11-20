# reviewer · HARD-3

- **Fecha:** 2026-11-20
- **Veredicto:** aprobado

## Criterios

1. **10 semillas, dos procesos, partida reproducible — cumplido.** `uv run pytest
   tests/test_final.py -q` → `10 passed in 56.31s`. Las 10 semillas lanzan dos
   subprocess con `--llm stub --llm-sincrono`, 1200 ticks y DB en `tmp_path`, y
   exigen `run --json` y `report kpi --json` byte a byte iguales. B2 cerrado.

2. **`report telemetry --db` y `report kpi --db` — cumplido.** Reproducido sobre
   `tribu.db` generada por §3: `muestras 20  ticks 60..1200`, filas 60/120 y
   1200 idénticas al README, KPI `herramienta_compuesta no`, `4/27`, `14.8 %`,
   `False`. Sobre la base real de 3000 ticks: `muestras 50  60..3000`, los cuatro
   hitos en `si`, `4/27`, `False`.

3. **README y arquitectura — cumplido (B1 cerrado).** Seguí el README en orden y
   ejecuté cada comando. §3 avisa de que §4-§6 leen la base stub y §7 la pisa;
   §5 y §6 van etiquetadas «sobre la partida de 1200 ticks del §3»; §7 ya no
   publica salidas de export ni de consulta.
   - §3 `run` + `report db` → `seed 1 tick 1200 poblacion 18`, `nodos 27 aristas
     24 ... telemetria 20` (igual que el README).
   - §4 telemetría → `muestras 20  ticks 60..1200`, `60  12 3 5 4 22 19 76.77
     17.22`, `1200  18 5 7 6 27 24 59.95 38.38` (igual).
   - §4 KPI → `herramienta_compuesta no`, `14.8 % (4/27)`, `False` (igual).
   - §5 export → `27 nodos, 24 aristas, 28 ficheros` (igual).
   - §6 `culture ask` → `destino ahuyentar_depredadores`, 5 pasos, autores 2/4,
     ticks 3-10; segunda consulta `no hay nodos apagados` (igual).
   - §7 `run --llm http --ticks 3000 --seed 1 --crisis --fresh` (51.75 s) →
     `report db`: `seed 1 tick 3000 nodos 32 aristas 34`; `report kpi`: cuatro
     hitos `si`, `14.8 % (4/27)`, `False` (igual en KPI; el README ya no publica
     32/34/33 ni los apagados en §7, así que no hay nada que no cuadre).
   - §7 headless: `run --headless --llm http --ticks 3000 --seed 1 --crisis` →
     6.99 s, 1 petición, 0 aplicadas, mismo 14.8 % (coincide con
     «7.04 s, 1 petición, 0 aplicadas»).
   Arquitectura §9 conserva los límites abiertos sin maquillar (14.8 %/`False`,
   D3 inexistente, `relaciones`/`recuerdos` vacías, tope de una tradición por
   rama, N=50 sin replicar todas las condiciones) y §9.5 explica la medición.

4. **`rag index` — cumplido.** `uv run python -m agents --json run rag index` →
   `"success": false`, `"chromadb no está instalado. Ejecuta: uv sync --extra
   rag"`, exit 1. README §9 reproduce el aviso y el extra.

5. **Gate — cumplido.** `uv run python -m agents --json run harness gate` →
   `"success": true`, `ENTORNO LISTO — se puede trabajar.`, `pytest 472 passed in
   318.42s`.

6. **B2 (test_final ancla el KPI) — cumplido.** Mutación aplicada en
   `tribal/store/repositorio.py` (`nodo.origen` → `"arbol"` en el INSERT):
   `pytest "tests/test_final.py::... [1]"` → `assert 0.0 > 0.0`, `1 failed in
   11.02s`. Revertida (`git diff tribal/` vacío) y `10 passed in 56.31s`.
   El test exige además `pct > 0`, `umbral == 50.0` y
   `veredicto == (all(hitos) and pct >= umbral)`.

## Bloqueantes

_(ninguno)_

## No bloqueante

- **Tiempos publicados.** README/arquitectura citan 60.37 s (60 fps) y 7.04 s
  (headless); en esta máquina dan 51.75 s y 6.99 s. Son la medición de la corrida
  publicada y los contadores ya van matizados («en la corrida publicada», «el
  timing varía»); el KPI (`14.8 %`, `False`) sí se reproduce.
- **`secrets scan`**: 13 hallazgos, todos fixtures preexistentes de
  `agents/tests/test_redaction.py` y `agents/tests/test_secrets_agent.py`; sin
  secretos reales. El detector es el heurístico propio (falta `detect-secrets`).
- **`doctor checkup`**: 7/7 OK, `project_config` ya informa `tribal v0.1.34`.
- **`opencode.json`**: sigue versionado en la raíz, sin cambios en este diff.
- Sin dependencias nuevas (`pyproject.toml`/`uv.lock` sin cambios), sin `.tmp-*`,
  y `test_final.py` es el único código nuevo.

## Evidencia ejecutada

```
$ uv run python -m agents --json run harness gate
"success": true · "ENTORNO LISTO — se puede trabajar." · pytest 472 passed in 318.42s

$ uv run pytest tests/test_final.py -q                 10 passed in 56.31s
$ uv run ruff check tribal/ tests/ agents/             All checks passed!
$ uv run ruff format --check tribal/ tests/            87 files already formatted
$ uv run mypy tribal/ tests/                           Success: no issues found in 87 source files
$ uv run python -m agents --json run doctor checkup    7/7 · tribal v0.1.34

# Flujo README §3-§7 reproducido en orden (salidas comparadas arriba)
# Mutación B2: 1 failed in 11.02s (assert 0.0 > 0.0); revertida → 10 passed
```
