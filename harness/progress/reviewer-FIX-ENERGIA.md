# reviewer · FIX-ENERGIA

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

# reviewer · FIX-ENERGIA

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

## Criterios

### 1. La cría no nace con más energía de la que su madre paga — CUMPLIDO

`tribal/sim.py:248-270` (`_nacer`): `aportado = min(ENERGIA_CRIA, madre.necesidades.energia)`,
`madre.necesidades.energia -= aportado`, `Necesidades(energia=aportado)`. El `max(0.0, ...)`
viejo está eliminado. Solo hay dos sitios que crean `Individuo(`: el mundo inicial
(`tribal/core/mundo.py:111`) y `_nacer` (`tribal/sim.py:256`); no hay camino del padre ni
segunda cría (el bucle de `_reproducir` hace `break` tras el primer padre y el cooldown se fija
en `_nacer`).

Suma de energía de todos los individuos antes/después de `_nacer`, barrido propio:

```
madre 30.0  -> madre  0.0  cría 30.0  delta_total +0.000000
madre 49.0  -> madre  0.0  cría 49.0  delta_total +0.000000
madre 50.0  -> madre  0.0  cría 50.0  delta_total +0.000000
madre 51.0  -> madre  1.0  cría 50.0  delta_total +0.000000
madre 64.9  -> madre 14.9  cría 50.0  delta_total +0.000000
madre 65.0  -> madre 15.0  cría 50.0  delta_total +0.000000
madre 65.1  -> madre 15.1  cría 50.0  delta_total +0.000000
madre 70.0  -> madre 20.0  cría 50.0  delta_total +0.000000
madre 100.0 -> madre 50.0  cría 50.0  delta_total +0.000000
```

En todos los casos `cría == min(ENERGIA_CRIA, energía_madre)` y la suma no crece. En el camino
real (umbral `>65`) la cría recibe 50 y la madre conserva >15.

### 2. Un test demuestra que una pareja con energía baja no produce un hijo con energía alta — CUMPLIDO

- `tests/test_reproduccion.py::test_una_pareja_sin_energia_suficiente_no_cria`: pareja a
  `UMBRAL_REPRODUCCION - 1` (64), madura, sin cooldown y en la misma casilla → 0 nacimientos en
  calma y en crisis; `_puede_reproducir` False para ambos.
- `::test_la_madre_no_paga_mas_de_lo_que_tiene`: madre 30 → madre 0, cría 30, total igual.

Mutación reproducida (código viejo restaurado a mano y vuelto a dejar): con
`max(0.0, ...)` + `Necesidades(energia=ENERGIA_CRIA)` la suite nueva da
`1 failed, 4 passed` y falla exactamente `test_la_madre_no_paga_mas_de_lo_que_tiene`
(`assert 50.0 == 30.0`). Fichero restaurado y hash verificado.

Matiz: el test de la pareja a 64 no distingue el código viejo (el umbral ya impedía criar); el
que caza la inyección es el de madre 30. La propiedad del criterio queda cubierta por los dos.

### 3. La población no crece en crisis por subsidio reproductivo — CUMPLIDO

Mecanismo: umbral idéntico (`UMBRAL_REPRODUCCION = 65`; `_puede_reproducir` y
`_umbral_reproduccion` no leen `crisis`) y energía auditada nacimiento a nacimiento:
`dE = +0.000000` en 10 corridas de 8000 ticks. La simulación auditada del test comprueba
`|balance| < 1e-9` en cada nacimiento.

10 semillas × 8000 ticks (semillas 1-10):

```
AGREGADO calma : nac=227  nac/1k_tick=2.838  nac/1k_persona_tick=0.2762  final_total=45  final_medio=4.5
AGREGADO crisis: nac=238  nac/1k_tick=2.975  nac/1k_persona_tick=0.2788  final_total=67  final_medio=6.7
semillas con crisis con menos nacimientos: 5/10
```

La tasa por persona-tick difiere +0,94 % (dentro del margen del test); el test de 3 semillas del
implementer da 0,260 (crisis) vs 0,282 (calma). La población final es caótica (0-20
supervivientes por semilla; las semillas 5 y 7 explican casi toda la diferencia): no es una
medida usable de fertilidad y no hay en ella inyección reproductiva que la explique.

Sobre el «13/20 semillas» del informe: no es significativo (binomial bilateral p≈0,26); no
prueba nada ni a favor ni en contra. Lo que sostiene el criterio es el mecanismo (0 energía
inyectada por nacimiento + mismo umbral), no el conteo por semilla.

Subsidios no energéticos medidos: la cría nace con `sed=0` y `salud=100`, pero en 211
nacimientos de 10 corridas la madre tenía sed 0 y salud 100 al parir → inyección neta 0 en
ambos regímenes; no explica crecimiento en crisis. El informe lo documenta en «Qué falta»; el
código no lo comenta.

Guards probados por mutación: `UMBRAL_REPRODUCCION_CRISIS = 30.0` a nivel de módulo → falla el
guard AST; umbral 30 en crisis dentro de `_umbral_reproduccion` → fallan guard y test de
población. Restaurado.

### 4. `uv run pytest -q` pasa y gate success=true — CUMPLIDO

- `uv run pytest -q` → `710 passed, 15 skipped in 110.59s`.
- `uv run python -m agents --json run harness gate` → `"success": true`,
  `"message": "ENTORNO LISTO — se puede trabajar."`, pytest `181 passed in 47.91s`
  (init.sh ejecuta `pytest tests/`, sin `agents/tests`; por eso 181 frente a 710).
- `bash init.sh` directo no corre en este shell (WSL sin `/bin/bash`), pero el gate del agente
  usa su propio bash y devuelve JSON válido.

## Bloqueantes

Ninguno.

## No bloqueante

1. **README desfasado:** el bloque «Salida real de ... `--json`» (línea 81) ya estaba obsoleto
   en HEAD (le faltan `descubridores`, `supervivencia_*`, `diferencial_seleccion`) y ahora
   tampoco muestra `coste_reproduccion`, aunque el párrafo lo anuncie. Conviene regenerarlo.
2. **Margen del test de crisis:** `MARGEN_RUIDO = 1.10` tolera hasta +10 % de fertilidad en
   crisis. La garantía real es la auditoría de energía por nacimiento (delta 0), no ese assert;
   un subsidio <10 % por otra vía pasaría el margen.
3. **Alcance del guard AST:** solo inspecciona asignaciones de nivel de módulo y nombres con
   `UMBRAL`+`CRISIS`. Una constante con otro nombre (`FERTILIDAD_SEQUIA`) o local a una función
   se escapa; el test conductual de población es el backstop.
4. **Robustez de `aportado`:** `min(ENERGIA_CRIA, madre.energia)` asume energía ≥0 (hoy todas
   las escrituras la recortan a 0). Un `max(0.0, ...)` haría la invariante estructural ante
   caminos futuros.
5. **`coste_reproduccion`:** es una constante que duplica `ENERGIA_CRIA`; aditivo y documentado,
   pero es una clave nueva en el contrato JSON por una feature de conservación (roza el alcance).
6. **`secrets scan`:** falla con 13 hallazgos en `agents/tests/test_redaction.py` y
   `test_secrets_agent.py`; fixtures preexistentes, fuera de este diff.
7. **Población final:** por semilla oscila entre 0 y 20 supervivientes; cualquier criterio de
   población necesita ventana multi-semilla, como ya hace el test.

## Regresiones comprobadas

- `uv run ruff check tribal/ tests/ agents/` → All checks passed!
- `uv run ruff format --check tribal/ tests/` → 43 files already formatted
- `uv run mypy tribal/ tests/` → Success: no issues found in 43 source files
- Determinismo: dos `run --headless --ticks 600 --json` idénticos byte a byte.
- Benchmark: 0.49 ms/tick («cabe en 16.67 ms»), exit 0 → 60 fps.
- pygame solo en `tribal/ui/`; el motor headless no lo importa.
- `git diff tests/`: solo `test_cli_run.py` (+`coste_reproduccion` en CLAVES); el resto es el
  fichero nuevo `tests/test_reproduccion.py`. Sin reformateos ni refactors ajenos.
- `doctor checkup` → 7/7 verificaciones superadas.
- `review_package` → 8 hallazgos, todos preexistentes (step, cli, mundo, acciones…), ninguno en
  el diff.

## Línea de gate

`success=true` · `ENTORNO LISTO — se puede trabajar.` · `181 passed in 47.91s`
(suite completa: `710 passed, 15 skipped`)
