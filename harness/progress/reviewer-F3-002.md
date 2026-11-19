# reviewer · F3-002

- **Fecha:** 2026-11-19
- **Veredicto:** aprobado

## Puerta (esta sesión)

`uv run python -m agents --json run harness gate` → `success: true`, `ready: true`,
`errors: 0`, `warnings: 0`, pytest `418 passed in 232.35s (0:03:52)`.

Repetí la suite entera por mi cuenta, porque `init.sh`/gate solo corren `tests/`:

- `uv run pytest tests/ -q --no-header` → `418 passed in 228.71s`
- `uv run pytest agents/tests -q --no-header` → `556 passed, 15 skipped in 85.08s`
- 418 + 556 = **974 passed, 15 skipped**: la cifra del informe, comprobada.

Lint/typecheck con los comandos del Makefile (no `ruff check .`, que arrastra
`docs/` y `agents/` preexistentes): `ruff check tribal/ tests/ agents/` → All
checks passed; `ruff format --check tribal/ tests/` → 80 files already
formatted; `mypy tribal/ tests/` → no issues in 80 source files.

## Criterios

1. **Enseñanza exige proximidad y lenguaje previo; conformistas imitan — CUMPLIDO.**
   Reproducido a mano, no leído: `ensenar(..., lenguaje=False)` → `False` sin
   transferencia; con lenguaje y a 0,5 tiles → `True`; a 9,0 tiles (radio 2,0) →
   `False` y el aprendiz no sabe la habilidad. `hablar` sin lenguaje devuelve
   `True` (sigue habilitando `proto_palabras`) pero no transfiere: comparten
   canal vía `ensenar(..., lenguaje=...)`. `Simulacion` pasa
   `lenguaje=grafo.activo("proto_palabras")` en **las tres** llamadas de
   `aplicar` (332, 347, 364); no queda ninguna sin el flag.
   Conformista: con `PROB_IMITACION=1.0` el observador de temperamento
   `conformista` copia `cazar` de quien come a su lado, sin lenguaje. Además
   comprobé la cadena completa: imitación → `portadores("turnos_de_vigilia") > 0`
   → el nodo sigue activo tras morir el modelo. `_imitar` no mira temperamento
   (acciones.py:371-384), así que el test cubre la ausencia de esa puerta.

2. **Único portador muere sin enseñar → `apagado`, no borrado — CUMPLIDO.**
   Script propio sobre `raedera` (nodo de combinación): portadores 1 en el tick 4;
   muere en el 5 → no se apaga; en el 124 (119 ticks) sigue activo; en el **125**
   se apaga con `tick_apagado=125` y `motivo_apagado='sin portadores'`. Sigue en
   `grafo.nodos`, `(origen, autor, tick) == ('combinacion', 1, 3)` intactos,
   `contar() == {'activos': 0, 'apagados': 4}` (los otros tres se apagan también
   porque el criterio de "práctica situacional" es *cualquier vivo* y en el
   experimento no queda nadie). Volver a sostenerlo en el 5000 no reescribe el
   tick; `apagar` otra vez devuelve `None`; `descubrir` devuelve el nodo apagado
   con `autor` todavía 1. También verifiqué el caso realista de ventana: pierde
   portadores en 5, vuelve uno en 50 (memoria limpia), se va en 60 → se apaga en
   el 180, exactamente 120 ticks después, no antes.
   **No se reactiva (correcto y además coherente de punta a punta):** `descubrir`
   no revive (`grafo.py`), `_intentar_combinacion` filtra
   `combinacion.id not in self.grafo.nodos` (sim.py:886) y
   `propuestas.validar` rechaza ids ya descubiertos; `beneficios.conocidos` exige
   `grafo.activo(nodo_id)`, así que un apagado deja de dar bonus aunque alguien
   re-aprenda la habilidad. La reactivación no la pide el concepto §9 y una
   transición de un solo sentido mantiene medible el experimento.

3. **Con enseñanza previa el nodo sobrevive — CUMPLIDO.**
   El aprendiz aprende `fabricar` por enseñanza; muere el maestro y tras 50
   ventanas de 120 ticks el nodo sigue activo (`contar` 4/0).

4. **`report culture --json` cuenta activos y apagados — CUMPLIDO.**
   `uv run python -m tribal report culture --json --crisis --ticks 5000` (seed 42,
   la del informe) → `activos 32 · apagados 2 · {34 nodos}`, y los dos apagados
   con `tick_apagado 4822` / `motivo 'sin portadores'`. Coherente:
   32 + 2 = 34 = `len(nodos)`; seed 1 → `34/0`, seed 7 → `32/0`, suma siempre
   igual al total. El texto marca `— apagado en 4822 (sin portadores)`.
   Sobre "¿puede apagarse un nodo recién creado antes de que exista la
   habilidad?": **no**. Las combinaciones conceden la habilidad al autor en el
   mismo acto de descubrir (sim.py:913 y 650), y el resto del árbol no tiene
   habilidad propia (`HABILIDAD_POR_NODO` solo tiene las 5 combinaciones; los 23
   nodos del árbol, `interaccion` y `llm` → portador = cualquier vivo). En tres
   partidas reales (seeds 42/7/1, 5000 ticks) ningún apagado tuvo
   `tick_apagado < tick + 120`, y en seed 42 los dos apagados tenían 0 portadores
   de su habilidad en el momento final.

5. **Gate `success=true` — CUMPLIDO.** Línea de arriba.

## Mutaciones (aplicadas, ejecutadas y revertidas; sha256 restaurado)

| Mutación | Resultado | ¿Muerde? |
|---|---|---|
| Quitar `if not lenguaje: return False` de `ensenar` | `test_sin_lenguaje_ensenar_no_transfiere` FAILED (`assert True is False`) | **sí** |
| `apagar` borra el nodo en vez de marcarlo | 3 tests FAILED (KeyError en `test_sin_portadores…`, `test_el_grafo_no_reactiva…`, `test_la_simulacion…`) | **sí** |
| Quitar la ventana (`tick - inicio < 0`) | `test_sin_portadores…` FAILED (apagaba en el tick 5) | **sí** |
| Sustituir el guard de proximidad por `distancia > 999` | los 8 tests PASAN | **no** |
| Radio de enseñanza ×10 (`DISTANCIA_ENSENANZA * 10`) | los 8 tests PASAN | **no** |

Las dos últimas no muerden por la distancia elegida en el test: el aprendiz está
a 4,0 tiles con radio 2,0, y ahí `_cercania` ya vale 0, así que la probabilidad
es nula aunque no exista el guard. Con un caso decisivo (`PROB_ENSENANZA=100`,
aprendiz a 2,5 tiles) comprobé que el guard **sí** marca la diferencia: con guard
→ `False` y no aprende; con el guard sustituido → `True` y aprende. Ver no
bloqueante 1.

## Verificaciones adicionales

- Persistencia real: `run --headless --ticks 5000 --crisis --db` (seed 42) y
  reapertura con `Repositorio(crear=False)` → `contar {32, 2}`, 34 nodos,
  `origen/autor/tick` intactos; `tick_apagado` y `motivo_apagado` vuelven a
  `0`/`''`. No borra ni corrompe apagados: la deuda es de datos, no de estado.
- 60 fps: 0,701 ms/tick (sin crisis) y 0,808 ms/tick (crisis) con 12 individuos,
  presupuesto 16,67 → ~20× de margen.
- `F3-001` y `F2`: `tests/test_store.py` y `tests/test_puerta_f2.py` verdes dentro
  de los 418; el esquema de `nodos` ya tenía `estado` y sigue siendo
  `repositorio.py` el único que importa `sqlite3`.
- `transmision.py` al 96 % de cobertura (solo falta la rama "ya está apagado" de
  `sostener`). `review_package` no señala nada en los ficheros nuevos; los
  hallazgos (funciones largas de `cli.py`/`sim.py`, 7 args de `run`) son
  preexistentes.
- Alcance: sin cambios en `pyproject.toml`/`uv.lock` (cero deps), sin `fitness`,
  sin `.tmp-*`, `opencode.json` trackeado y sin tocar. Todo lo sucio del árbol
  pertenece a F3-002 (README, featureslist/current de `harness start`, tests
  adaptados, tribal/, arquitectura.md) más los tres ficheros nuevos del informe:
  `commit_feature` no barrería nada ajeno.

## Bloqueantes

_(ninguno)_

## No bloqueante

1. **El test de proximidad no es decisivo.** `test_la_ensenanza_exige_proximidad…`
   coloca al aprendiz a 4,0 tiles con radio 2,0: `_cercania = 0`, probabilidad 0
   aunque se quite el guard. Lo blindaría con
   `monkeypatch.setattr(acciones, "PROB_ENSENANZA", 100.0)` y el aprendiz a 2,5
   tiles (comprobado: así el guard ausente transfiere y el test cae). No cambia
   el veredicto porque el comportamiento exigido está implementado y lo verifiqué
   por separado.
2. **Ningún test fija las claves nuevas de `report culture --json`.** Borrar
   `activos`/`apagados`/`nodos_por_estado` de `cli.py` no rompe la suite; los
   informes de cultura ya tienen tests de otras claves (`seed`, `nivel_max`,
   `nodos_por_origen`), así que un `assert datos["activos"] + datos["apagados"] ==
   len(datos["nodos"])` en `tests/test_arbol.py` cerraría el hueco.
3. **Al reabrir, `tick_apagado`/`motivo_apagado` se pierden** (deuda declarada,
   migración de esquema). Hoy solo se nota si alguien lee el grafo desde la BD:
   saldría `apagado en 0 ()`. Conviene un consumidor que no muestre tick 0 como
   si fuera un dato, o cerrarlo en SAVE-001.
4. **El mapa nodo→habilidad solo apaga las 5 combinaciones.** Con la tribu viva,
   los 23 nodos del árbol, `interaccion` y `llm` cuentan como portador cualquier
   vivo; en seed 42 termina con **1 superviviente** y 32 de 34 nodos siguen
   activos. Es una simplificación documentada (transmision.py, README,
   arquitectura §2.4) y no incumple ningún criterio, pero el relato de §6
   ("la cultura se pierde según quién enseñe") queda más flojo de lo que sugiere
   la descripción de la feature: hoy solo mueren técnicas de combinación.
5. `hablar` mantiene `lenguaje: bool = False` por defecto (necesario para el
   arranque: sin lenguaje no hay `proto_palabras`, y `hablar` debe poder
   descubrirlo). El riesgo es que un llamador externo olvide el flag y la
   transmisión se apague en silencio; solo `sim` lo usa, así que hoy no pasa.
6. `secrets scan` falla con 13 hallazgos, todos en fixtures de `agents/tests/`
   (`test_redaction.py`, `test_secrets_agent.py`), preexistentes y fuera del diff.
   `ruff format --check .` a nivel repo también falla en `agents/`/`docs/`
   preexistentes; el implementer acotó a `tribal/ tests/`, que es lo correcto.
