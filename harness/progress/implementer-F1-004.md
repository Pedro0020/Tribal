# implementer · F1-004

- **Fecha:** 2026-11-18
- **Veredicto:** ok

# F1-004 — Estado a la parada por decisión del líder

## Qué hay en el árbol

- La ronda 2 dejó F1-004 con plasticidad cultural, crisis y beneficios, pero el
  reviewer la rechazó: el ruido de las crías no dependía de ninguna innovación y
  la crisis se había vuelto demográficamente favorable.
- En la ronda 3 se alcanzó a implementar la corrección de mecanismo:
  - `tribal/sim.py`: plasticidad solo con una `combinacion` activa (una
    tradición ya no cuenta); sin innovación no hay ruido gaussiano y solo hay
    decaimiento suave hacia 0.5; +0.035 por innovación a los vivos, +0.02 por
    generación a los progenitores y molde de la cría solo con innovación.
  - La crisis se endureció: recursos a la mitad, sed 1.3, cooldown global de
    crisis, ventaja reproductiva relativa y realimentación por frecuencia.
  - `tribal/core/genoma.py`: umbral `UMBRAL_DIVERGENTE` calibrado a 0.55 y
    docstring corregida (plasticidad fenotípica, no herencia).
  - Tests nuevos de no-innovación, tradición que no cuenta, innovación que sí,
    cooldown, frecuencia y penalización.
- **La calibración de la ronda 3 no se terminó.** Con las constantes finales
  probadas el barrido 1..10 seguía teniendo semillas con población en crisis
  igual o superior a la calma, alguna semilla sin combinación (seed 6) y brazos
  con σ por debajo de 0.1 o con extinción. No se debe presentar como puerta
  superada. El líder decidió parar antes de seguir retocando.
- `heredar` no se tocó. Los tests de F1-001 no se modificaron.

## Ficheros de F1-004

Modificados:

- `README.md`
- `tests/test_arbol.py`
- `tests/test_cli_run.py`
- `tests/test_divergencia.py`
- `tribal/cli.py`
- `tribal/core/acciones.py`
- `tribal/core/depredador.py`
- `tribal/core/genoma.py`
- `tribal/core/modelos.py`
- `tribal/culture/arbol.py`
- `tribal/culture/grafo.py`
- `tribal/sim.py`

Nuevos:

- `tests/test_tradiciones.py`
- `tribal/culture/beneficios.py`
- `tribal/culture/tradiciones.py`
- `harness/progress/implementer-F1-004.md` (este informe, vía `harness record`)

No son míos: `harness/featureslist.json` y `harness/progress/current.md` (los
mueve `harness`), `harness/memory.md`, `vault/01_PROYECTO/concepto.md`,
`vault/01_PROYECTO/stack-tecnologico.md` y
`vault/01_PROYECTO/emergencia-seleccion.md`.

## Verificación parcial

- Última ejecución dirigida tras los cambios de ronda 3:
  `49 passed` en `tests/test_divergencia.py`, `tests/test_genoma.py` y
  `tests/test_tradiciones.py`.
- `ruff check tribal tests` y `ruff format --check tribal tests`: limpios.
- `mypy tribal tests`: sin issues.
- La suite completa **no se volvió a ejecutar** después de los últimos cambios
  de calibración porque el líder ordenó parar. La última suite completa antes
  de esa calibración fue `670 passed, 15 skipped`; no se usa como evidencia de
  la ronda 3.
- Mutaciones comprobadas antes de la parada: quitar `PLASTICIDAD_HITO` tumba el
  test de innovación; quitar la ventaja tumba el test de cooldown; quitar la
  penalización tumba el test de energía.

## Temporal

- Se dejó `.tmp-impl.md` en la raíz para alimentar `harness record
  --content-file`. No se borra por indicación del líder.

## Parada por decisión del lider

Me detuve antes de la ronda 3; el diagnóstico y el arreglo están en
`vault/01_PROYECTO/emergencia-seleccion.md`; F1-004 se bloquea.
