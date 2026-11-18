# implementer · F1-002

- **Fecha:** 2026-11-18
- **Veredicto:** ok

# F1-002 — Árbol de conocimiento con progresión y origen de nodo

## Qué cambié

- `tribal/culture/arbol.py` — `Nodo` frozen (`id`, `rama`, `nivel`, `titulo`, `contenido`,
  `requisitos`, `origen`, `estado`, `autor`, `tick`) y `ARBOL`: 23 nodos en las cinco ramas
  (lítica 0-4, fuego 0-4, lenguaje 0-3, roles 0/0/1/2/2, simbólico 0-3). Los niveles 0 no exigen
  nada; el resto pide los de su rama y dos cruzan: `mito` ← `proto_palabras`+`ritual` y
  `lider` ← `anciano`+`caza_cooperativa`, con el porqué en el docstring. Un id repetido falla al
  importar.
- `tribal/culture/grafo.py` — `Grafo` con `nodos`/`aristas`; `descubrir()` valida que todos los
  requisitos estén activos y lanza `PrerequisitoFaltante`, escribe `origen`/`autor`/`tick` al
  crear, y es idempotente (redescubrir no reescribe nada). `avanzar(rama)`, `pct_fuera_arbol()`
  (KPI de `objetivo.md` §3.2), `nodos_por_origen()` y `a_json()`.
- `tribal/culture/__init__.py` — docstring del paquete.
- `tribal/sim.py` — `Simulacion.grafo`; `PRACTICAS` (`comer` + `recolectar` → lítica) y
  `_practicar()`: un nodo nuevo como mucho por tick, solo si quien practica sabe la habilidad.
  `resumen()` añade `nodos`, `aristas`, `pct_fuera_arbol` y `nodos_por_origen`.
- `tribal/cli.py` — `report culture` con `--seed/--ticks/--config/--json`; el docstring del
  subcomando explica que en esta fase simula `--ticks` (600) en headless porque aún no hay
  `tribu.db`, y que cuando exista leerá el grafo guardado.
- `tests/test_arbol.py` — 15 tests (catálogo, DAG, rechazo, origen, inmutabilidad, idempotencia,
  KPI no-cero, gate de habilidad, tope por tick, simulación y CLI).
- `tests/test_cli_run.py` — `CLAVES` del resumen ampliadas con las cuatro claves nuevas.
- `README.md` — apartado «Árbol de conocimiento (Fase 1)» con la salida real; corregida la frase
  que decía que aún no había árbol.

## Ronda 2 — huecos no bloqueantes del reviewer

1. **Gate de habilidad (`tribal/sim.py:197`)** — dos tests nuevos que pasan por `step()`:
   `test_sin_la_habilidad_no_se_descubre_nodo` (come —las bayas bajan de 8 a 7— y `grafo.nodos`
   queda vacío) y `test_con_la_habilidad_el_nodo_nace_en_el_arbol` (`guijarro`, `origen="arbol"`,
   `autor` == el que comió). Mutación: `if False and not …sabe(habilidad)` →
   `1 failed, 14 passed`; restaurado.
2. **Tope de un nodo por tick (`tribal/sim.py:122-125`)** — `test_como_mucho_un_nodo_nuevo_por_tick`
   con tres individuos con `recolectar` encima de las bayas: `bayas.cantidad == 5` prueba que los
   tres comieron en el mismo tick, y `list(grafo.nodos) == ["guijarro"]` fija el tope (sin el
   `and not descubierto` saldrían `guijarro`, `lasca` y `bifaz`).
3. **`pct_fuera_arbol` no-cero (`tribal/culture/grafo.py:89-95`)** —
   `test_pct_fuera_arbol_solo_cuenta_combinacion_e_interaccion`: 3 `arbol` + 1 `combinacion` +
   1 `interaccion` → `40.0`; y al añadir un `llm` (que sí aparece en `nodos_por_origen`) → `33.3`,
   es decir `llm` no cuenta como fuera del árbol. Mutación: `nodo.origen in ()` →
   `1 failed, 14 passed`; restaurado.
4. **Docstrings** — `grafo.py` (módulo y `pct_fuera_arbol`) dice ahora exactamente que cuenta
   `combinacion` o `interaccion` (niveles 1 y 2 de §8b) y que `llm` no entra en el KPI;
   `arbol.py:29` aclara que §8b define tres niveles y que `llm` es un origen de propuesta, no un
   nivel.

## Criterios de aceptación

1. **`tribal/culture/arbol.py` define las cinco ramas con niveles y prerrequisitos** —
   `uv run python -m pytest tests/test_arbol.py -q` → 15 passed
   (`test_el_arbol_cubre_las_cinco_ramas_con_una_escalera_sin_huecos`,
   `test_los_requisitos_existen_y_forman_un_dag`,
   `test_los_nodos_de_nivel_cero_no_exigen_nada_y_el_mito_cruza_ramas`).
2. **El motor rechaza descubrir sin prerrequisitos y registra el origen al crear** —
   `test_sin_prerrequisito_no_hay_nodo` (lanza `PrerequisitoFaltante` y no deja nodo ni arista) y
   `test_con_el_prerrequisito_el_nodo_nace_con_origen_arbol` (`origen == "arbol"`, autor y tick
   del nacimiento, arista `guijarro → lasca`).
3. **Origen no reescribible** — `test_el_origen_no_se_puede_reescribir_despues`:
   `nodo.__setattr__("origen", "llm")` lanza `FrozenInstanceError` y redescubrir con
   `origen="combinacion"` devuelve el mismo objeto con origen/autor/tick intactos.
4. **`report culture --json` imprime nodos, aristas y `pct_fuera_arbol`** —
   `uv run python -m tribal report culture --json` (salida abajo): 5 nodos, 4 aristas,
   `pct_fuera_arbol: 0.0`.
5. **`harness gate success=true`** — `uv run python -m agents --json run harness gate` →
   `success: true`, `errors: 0`, `warnings: 0`, `pytest 102 passed`.

## Evidencia

`uv run python -m tribal report culture --json`:

```json
{"seed": 42, "ticks": 600, "nodos": [{"id": "guijarro", "rama": "litica", "nivel": 0, "titulo": "Guijarro", "origen": "arbol", "autor": 7, "tick": 263}, {"id": "lasca", "rama": "litica", "nivel": 1, "titulo": "Lasca", "origen": "arbol", "autor": 10, "tick": 272}, {"id": "bifaz", "rama": "litica", "nivel": 2, "titulo": "Bifaz", "origen": "arbol", "autor": 8, "tick": 279}, {"id": "punta_de_lanza", "rama": "litica", "nivel": 3, "titulo": "Punta de lanza", "origen": "arbol", "autor": 1, "tick": 313}, {"id": "caza_cooperativa", "rama": "litica", "nivel": 4, "titulo": "Caza cooperativa", "origen": "arbol", "autor": 12, "tick": 319}], "aristas": [{"origen": "guijarro", "destino": "lasca"}, {"origen": "lasca", "destino": "bifaz"}, {"origen": "bifaz", "destino": "punta_de_lanza"}, {"origen": "punta_de_lanza", "destino": "caza_cooperativa"}], "pct_fuera_arbol": 0.0, "nodos_por_origen": {"arbol": 5, "combinacion": 0, "interaccion": 0, "llm": 0}}
```

`uv run python -m tribal run --headless --ticks 3000 --json` (recorte de `nodos`/KPI, resto igual
que antes de la feature):

```
 "nodos": [
  {"id": "guijarro", "rama": "litica", "nivel": 0, "titulo": "Guijarro", "origen": "arbol", "autor": 7, "tick": 263},
  {"id": "lasca", "rama": "litica", "nivel": 1, "titulo": "Lasca", "origen": "arbol", "autor": 10, "tick": 272},
  {"id": "bifaz", "rama": "litica", "nivel": 2, "titulo": "Bifaz", "origen": "arbol", "autor": 8, "tick": 279},
  {"id": "punta_de_lanza", "rama": "litica", "nivel": 3, "titulo": "Punta de lanza", "origen": "arbol", "autor": 1, "tick": 313},
  {"id": "caza_cooperativa", "rama": "litica", "nivel": 4, "titulo": "Caza cooperativa", "origen": "arbol", "autor": 12, "tick": 319}
 ],
 "pct_fuera_arbol": 0.0,
 "nodos_por_origen": {"arbol": 5, "combinacion": 0, "interaccion": 0, "llm": 0}
```

`uv run python -m pytest tests/test_arbol.py -q --no-header`:

```
15 passed in 0.90s
```

Mutaciones (rojo → restaurado):

```
# gate de habilidad: if False and not individuo.habilidades.sabe(habilidad)
FAILED tests/test_arbol.py::test_sin_la_habilidad_no_se_descubre_nodo
1 failed, 14 passed in 0.84s

# pct_fuera_arbol: nodo.origen in ()
FAILED tests/test_arbol.py::test_pct_fuera_arbol_solo_cuenta_combinacion_e_interaccion
1 failed, 14 passed in 0.84s
```

`uv run python -m pytest -q --no-header`:

```
631 passed, 15 skipped in 67.58s (0:01:07)
```

`uv run ruff check tribal/ tests/ agents/` / `uv run ruff format --check tribal/ tests/`:

```
All checks passed!
35 files already formatted
```

`uv run mypy tribal/ tests/`:

```
Success: no issues found in 35 source files
```

`./init.sh` (vía Git Bash; `make` no está instalado en esta máquina, se usan los mismos comandos):

```
Entorno
  ✔ python                 ./.venv/Scripts/python.exe 3.12
  ✔ uv                     uv 0.10.7 (08ab1a344 2026-02-27)
  ✔ venv                   .venv presente
Arnés
  ✔ AGENTS.md              presente
  ✔ featureslist.json      presente
  ✔ current.md             presente
  ✔ history.md             presente
  ✔ subagentes             lider, implementer, reviewer, explorer
Backlog
  ✔ featureslist           27 features · 17 pending · 1 in_progress · 9 done · 0 blocked
  ✔ siguiente tarea        F1-002 — Arbol de conocimiento con progresion y origen de nodo [in_progress]
Proyecto
  ✔ paquete                tribal/ presente (project.yml)
  ✔ pyproject              presente
  ✔ tests                  12 ficheros de test
Verificación
  ✔ pytest                 102 passed in 8.22s
━━ ENTORNO LISTO ━━  0 aviso(s)
```

`uv run python -m agents --json run harness gate`:

```
success: true
message: "ENTORNO LISTO — se puede trabajar."
data: {"ready": true, "errors": 0, "warnings": 0, ...}
```

## Qué falta

- Persistencia: `store` con `nodos`/`aristas` en SQLite y `report culture --db` (F1-003).
- Prácticas de fuego, lenguaje y roles: en F1 solo la lítica progresa (`comer` + `recolectar`);
  el resto del árbol existe pero nadie lo recorre todavía.
- `apagar()`/decaimiento de nodos: no hay transmisión aún, así que nadie pierde un nodo.
- No bloqueantes del reviewer que quedan fuera de esta ronda: `nodos` público (hueco 6),
  `avanzar` con nodos apagados (8) y el tamaño de `build_parser` (7).
