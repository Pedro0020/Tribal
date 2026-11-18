# implementer · F1-003

- **Fecha:** 2026-11-18
- **Veredicto:** ok

## Qué cambié

- `tribal/core/genoma.py` — `temperamento()` y umbrales 0.6/0.4: el rasgo `divergencia` clasifica divergente / neutro / conformista.
- `tribal/culture/combinaciones.py` (nuevo) — catálogo de 5 cruces plausibles (`raedera`, `cuchillo_al_fuego`, `canto_ritual`, `caceria_dirigida`, `turnos_de_vigilia`), con sus dos requisitos, rama y origen `combinacion`; validados al importar.
- `tribal/culture/grafo.py` — descubre también nodos de `COMBINACIONES`, fuerza `origen="combinacion"` y añade `ultimo_activo()`, `veces_usado` e `imitado` (transmisión por imitación).
- `tribal/core/recursos.py` — `regenerar(..., penalizacion)` espacia agua y bayas durante la sequía.
- `tribal/config.py` — `crisis: bool` y `sequia_ticks: int >= 0`, con validación.
- `tribal/sim.py` — sequía (regeneración ×0.5, sed ×1.25), intentos de cruce solo de divergentes en crisis (consumen tick, pueden fallar), práctica registrada siempre para contar imitaciones y nuevos contadores en `resumen()`.
- `tribal/cli.py` — `run --crisis`.
- `tests/test_divergencia.py` (nuevo) — 11 tests: clasificación, catálogo, imitación, crisis con nodos nuevos, calma sin ellos, origen inmutable, validación, CLI y determinismo entre procesos.
- `tests/test_config.py`, `tests/test_cli_run.py` — esquemas actualizados con las claves nuevas.
- `docs/config-ejemplo.json`, `README.md` — `crisis`/`sequia_ticks`, sección de divergentes y conformistas y salida real.

## Criterios de aceptación

1. **La divergencia es un rasgo del genoma y decide quién experimenta y quién imita.**
   `Genoma.divergencia` + `temperamento()`; solo `divergente` entra en `_intentar_combinacion()` y solo `conformista` suma en `Grafo.imitado`.
   Evidencia: `test_el_genoma_decide_quien_experimenta_y_quien_imita` y `test_el_conformista_que_usa_un_nodo_ajeno_cuenta_como_imitacion`.

2. **Los conformistas copian nodos que ven funcionar y los divergentes intentan combinaciones.**
   `Grafo.registrar_uso()` cuenta `veces_usado`/`imitado`; `_intentar_combinacion()` elige un cruce con sus dos nodos activos y puede fallar.
   Evidencia: los dos tests anteriores y `test_el_origen_de_una_combinacion_es_inmutable`.

3. **En crisis suben los intentos divergentes y aparecen nodos nuevos.**
   `uv run python -m tribal run --headless --json --ticks 5000 --crisis --seed 42` →
   `intentos_divergentes: 2`, `combinaciones_logradas: 1`, `nodos_por_origen.combinacion: 1`, nodo `raedera` con `origen: "combinacion"`.

4. **Sin crisis no aparecen.**
   Mismo comando sin `--crisis` →
   `intentos_divergentes: 0`, `combinaciones_logradas: 0`, `nodos_por_origen.combinacion: 0`, y todos los nodos con `origen: "arbol"`.

5. **`run --headless --json --ticks 5000` reporta n_divergentes, n_conformistas y nodos por origen.**
   La salida de crisis incluye `n_divergentes: 4`, `n_conformistas: 2`, `n_neutros: 21`, `nodos_por_origen: {"arbol": 5, "combinacion": 1, "interaccion": 0, "llm": 0}`.

6. **`harness gate` success=true.**
   `uv run python -m agents --json run harness gate` → `success: true`, `data.ready: true`, `data.errors: 0`.

## Evidencia

### Crisis (literal)

```
uv run python -m tribal run --headless --json --ticks 5000 --crisis --seed 42
{"seed": 42, "ticks": 5000, "poblacion_inicial": 12, "poblacion_final": 27, "nacimientos": 38, "muertes": 23, "media_energia": 44.7, "media_sed": 40.84, "media_genes": {"velocidad": 0.986, "metabolismo": 1.069, "longevidad": 1.099, "fuerza": 1.038, "resistencia": 0.971, "inteligencia": 1.06, "salud": 1.002, "divergencia": 0.511}, "habilidades_distintas": 1, "habilidades": {"24": ["recolectar"], "25": ["recolectar"], "26": ["recolectar"], "27": ["recolectar"], "28": ["recolectar"], "29": ["recolectar"], "30": ["recolectar"], "31": ["recolectar"], "32": ["recolectar"], "33": ["recolectar"], "34": ["recolectar"], "35": ["recolectar"], "36": ["recolectar"], "37": ["recolectar"], "38": ["recolectar"], "39": ["recolectar"], "40": ["recolectar"], "41": ["recolectar"], "42": ["recolectar"], "43": ["recolectar"], "44": ["recolectar"], "45": ["recolectar"], "46": ["recolectar"], "47": ["recolectar"], "48": ["recolectar"], "49": ["recolectar"], "50": ["recolectar"]}, "individuos_movidos": 50, "depredador": {"activos": 1, "ataques": 6, "muertes": 2}, "agrupamiento_max": 11, "huidas": 985, "n_divergentes": 4, "n_conformistas": 2, "n_neutros": 21, "intentos_divergentes": 2, "combinaciones_logradas": 1, "imitaciones": 41, "nodos": [{"id": "guijarro", "rama": "litica", "nivel": 0, "titulo": "Guijarro", "origen": "arbol", "autor": 10, "tick": 254}, {"id": "lasca", "rama": "litica", "nivel": 1, "titulo": "Lasca", "origen": "arbol", "autor": 8, "tick": 260}, {"id": "bifaz", "rama": "litica", "nivel": 2, "titulo": "Bifaz", "origen": "arbol", "autor": 11, "tick": 307}, {"id": "punta_de_lanza", "rama": "litica", "nivel": 3, "titulo": "Punta de lanza", "origen": "arbol", "autor": 5, "tick": 314}, {"id": "raedera", "rama": "litica", "nivel": 3, "titulo": "Raedera", "origen": "combinacion", "autor": 7, "tick": 349}, {"id": "caza_cooperativa", "rama": "litica", "nivel": 4, "titulo": "Caza cooperativa", "origen": "arbol", "autor": 6, "tick": 315}], "aristas": [{"origen": "guijarro", "destino": "lasca"}, {"origen": "lasca", "destino": "bifaz"}, {"origen": "bifaz", "destino": "punta_de_lanza"}, {"origen": "punta_de_lanza", "destino": "caza_cooperativa"}, {"origen": "lasca", "destino": "raedera"}, {"origen": "bifaz", "destino": "raedera"}], "pct_fuera_arbol": 16.7, "nodos_por_origen": {"arbol": 5, "combinacion": 1, "interaccion": 0, "llm": 0}, "config": {"seed": 42, "individuos": 12, "ancho": 60, "alto": 34, "tasa_sed": 0.16, "tasa_energia": 0.15, "tasa_salud": 0.6, "cooldown_reproduccion": 600, "depredadores": 1, "depredador_activo": true, "crisis": true, "sequia_ticks": 0}}
```

### Sin crisis (literal)

```
uv run python -m tribal run --headless --json --ticks 5000 --seed 42
{"seed": 42, "ticks": 5000, "poblacion_inicial": 12, "poblacion_final": 54, "nacimientos": 67, "muertes": 25, "media_energia": 41.24, "media_sed": 39.1, "media_genes": {"velocidad": 1.007, "metabolismo": 1.09, "longevidad": 1.108, "fuerza": 1.05, "resistencia": 0.955, "inteligencia": 0.987, "salud": 1.007, "divergencia": 0.556}, "habilidades_distintas": 1, "habilidades": {"20": ["recolectar"], "26": ["recolectar"], "28": ["recolectar"], "29": ["recolectar"], "30": ["recolectar"], "31": ["recolectar"], "32": ["recolectar"], "33": ["recolectar"], "34": ["recolectar"], "35": ["recolectar"], "36": ["recolectar"], "37": ["recolectar"], "38": ["recolectar"], "39": ["recolectar"], "40": ["recolectar"], "41": ["recolectar"], "42": ["recolectar"], "43": ["recolectar"], "44": ["recolectar"], "45": ["recolectar"], "46": ["recolectar"], "47": ["recolectar"], "48": ["recolectar"], "49": ["recolectar"], "50": ["recolectar"], "51": ["recolectar"], "52": ["recolectar"], "53": ["recolectar"], "54": ["recolectar"], "55": ["recolectar"], "56": ["recolectar"], "57": ["recolectar"], "58": ["recolectar"], "59": ["recolectar"], "60": ["recolectar"], "61": ["recolectar"], "62": ["recolectar"], "63": ["recolectar"], "64": ["recolectar"], "65": ["recolectar"], "66": ["recolectar"], "67": ["recolectar"], "68": ["recolectar"], "69": ["recolectar"], "70": ["recolectar"], "71": ["recolectar"], "72": ["recolectar"], "73": ["recolectar"], "74": ["recolectar"], "75": ["recolectar"], "76": ["recolectar"], "77": ["recolectar"], "78": ["recolectar"], "79": ["recolectar"]}, "individuos_movidos": 79, "depredador": {"activos": 1, "ataques": 5, "muertes": 1}, "agrupamiento_max": 19, "huidas": 3580, "n_divergentes": 18, "n_conformistas": 3, "n_neutros": 33, "intentos_divergentes": 0, "combinaciones_logradas": 0, "imitaciones": 42, "nodos": [{"id": "guijarro", "rama": "litica", "nivel": 0, "titulo": "Guijarro", "origen": "arbol", "autor": 7, "tick": 263}, {"id": "lasca", "rama": "litica", "nivel": 1, "titulo": "Lasca", "origen": "arbol", "autor": 10, "tick": 272}, {"id": "bifaz", "rama": "litica", "nivel": 2, "titulo": "Bifaz", "origen": "arbol", "autor": 8, "tick": 279}, {"id": "punta_de_lanza", "rama": "litica", "nivel": 3, "titulo": "Punta de lanza", "origen": "arbol", "autor": 1, "tick": 313}, {"id": "caza_cooperativa", "rama": "litica", "nivel": 4, "titulo": "Caza cooperativa", "origen": "arbol", "autor": 12, "tick": 319}], "aristas": [{"origen": "guijarro", "destino": "lasca"}, {"origen": "lasca", "destino": "bifaz"}, {"origen": "bifaz", "destino": "punta_de_lanza"}, {"origen": "punta_de_lanza", "destino": "caza_cooperativa"}], "pct_fuera_arbol": 0.0, "nodos_por_origen": {"arbol": 5, "combinacion": 0, "interaccion": 0, "llm": 0}, "config": {"seed": 42, "individuos": 12, "ancho": 60, "alto": 34, "tasa_sed": 0.16, "tasa_energia": 0.15, "tasa_salud": 0.6, "cooldown_reproduccion": 600, "depredadores": 1, "depredador_activo": true, "crisis": false, "sequia_ticks": 0}}
```

### Tests

```
uv run pytest -q
642 passed, 15 skipped in 75.57s (0:01:15)
```

### Lint / typecheck

`make` no está instalado en esta máquina (PowerShell ni Git Bash lo encuentran); ejecuté los mismos comandos del Makefile:

```
uv run ruff check tribal/ tests/ agents/  ->  All checks passed!
uv run ruff format --check tribal/ tests/  ->  37 files already formatted
uv run mypy tribal/ tests/  ->  Success: no issues found in 37 source files
```

### init.sh

```
━━ init.sh · arnés de Tribal ━━
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
  ✔ featureslist           27 features · 16 pending · 1 in_progress · 10 done · 0 blocked
  ✔ siguiente tarea        F1-003 — Divergentes y conformistas: variacion y transmision [in_progress]
Proyecto
  ✔ paquete                tribal/ presente (project.yml)
  ✔ pyproject              presente
  ✔ tests                  13 ficheros de test
Verificación
  ✔ pytest                 113 passed in 15.09s
━━ ENTORNO LISTO ━━  0 aviso(s)
```

### Gate

```
uv run python -m agents --json run harness gate
"success": true, "message": "ENTORNO LISTO — se puede trabajar."
"data": {"ready": true, "errors": 0, "warnings": 0, ... "pytest": "113 passed in 15.08s"}
```

## Qué falta

Nada para los criterios de F1-003. El resto de combinaciones del catálogo espera a que
sus ramas (fuego, lenguaje, simbólico) tengan práctica que las descubra; hoy solo la
lítica avanza y por eso la demo crea `raedera` y no las demás. No commiteé ni cerré la
feature.

## Ronda 2 — B1: test que ancla «y quién imita»

- Añadidos en `tests/test_divergencia.py`: `test_ni_el_divergente_ni_el_neutro_suman_imitaciones` (autor divergente + usuario divergente + usuario neutro → `veces_usado == {"guijarro": 2}`, `imitado == {}`, `imitaciones == 0`) y `test_el_mismo_montaje_con_un_conformista_si_suma_imitacion` (mismo montaje con conformista → `imitado == {"guijarro": 1}`).
- Mutación M5 (quitar `es_conformista and` en `tribal/culture/grafo.py:84`): `uv run pytest -q -x` → `FAILED tests/test_divergencia.py::test_ni_el_divergente_ni_el_neutro_suman_imitaciones`; `1 failed, 51 passed, 1 skipped in 6.09s`.
- Mutación M3 (quitar `self.grafo.registrar_uso(...)` en `tribal/sim.py`): `uv run pytest -q -x` → `FAILED tests/test_divergencia.py::test_el_conformista_que_usa_un_nodo_ajeno_cuenta_como_imitacion`; `1 failed, 50 passed, 1 skipped in 3.07s`.
- Restaurado por hash SHA-256: `grafo.py=110371143F9BB61BBEF32B73B1BD85E532B56EC15F3F5479EA3B36E59DDE6948`, `sim.py=D14A46348F2EC7CBB0324C4E05C78C188333835962A0CFEA05BE068FC163E85D`.
- Verificación final: `pytest -q` → `644 passed, 15 skipped in 75.91s`; `ruff check` → `All checks passed!`; `ruff format --check` → `37 files already formatted`; `mypy` → `Success: no issues found in 37 source files`; `harness gate` → `success=True`, `ready=True`, `errors=0`, `pytest=115 passed`.
