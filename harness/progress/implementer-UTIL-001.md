# implementer · UTIL-001

- **Fecha:** 2026-11-18
- **Veredicto:** ok

# implementer · UTIL-001

- **Fecha:** 2026-11-18
- **Veredicto:** ok

# UTIL-001 — Utilidad situacional, no multiplicadores fijos

## Qué cambié

- `tribal/culture/beneficios.py`: la utilidad de cada combinación deja de ser un
  multiplicador fijo. Nuevo `Situacion` (escasez por `TipoRecurso` + gancho
  `estacion`), `escasez_de`, `situacion`, `portadores`, `utilidad`,
  `utilidades`, `conocidos` y `activos` situacionales. `EFECTOS` pasa a ser el
  efecto **nominal** (el de recurso agotado). Valida al importar que cada
  combinación afecta a una sola dimensión y que tiene recurso y habilidad.
- `tribal/sim.py`: calcula `situacion`/`utilidades` una vez por tick, compone el
  beneficio por individuo con ellas, aplica el daño del depredador desde ese
  mismo mapa y acumula `utilidad_media` por nodo. `resumen` publica
  `utilidad_media` y `Situacion.a_json()` (`escasez`, `estacion`). Sin rastro de
  temperamento: solo habilidades y estado.
- `tribal/core/acciones.py`: `comer` documenta que los bonus que recibe son la
  utilidad situacional (el cableado vive en `sim`+`beneficios` para no invertir
  la capa `core → culture`). Sin cambio de comportamiento.
- `tests/test_utilidad.py` (nuevo): 5 tests (utilidad vs escasez/densidad,
  medida de escasez, calma vs crisis a 5 semillas, telemetría del resumen,
  independencia del temperamento).
- `tests/test_divergencia.py`, `tests/test_divergencia_calma.py`: los escenarios
  de "el bonus es igual para quien la sabe" pasan a tener escasez real; en
  abundancia la utilidad vale 1.0 y ya no hay bonus que comparar.
- `tests/test_cli_run.py`: el contrato de claves del resumen incluye
  `utilidad_media`, `escasez` y `estacion`.
- `README.md`: tabla de efectos nominales + recurso, cómo se interpola la
  utilidad, densidad de portadores, campos nuevos del resumen y JSON de ejemplo.

Diseño de la utilidad (`utilidad = 1 + efecto_nominal_desviado · escasez · densidad`):

- `escasez = 1 − Σcantidad / Σcapacidad` por tipo, acotada a [0,1]; sin fuentes
  del tipo vale 0 (no hay oportunidad que explotar).
- `densidad = 1 / (1 + 0.1 · portadores)`; documentado como utilidad de
  oportunidad, no de rasgo.
- `estacion: str | None` en `Situacion`, hoy siempre `None`; se conectará en
  AMB-001 sin cambiar la interfaz. Publicada en el resumen.
- Recurso por nodo: raedera→bayas; cuchillo/cacería/vigilia→caza; canto→agua.

## Criterios de aceptación

1. **La utilidad depende del estado del mundo.**
   `uv run pytest -q tests/test_utilidad.py::test_la_utilidad_crece_con_la_escasez_y_baja_con_los_portadores tests/test_utilidad.py::test_la_escasez_es_la_fraccion_que_falta_sobre_la_capacidad`
   → 2 passed. Lleno = 1.0; agotado con 1 portador = 1.2273 (raedera) y 0.5455
   (vigilia); con 10 y 20 portadores baja monótonamente.
2. **Misma semilla: calma no mueve, crisis sí.**
   `uv run pytest -q tests/test_utilidad.py::test_en_calma_el_invento_no_mueve_la_energia_y_en_escasez_si`
   → passed. Tabla de 5 semillas (media de energía de 3000 ticks, un adulto,
   agua de sobra, sin depredadores; brazo A reserva de bayas llena y con
   regeneración, brazo B 25/100 sin regenerar → escasez 0.75):

   ```
   seed | calma sin/con/dif | crisis sin/con/dif
      1 |  61.42  61.42  +0.00 |  61.42  63.37  +1.95
      2 |  59.79  59.79  +0.00 |  59.79  64.42  +4.63
      3 |  60.71  60.71  +0.00 |  60.71  63.29  +2.58
      4 |  59.80  59.80  +0.00 |  59.80  62.71  +2.90
      5 |  60.28  60.28  +0.00 |  60.28  64.82  +4.53
   media|                +0.00 |                +3.32
   ```

   Umbral del test: |dif| < 0.1 en calma (la utilidad es exactamente 1.0, así
   que 0.1 es solo redondeo), dif > 0.5 por semilla y media > 1.5 en crisis
   (mínimo medido 1.95, media 3.32). Se mide media de energía y no
   supervivencia porque el escenario controlado no tiene depredador ni vejez:
   ambos brazos sobreviven, y lo que el mecanismo mueve es la energía.
3. **Resumen con `utilidad_media` y el estado que la modula.**
   `uv run pytest -q tests/test_utilidad.py::test_el_resumen_publica_utilidad_media_y_el_estado_que_la_modula`
   → passed. En calma `utilidad_media.raedera == 1.0`; con escasez 0.75,
   `== 1.0 + 0.25·0.75/1.1`, `escasez == {agua: 0.0, bayas: 0.75, caza: 0.0}`,
   `estacion is None`. Partida real de 5000 ticks en crisis:
   ```json
   {"utilidad_media": {"cuchillo_al_fuego": 1.0638, "canto_ritual": 0.9756,
     "turnos_de_vigilia": 0.8245, "raedera": 1.0868, "caceria_dirigida": 1.19},
    "escasez": {"agua": 0.5, "bayas": 0.833, "caza": 0.688}, "estacion": null}
   ```
4. **La utilidad no depende del temperamento.**
   `uv run pytest -q tests/test_utilidad.py::test_la_utilidad_no_depende_del_temperamento`
   → passed: divergencia 0.1 y 0.9, misma habilidad y mismo mundo, misma
   energía y mismo multiplicador (> 1.0). No hay ninguna lectura de
   `divergencia` en `beneficios.py`, así que el guard de DIVERGENCIA-002
   (`tests/test_divergencia_calma.py::test_el_rasgo_solo_se_lee_donde_es_conducta`)
   sigue en verde.
5. **Suite y puerta.**
   `uv run pytest -q` → `715 passed, 15 skipped in 111.00s`.
   `make` no existe en este shell de Windows; se ejecutan los mismos comandos
   del Makefile: `uv run ruff check tribal/ tests/ agents/` → All checks passed;
   `uv run ruff format --check tribal/ tests/` → 44 files already formatted;
   `uv run mypy tribal/ tests/` → Success: no issues found in 44 source files.
   `bash` tampoco existe, así que la puerta se ejecuta por su ruta de código:
   `uv run python -m agents --json run harness gate` → `success: True`, 14
   checks en `ok`, `pytest | 186 passed in 48.95s`.

## Evidencia

```
$ uv run pytest -q
........................................................................ [ 98%]
.........                                                                [100%]
715 passed, 15 skipped in 111.00s

$ uv run ruff check tribal/ tests/ agents/
All checks passed!

$ uv run ruff format --check tribal/ tests/
44 files already formatted

$ uv run mypy tribal/ tests/
Success: no issues found in 44 source files

$ uv run python -m agents --json run harness gate
success: True
- ok python | ./.venv/Scripts/python.exe 3.12
- ok uv | uv 0.10.7 (08ab1a344 2026-02-27)
- ok venv | .venv presente
- ok AGENTS.md | presente
- ok featureslist.json | presente
- ok current.md | presente
- ok history.md | presente
- ok subagentes | lider, implementer, reviewer, explorer
- ok featureslist | 41 features · 24 pending · 1 in_progress · 14 done · 2 blocked
- ok siguiente tarea | UTIL-001 — Utilidad situacional: el invento vale segun el estado [in_progress]
- ok paquete | tribal/ presente (project.yml)
- ok pyproject | presente
- ok tests | 18 ficheros de test
- ok pytest | 186 passed in 48.95s
```

## Qué falta

- La estación/clima es un gancho (`estacion=None`, sin efecto): se conecta en
  AMB-001. `Situacion` y el resumen ya la publican.
- La densidad de portadores usa solo "sabe la habilidad"; cuando la transmisión
  sesgada por prestigio (eje 2) exista, puede afinarse con prestigio, pero el
  contrato de utilidad no cambia.
- `make`/`bash` no existen en este entorno Windows; la puerta se verificó con
  `harness gate` (misma ruta que usa `init.sh`). No se commiteó nada.

## Corrección del no bloqueante del reviewer (README)

- Regenerada la línea JSON de 600 ticks con la salida real de
  `uv run python -m tribal run --headless --ticks 600 --json` (seed 42):
  `poblacion_final 13, nacimientos 1, media_energia 66.58, media_sed 37.26,
  imitaciones 522`, `utilidad_media {}`,
  `escasez {agua 0.0, bayas 0.179, caza 0.312}`, `estacion null`. La línea
  parsea como JSON (37 claves).
- Revisada la sección: también estaban caducos el bloque `--benchmark` (ahora
  `ataques 2, agrupamiento max 9, huidas 160, media energia 44.62, media sed
  43.56` y `0.52 ms/tick`) y dos conteos de los ejemplos de 5000 ticks
  (`intentos_divergentes 15 -> 8` en crisis; `interaccion 4 -> 5` en calma).
- `uv run pytest -q` -> `715 passed, 15 skipped in 113.59s`.
- `uv run python -m agents --json run harness gate` -> `success: True`,
  `pytest | 186 passed in 52.29s`.
