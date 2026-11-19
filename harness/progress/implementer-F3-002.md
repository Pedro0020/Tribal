# implementer · F3-002

- **Fecha:** 2026-11-19
- **Veredicto:** ok

# Implementer — F3-002 (cierre de huecos del reviewer)

## Qué cambié

- `tests/test_transmision.py`: `test_la_ensenanza_exige_proximidad...` ahora es
  decisivo — `PROB_ENSENANZA=100` y aprendiz a 2,5 tiles (x=4,5, radio 2,0).
  Sin el guard de distancia transfiere; con el guard, no.
- `tests/test_arbol.py`: test nuevo
  `test_report_culture_json_cuenta_activos_y_apagados`: fija `activos`,
  `apagados`, `nodos_por_estado` y `activos + apagados == len(nodos)`.
- `tribal/store/esquema.py`: `nodos` gana `tick_apagado` (INTEGER, default 0) y
  `motivo_apagado` (TEXT, default ''); `estado` sigue siendo `activo`/`apagado`.
- `tribal/store/repositorio.py`: `guardar` y `_leer_grafo` escriben/leen las dos
  columnas; `_migrar_apagado` hace `ALTER TABLE ... ADD COLUMN` al abrir con
  `crear=True` una base anterior a F3-002; con `crear=False` una base vieja se
  lee con `0 AS tick_apagado, '' AS motivo_apagado` (no se escribe en lectura).
- `tests/test_store.py`: columnas nuevas en el test de esquema, ida y vuelta de
  un nodo apagado (`tick=100`, `sin portadores`) y migración de una base sin
  las columnas.
- `README.md` y `vault/01_PROYECTO/arquitectura.md`: el apagado se persiste y
  la migración es compatible con BDs existentes.

## Criterios

1. Test de proximidad decisivo y verificado por mutación: mutar el guard a
   `distancia > 999.0` hace FAILED el test (`assert True is False`); revertido.
2. Test de `report culture --json`: borrar el bloque de tres claves de `cli.py`
   hace FAILED el test (`KeyError: 'activos'`); revertido.
3. Persistencia del apagado: `test_el_apagado_del_nodo_sobrevive_a_cerrar_y_reabrir`
   y `test_una_base_sin_columnas_de_apagado_se_migra_al_abrirla` PASSED.

## Evidencia

`uv run pytest` (los cuatro tests de los huecos):

```
tests/test_transmision.py::test_la_ensenanza_exige_proximidad_aunque_haya_lenguaje PASSED [ 25%]
tests/test_arbol.py::test_report_culture_json_cuenta_activos_y_apagados PASSED [ 50%]
tests/test_store.py::test_el_apagado_del_nodo_sobrevive_a_cerrar_y_reabrir PASSED [ 75%]
tests/test_store.py::test_una_base_sin_columnas_de_apagado_se_migra_al_abrirla PASSED [100%]
============================== 4 passed in 4.73s ==============================
```

Mutación 1 (guard de distancia sustituido por `999.0`):

```
E       AssertionError: assert True is False
FAILED tests/test_transmision.py::test_la_ensenanza_exige_proximidad_aunque_haya_lenguaje
1 failed in 0.39s
```

Mutación 2 (borrado de `activos`/`apagados`/`nodos_por_estado` en `cli.py`):

```
E       KeyError: 'activos'
FAILED tests/test_arbol.py::test_report_culture_json_cuenta_activos_y_apagados
1 failed in 0.78s
```

`uv run pytest -q`: `977 passed, 15 skipped in 295.99s (0:04:55)`

Lint/typecheck:

```
All checks passed!
RUFF_CHECK=0
80 files already formatted
RUFF_FORMAT=0
Success: no issues found in 80 source files
MYPY=0
```

`bash ./init.sh`:

```
Proyecto
  ✔ paquete                tribal/ presente (project.yml)
  ✔ pyproject              presente
  ✔ tests                  35 ficheros de test

Verificación
  ✔ pytest                 421 passed in 219.79s (0:03:39)

━━ ENTORNO LISTO ━━  0 aviso(s)
```

`uv run python -m agents --json run harness gate`:

```
{'success': True, 'message': 'ENTORNO LISTO — se puede trabajar.', 'warnings': [], 'needs': []}
{'ready': True, 'errors': 0, 'warnings': 0}
```

## Qué falta

- Nada de los tres huecos. Sigue fuera de alcance el relato de §6 para nodos del
  árbol (no bloqueante 4 del reviewer) y no hay commit: cierra el líder.
