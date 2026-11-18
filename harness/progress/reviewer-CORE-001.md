# reviewer · CORE-001

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

# CORE-001 - revision independiente, ronda 2 (reviewer)

Fecha: 2026-11-18

## Puerta (ejecutada en esta sesion)

    uv run python -m agents --json run harness gate
    success=true | errors=0 | warnings=0 | pytest 25 passed in 1.44s | exit 0

## Bloqueante de la ronda 1: resuelto

1. 'run --json' reproducible.
   - Dos corridas identicas de 'uv run python -m tribal run --headless --json --ticks 600':
     {seed: 42, ticks: 600, poblacion_inicial: 12, poblacion_final: 12, nacimientos: 0, muertes: 0, media_energia: 66.62, media_sed: 42.32, individuos_movidos: 12}
     {seed: 42, ticks: 600, poblacion_inicial: 12, poblacion_final: 12, nacimientos: 0, muertes: 0, media_energia: 66.62, media_sed: 42.32, individuos_movidos: 12}
     IDENTICOS=True, ambas de 176 bytes. Ya no aparece ms_tick_medio.
   - Seed distinta sigue dando otra cosa: seed 7 -> media_energia 40.85, media_sed 38.25.
   - El reloj de pared sale solo con --benchmark y por stderr:
     'uv run python -m tribal run --seed 7 --benchmark --headless --ticks 600' imprime el
     resumen por stdout y 'benchmark: 0.23 ms/tick, cabe en 16.67 ms' por stderr, exit 0.
   - cli.py:75 ya no toca el dict; _benchmark() escribe siempre en stderr.
   - Test nuevo: test_dos_ejecuciones_json_dan_la_misma_salida compara dos salidas completas.
     CLAVES actualizado sin ms_tick_medio. test_benchmark exige que 'ms_tick_medio' NO este
     en stdout y que el veredicto este en stderr.
   - README: el JSON pegado coincide byte a byte con el de hoy y no tiene ms; la linea del
     benchmark sale marcada como stderr y avisa de que varia unas centesimas. La frase falsa
     del genoma se sustituyo por la real (genoma minimo de velocidad y metabolismo, herencia
     en Fase 1), que es lo que hace modelos.Genoma.

## Criterios (regresion)

1. CUMPLIDO - captura nueva con dummy (seed 1, 10 individuos, 120 ticks): Surface (480, 286),
   19 colores, HUD 'tick 120  pob 10  energia 70  sed 28', mapa con 3 lagos, bosques e
   individuos visibles. Coincide con docs/img/fase0.png.
2. CUMPLIDO - 'run --seed 2 --ticks 3000 --headless --json' -> poblacion_final 11, muertes 1,
   exit 0. Tests de muerte y de extincion intactos.
3. CUMPLIDO - app.bucle con SDL dummy: 120 frames en 1.960 s -> 61.2 fps, mundo.tick=120.
   Clock.tick(60) y un unico sim.step() por frame siguen en app.py.
4. CUMPLIDO - 'import tribal.sim' -> pygame en sys.modules = False. test_motor sin pygame.
5. CUMPLIDO - ruff check All checks passed | ruff format 22 files already formatted |
   mypy 22 files no issues | pytest 25 passed | gate success=true. Todos exit 0.
6. CUMPLIDO - comandos reales, JSON y resumen identicos a la salida de hoy, sin numeros que
   caduquen.

## Test del bucle: comprobado por mutacion

- tests/test_render.py::test_bucle_pinta_un_frame_por_tick hace app.bucle(sim, ticks_max=5) y
  afirma simulacion.mundo.tick == 5, ademas de que se haya pintado y que el frame tenga 4+
  colores.
- Lo he verificado rompiendolo a proposito: inserte un segundo simulacion.step() y el test
  cae con 'assert 10 == 5'. Despues restaure el fichero a su contenido original (1319 bytes,
  LF), y la suite vuelve a 25 passed con ruff y mypy limpios.

## No bloqueante

- Con ticks_max el bucle retorna antes de pintar el ultimo frame: 5 ticks -> 4 blits. El test
  solo exige que pintados no este vacio, asi que no distingue N de N-1. Irrelevante para la
  partida real (ticks_max=0); el nombre del test promete un poco mas de lo que comprueba.
- README pega 'benchmark: 0.24 ms/tick' y hoy sale 0.23: el propio texto avisa de que varia
  unas centesimas, asi que no caduca como antes.
- tribal/__init__.py 0.1.1 vs pyproject 0.1.3: preexistente, toca en QA-001.
- La extincion sigue sin ser alcanzable por CLI con el mapa normal (solo test y mundo sin
  recursos). Documentado y aceptable en Fase 0.
- El benchmark (0.2x ms frente a 16.67) no puede fallar hoy: no sirve como alarma de
  regresion de rendimiento, solo como evidencia de que cabe.

## Alcance

git status --short sin cambios respecto a la ronda 1: README.md, pyproject.toml, uv.lock,
tribal/cli.py, harness/ (solo via agente) y nuevos tribal/{core,agents,ui}, tribal/sim.py,
tests/*, docs/img. agents/ intacto, sin .tmp-*, sin __pycache__ trackeable, sin sqlite ni LLM.
