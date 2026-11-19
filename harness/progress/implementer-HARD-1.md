# implementer · HARD-1

- **Fecha:** 2026-11-19
- **Veredicto:** ok

## Qué cambié

- `tribal/sim.py` — `Simulacion.muestra()` (una fila de telemetría) y
  `run_muestreado()` (corre y muestrea cada intervalo; el último tramo puede ser
  parcial).
- `tribal/cli.py` — subcomando `report telemetry` con `--seed`, `--ticks`,
  `--intervalo`, `--config`, `--crisis` y `--json`; tabla legible sin `--json`.
- `tests/test_telemetria.py` — 10 muestras para 600/60, primera y última contra
  el resumen, tabla legible y determinismo.
- `tests/test_semillas.py` — parametrizado con las semillas 1..10: dos
  subprocesos byte a byte + resumen de `Simulacion` en proceso.
- `tests/test_puerta_f1.py` — la lista blanca de `temperamento()` admite
  `sim.muestra` (cuenta temperamentos para telemetría; no decide conducta).
- `README.md` — estado tras Fase 1, sección de `report telemetry`, ejemplos
  actualizados de `run`/`report culture` y título de la puerta F1-006.
- `vault/01_PROYECTO/arquitectura.md` — §9 con lo que existe tras Fase 1, los
  comandos, lo que falta (LLM/persistencia) y §9.3 renombrada a F1-006; §10 con
  las referencias nuevas.

## Criterios de aceptación

1. **10 semillas reproducen su resumen exacto.**
   `uv run pytest tests/test_semillas.py -q` → `10 passed in 15.00s`.
   Cada semilla lanza dos `python -m tribal run --headless --json --ticks 600
   --seed N` y exige `stdout` idéntico byte a byte; además compara la línea con
   `run(600, N, headless=True).resumen()` serializado.
2. **`report telemetry --json` por intervalo.**
   `uv run python -m tribal report telemetry --json --seed 42 --ticks 600 --intervalo 60`
   devuelve `seed`, `ticks`, `intervalo`, `crisis` y 10 `muestras` con `tick`,
   `poblacion`, `divergentes`, `conformistas`, `neutros`, `nodos`, `aristas`,
   `media_energia` y `media_sed`. Salida literal abajo.
3. **README y arquitectura al día.**
   README: «Estado tras Fase 1», «Telemetría por intervalo», ejemplos de
   `run`/`report culture` recalculados con el motor actual y puerta F1-006.
   Arquitectura §9: estado real (core, agents, culture, sim, ui, gate_f1),
   comandos, y lo que falta (llm/store); §10 con README e implementer-F1-006.
   Los números pegados se ejecutaron antes de escribirlos.
4. **Puerta en verde.**
   `uv run python -m agents --json run harness gate` → `success: true`,
   `ready: true`, `errors: 0`, `warnings: 0`; `./init.sh` → `ENTORNO LISTO`.

## Evidencia

`uv run pytest -q`:

```
........................................................................ [  8%]
........................................................................ [ 17%]
........................................................................ [ 26%]
........................................................................ [ 34%]
........................................................................ [ 43%]
........................................................................ [ 52%]
........................................................................ [ 61%]
........................................................................ [ 69%]
........................................................................ [ 78%]
...................................s.ssssssssssss..s.................... [ 87%]
........................................................................ [ 96%]
.................................                                        [100%]
811 passed, 15 skipped in 223.66s (0:03:43)
```

`uv run ruff check tribal/ tests/ agents/` → `All checks passed!`

`uv run ruff format --check tribal/ tests/` → `49 files already formatted`

`uv run mypy tribal/ tests/` → `Success: no issues found in 49 source files`

`uv run pytest tests/test_semillas.py -q`:

```
..........                                                               [100%]
10 passed in 15.00s
```

`uv run pytest tests/test_telemetria.py -q`:

```
....                                                                     [100%]
4 passed in 2.37s
```

`uv run python -m tribal report telemetry --json --seed 42 --ticks 600 --intervalo 60`:

```
{"seed": 42, "ticks": 600, "intervalo": 60, "crisis": false, "muestras": [{"tick": 60, "poblacion": 12, "divergentes": 3, "conformistas": 7, "neutros": 2, "nodos": 15, "aristas": 12, "media_energia": 75.56, "media_sed": 20.6}, {"tick": 120, "poblacion": 12, "divergentes": 3, "conformistas": 7, "neutros": 2, "nodos": 23, "aristas": 20, "media_energia": 71.49, "media_sed": 30.32}, {"tick": 180, "poblacion": 12, "divergentes": 3, "conformistas": 7, "neutros": 2, "nodos": 23, "aristas": 20, "media_energia": 69.2, "media_sed": 40.03}, {"tick": 240, "poblacion": 12, "divergentes": 3, "conformistas": 7, "neutros": 2, "nodos": 23, "aristas": 20, "media_energia": 70.71, "media_sed": 49.74}, {"tick": 300, "poblacion": 12, "divergentes": 3, "conformistas": 7, "neutros": 2, "nodos": 23, "aristas": 20, "media_energia": 66.88, "media_sed": 59.46}, {"tick": 360, "poblacion": 12, "divergentes": 3, "conformistas": 7, "neutros": 2, "nodos": 23, "aristas": 20, "media_energia": 56.78, "media_sed": 58.2}, {"tick": 420, "poblacion": 14, "divergentes": 3, "conformistas": 8, "neutros": 3, "nodos": 24, "aristas": 21, "media_energia": 65.89, "media_sed": 29.18}, {"tick": 480, "poblacion": 14, "divergentes": 3, "conformistas": 8, "neutros": 3, "nodos": 24, "aristas": 21, "media_energia": 60.66, "media_sed": 33.85}, {"tick": 540, "poblacion": 15, "divergentes": 3, "conformistas": 8, "neutros": 4, "nodos": 30, "aristas": 27, "media_energia": 63.59, "media_sed": 26.91}, {"tick": 600, "poblacion": 16, "divergentes": 3, "conformistas": 8, "neutros": 5, "nodos": 30, "aristas": 27, "media_energia": 75.23, "media_sed": 34.51}]}
```

`./init.sh` (Git Bash; `make` no está instalado en esta máquina, así que los
targets se ejecutaron como sus comandos equivalentes):

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
  ✔ featureslist           43 features · 21 pending · 1 in_progress · 18 done · 3 blocked
  ✔ siguiente tarea        HARD-1 — Endurecimiento tras Fase 1: semilla, telemetria y docs [in_progress]

Proyecto
  ✔ paquete                tribal/ presente (project.yml)
  ✔ pyproject              presente
  ✔ tests                  22 ficheros de test

Verificación
  ✔ pytest                 255 passed in 151.88s (0:02:31)

━━ ENTORNO LISTO ━━  0 aviso(s)
Puedes trabajar. Siguiente paso: lee harness/progress/current.md y elige la primera feature pendiente.
```

`uv run python -m agents --json run harness gate`:

```
{
  "success": true,
  "agent": "harness",
  "action": "gate",
  "message": "ENTORNO LISTO — se puede trabajar.",
  "data": {
    "ready": true,
    "errors": 0,
    "warnings": 0,
    ...
    "checks": [
      ...
      {"status": "ok", "check": "pytest", "detail": "255 passed in 154.22s (0:02:34)"}
    ]
  },
  "warnings": [],
  "needs": []
}
```

## Qué falta

- Nada bloqueante. No se commiteó nada, no se tocaron `harness/featureslist.json`
  ni `harness/progress/` a mano (solo el `record` de este informe).
- `make` no está disponible en el PATH de esta máquina; lint/format/typecheck y
  la suite se ejecutaron con sus comandos `uv` equivalentes y `init.sh` con Git
  Bash.
