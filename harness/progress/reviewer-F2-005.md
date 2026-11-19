# reviewer · F2-005

- **Fecha:** 2026-11-19
- **Veredicto:** aprobado

## Ronda 2 — bloqueante de la ronda 1 resuelto

El bloqueante era que `Diario.ultimas(n)` devolvía `entradas[-n:]` y un diálogo
asíncrono podía anotarse con un tick anterior al último hito. Ahora `ultimas`
ordena por `tick` con `sorted` estable y corta las `n` mayores; `resumen()` y
`report diary` usan esa misma vista. El append no se toca (sigue siendo el
hecho de llegada).

Verificado por el reviewer, no solo por el test:

```
Diario: registrar(5, primer_fuego); registrar(1, dialogo)
  append          -> [5, 1]
  ultimas(2)      -> [1, 5]
  ultimas(1)      -> [5]
  empates (7,7)   -> primer_fuego, primera_tradicion (orden de llegada)

Cola asíncrona real (transporte 200 ms), hito en tick 5 y decisión en tick 1:
  append              -> [5, 1]
  ultimas(2)          -> [1, 5]
  resumen()["diario"]["ultimas"] -> [1, 5]
```

`report diary --last 5` sale ordenado y legible: ticks 2, 6, 12, 13, 86; con
`--llm stub --llm-sincrono` las cinco narradas. `test_report_diary_ordena_una_serie_desordenada`
fija la vista de la CLI.

## Criterios

1. **Cumplido.** El diario registra tick, tipo y texto de los hitos, conectado
   al motor. Los hitos ahora se atan al nodo que representa el hecho
   (`HITO_POR_NODO`): `observar_rayo`→`primer_fuego`,
   `proto_palabras`→`primera_palabra`, `ritual`→`primer_rito`,
   `caza_cooperativa`→`primera_caza_grupo`. En la corrida real (600 ticks,
   semilla 42) los ticks de las entradas coinciden con los del grafo: fuego 2,
   rito 6, caza 13, palabra 86. La muerte de anciano sigue igual
   (`edad >= UMBRAL_ANCIANO`), verificada en la ronda 1 (44 entradas en 8000
   ticks, primera en 1818).
2. **Cumplido.** El texto se guarda literal (sin `strip`), el fallo del
   transporte deja `texto=""`/`narrada=false`, y no bloquea: el test de 400 ms
   pasa y mi comprobación independiente da `mundo.tick == 10`,
   `ms_tick_medio = 0.16` (< 16.67) y `en_vuelo >= 1`. La pérdida de frases en
   asíncrono sigue siendo best-effort y ahora está cuantificada en el README.
3. **Cumplido.** Backend falso: cada hito deja entrada y el diálogo se asocia a
   su individuo; el contador `dialogos` de `resumen()` cuadra.
4. **Cumplido.** `report diary --json --last 5` imprime 5 entradas con todos los
   campos, en orden de tick, determinista; sin `--json` es legible.
5. **Cumplido.** Gate en verde (abajo).

## `primera_palabra` y `primer_rito`

Ya no se disparan con `gestos` ni con `arte_rupestre`. Verificado forzando la
rutina: tras el primer `hablar` no hay entrada; tras el segundo
(`proto_palabras`) aparece `primera_palabra` con el tick del nodo. Igual con
`pintar`: sin entrada tras `arte_rupestre`, `primer_rito` tras `ritual`. En la
corrida real, `gestos` (85) < `proto_palabras` (86) y `arte_rupestre` (3) <
`ritual` (6), y las entradas caen en 86 y 6.

## Evidencia ejecutada por el reviewer

```
uv run python -m agents --json run harness gate
  success=true · ready=true · errors=0 · warnings=0
  pytest: 368 passed in 178.06s (0:02:58)

uv run python -m pytest -q --no-header
  924 passed, 15 skipped in 244.23s (0:04:04)

uv run python -m pytest tests/test_diario.py -q
  17 passed in 4.13s

uv run ruff check tribal/ tests/          → All checks passed!
uv run ruff format --check tribal/ tests/ → 70 files already formatted
uv run mypy tribal/ tests/                → Success: no issues found in 70 source files
uv run python -m tribal run --headless --ticks 600 --benchmark
  benchmark: 0.66 ms/tick, cabe en 16.67 ms
uv run python -m agents --json run review review_package → sin hallazgos en diario.py
uv run python -m agents --json run secrets scan → solo fixtures de agents/tests (preexistentes)
```

Alcance: `opencode.json` limpio (`git status` no lo lista y no contiene
`pixellab`/`Bearer`/`mcp`); `docs/art` no aparece en el diff de la feature; sin
dependencias nuevas, sin canales de fitness, sin `.tmp-*`.

## No bloqueante

- El docstring de la clase `Diario` sigue diciendo "append-only ... en orden de
  tick"; el de `ultimas` ya explica que el append puede no serlo. Corregir esa
  línea evita que el próximo lector asuma la garantía vieja.
- `ultimas` ordena toda la lista en cada llamada; con decenas de entradas es
  irrelevante, pero si el diario crece conviene insertar ordenado o cachear.
- Fuera de esta feature: en plena ronda apareció el commit `8395353` ("kit de
  pixel art") con `docs/art/` y una entrada `ART-001` en
  `harness/featureslist.json`. No está en el diff de F2-005 y no debe mezclarse
  en su commit.
