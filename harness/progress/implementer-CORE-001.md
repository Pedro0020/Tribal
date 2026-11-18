# implementer · CORE-001

- **Fecha:** 2026-11-18
- **Veredicto:** ok

# CORE-001 - implementer, ronda 2 (2026-11-18, verdict ok)

## Que cambie

- tribal/cli.py: el resumen serializable ya no lleva ms_tick_medio; el JSON es solo el dict de sim.resumen(). El benchmark se imprime aparte, siempre por stderr, con el veredicto del presupuesto y el exit code 0/1 (_benchmark).
- tests/test_cli_run.py: CLAVES sin ms_tick_medio; nuevo test_dos_ejecuciones_json_dan_la_misma_salida (mismo comando --headless --json --ticks 300 dos veces, stdout byte-identico); el test de benchmark lee el ms de stderr con regex y exige < 16.67.
- tests/test_render.py: import de pygame a nivel de modulo y nuevo test_bucle_pinta_un_frame_por_tick: app.bucle(sim, ticks_max=5) deja sim.mundo.tick == 5 y al menos un frame pintado con >= 4 colores.
- README.md: la frase del genoma dice lo que hay (genoma minimo con velocidad y metabolismo, usados por necesidades y movimiento) y lo que falta (herencia y mutacion, Fase 1); el JSON de ejemplo ya no muestra ms_tick_medio; el benchmark aparece separado en stdout y stderr.
- docs/img/fase0.png sin tocar: el render no cambio.

## Criterios

1. BLOQUEANTE reproducibilidad: el JSON de --headless --json es determinista. Dos ejecuciones de --ticks 600 dan ficheros con el mismo hash SHA256; el test automatizado lo fija con --ticks 300.
2. NO BLOQUEANTE genoma: README corregido, describe el genoma minimo real y aplaza herencia/mutacion a F1.
3. NO BLOQUEANTE app.py: test de bucle real con driver dummy; comprobado por mutacion que duplicar simulacion.step() lo tumba (assert 10 == 5) y que el fichero restaurado no deja diff.
4. Benchmark: imprime ms/tick y veredicto por stderr y el exit code sigue siendo 0; el JSON sigue sin campos de reloj de pared.

## Evidencia

uv run python -m tribal run --headless --json --ticks 600   (dos veces, salida identica, hash igual)
    {'seed': 42, 'ticks': 600, 'poblacion_inicial': 12, 'poblacion_final': 12,
     'nacimientos': 0, 'muertes': 0, 'media_energia': 66.62, 'media_sed': 42.32,
     'individuos_movidos': 12}
    identicos=True (Get-FileHash de los dos ficheros)

uv run python -m tribal run --seed 7 --benchmark --headless --ticks 600   (exit 0)
    stdout:
    seed 7  ticks 600  poblacion 12 -> 12
    muertes 0  nacimientos 0  individuos movidos 12
    media energia 40.85  media sed 38.25
    stderr:
    benchmark: 0.24 ms/tick, cabe en 16.67 ms

uv run pytest tests -q
    25 passed in 1.42s

uv run ruff check tribal/ tests/
    All checks passed!

uv run ruff format --check tribal/ tests/
    22 files already formatted

uv run mypy tribal/ tests/
    Success: no issues found in 22 source files

uv run python -m agents --json run harness gate
    exit 0, success=true, message: ENTORNO LISTO, 0 errores, 0 warnings

## Que falta

- harness/progress/reviewer-CORE-001.md esta truncado a partir de la linea 45 (el texto guardado acaba en uv run python -c import); apliquÃ© los tres puntos del encargo, pero el informe del reviewer no se lee entero.
- Sigue pendiente lo ya declarado en la ronda 1: nacimientos a 0, extincion solo demostrable en tests o con un mundo sin recursos, y __version__ 0.1.1 frente a 0.1.3 (bug previo).
