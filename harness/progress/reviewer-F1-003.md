# reviewer · F1-003

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

## Criterios (re-verificados en esta sesión)

**1. La divergencia es un rasgo del genoma y decide quién experimenta y quién imita — CUMPLIDO (B1 cerrado).**
`Genoma.divergencia` (0–1, herencia media + mutación 5 %), `temperamento()` con umbrales 0.6/0.4, y los neutros ni intentan ni imitan.
Lado «quién imita»: los dos casos hermanos existen en `tests/test_divergencia.py` (13 tests recogidos) y son correctos —
`test_ni_el_divergente_ni_el_neutro_suman_imitaciones` (autor divergente + otro divergente + neutro → `veces_usado == {"guijarro": 2}`, `imitado == {}`, `imitaciones == 0`) y
`test_el_mismo_montaje_con_un_conformista_si_suma_imitacion` (mismo montaje con conformista → `imitado == {"guijarro": 1}`). La aserción clave es la negativa: el divergente usuario cuenta uso pero no transmisión, que es justo lo que el mutante rompía.
Sonda directa independiente: autor div. 0.9 + usuario div. 0.9 + neutro 0.5 → `imitado {}`, `imitaciones 0`; con conformista 0.1 → `imitado {"guijarro": 1}`.
Lado «quién experimenta»: solo los divergentes pueden intentar (la probabilidad es proporcional a `divergencia - 0.6`, negativa por debajo del umbral).

**2. Conformistas imitan; divergentes combinan — CUMPLIDO.**
5 cruces con 2 requisitos existentes en `ARBOL`, ningún id colisionando, validados al importar. `descubrir` fuerza `origen="combinacion"` y valida prerrequisitos (sin los dos nodos activos → `PrerequisitoFaltante`); `origen` inmutable (`frozen` + idempotente). Contadores reales: seed 42 en calma, 600 ticks → `veces_usado {'caza_cooperativa': 7}` / `imitado 3`; 1500 ticks → `46 / 12`. Crecen, no son flags.

**3. En crisis suben los intentos y aparecen nodos nuevos — CUMPLIDO.**
Barrido de 10 semillas con `--crisis --ticks 5000`: 9/10 con un nodo `combinacion` (`raedera`), 15 intentos en total. Seed 42: 2 intentos, 1 combinación, `raedera` en tick 349. La única sin intentos (11) se extingue (población 0).

**4. Sin crisis no aparecen — CUMPLIDO y robusto.**
10/10 semillas sin `--crisis`: 0 intentos, 0 combinaciones, 50/50 nodos con `origen="arbol"`. Idéntico al barrido de la ronda 1 y coherente con el gate `_en_crisis()`.

**5. `run --headless --json --ticks 5000` reporta los contadores — CUMPLIDO.**
`n_divergentes 4`, `n_conformistas 2`, `n_neutros 21`, `intentos_divergentes 2`, `combinaciones_logradas 1`, `imitaciones 41`, `nodos_por_origen {"arbol": 5, "combinacion": 1, "interaccion": 0, "llm": 0}`, `pct_fuera_arbol 16.7`.

**6. Gate — CUMPLIDO.**
`success: true`, `ready: true`, `errors: 0`, `warnings: 0`, `pytest: 115 passed in 15.03s`.

## Bloqueantes

Ninguno. B1 resuelto:

| Mutación | Resultado | Restauración |
|----------|-----------|--------------|
| M5 quitar `es_conformista and` en `grafo.py:84` | **CAE** en `test_ni_el_divergente_ni_el_neutro_suman_imitaciones` | SHA-256 OK |
| M3 quitar `registrar_uso(...)` en `sim.py` | CAE en `test_el_conformista_que_usa_un_nodo_ajeno_cuenta_como_imitacion` | SHA-256 OK |
| M4 no forzar `origen="combinacion"` | CAE en `test_el_origen_de_una_combinacion_es_inmutable` | SHA-256 OK |
| M6 quitar el filtro de requisitos activos | CAE en `test_en_crisis_...` | SHA-256 OK |
| M2 quitar el gate de crisis | CAE en `test_la_simulacion_descubre_nodos_del_arbol_con_origen_arbol` | SHA-256 OK |
| M1 quitar la comprobación de temperamento en `_intentar_combinacion` | SOBREVIVE — equivalente (probabilidad negativa <0.6; salida idéntica en 5 semillas) | SHA-256 OK |

Hashes verificados por mí, antes y después: `tribal/sim.py = D14A4634…E85D`, `tribal/culture/grafo.py = 11037114…6948` (coinciden con los que reporta el implementer). Ningún fichero de producción cambió en la ronda 2: el `git diff --stat` sigue en `grafo.py 38` / `sim.py 102` líneas.

## Sin debilitamiento

- `644 passed, 15 skipped` = los 642 de la ronda 1 + los 2 nuevos; no se perdió ni se saltó nada (15 skipped son los mismos de antes).
- `tests/test_divergencia.py` solo crece (13 tests); ningún test existente cambió de aserciones.
- `git diff tests/` sigue siendo aditivo: `test_cli_run.py` (+6, claves nuevas del resumen) y `test_config.py` (+4, claves nuevas de config).
- Las mutaciones que ya caían siguen cayendo (M2/M3/M4/M6), así que los tests viejos no se han aflojado.

## No bloqueante

- **Informe del implementer con cifras viejas en el cuerpo**: la sección «Qué cambié» sigue diciendo «11 tests» y «Tests: 642 passed», y el gate cita 113. La sección «Ronda 2» al final sí está al día (644, 115, hashes). Un lector que se pare en el cuerpo se lleva la foto anterior; convendría actualizar los números.
- **M1 equivalente**: la comprobación de temperamento en `_intentar_combinacion` es redundante con la fórmula de probabilidad. No falla ningún test porque el comportamiento es idéntico, pero si alguien cambia `exceso` por `abs(exceso)` los conformistas empezarían a experimentar sin que nada lo note.
- **Siguen abiertos de la ronda 1, sin cambios y fuera de los criterios**: la proporción de divergentes baja en crisis (15 % vs 33 %; el «frequency-dependence» del objetivo no se mide), `sequia_ticks` corto no produce combinaciones porque la sequía acaba antes de que exista `bifaz`, el test end-to-end usa una sola semilla, `ultimo_activo` concentra `veces_usado`/`imitado` en el nodo más alto de la rama y `combinaciones.py` está al 75 % (validaciones de import sin test).
- **Calidad**: `ruff check` limpio, `ruff format --check` 37 ficheros, `mypy` sin issues, cobertura 95.7 %, `doctor` 7/7 (ronda 1), `pygame` fuera del motor, `--benchmark --crisis` 0.34 ms/tick, determinismo entre procesos correcto y sensible a la semilla.
