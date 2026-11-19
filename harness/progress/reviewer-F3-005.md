# reviewer · F3-005

- **Fecha:** 2026-11-19
- **Veredicto:** aprobado

## Criterios

1. **Camino y origen de cada nodo — CUMPLIDO.** BD nueva por CLI (5000 ticks, semilla 2,
   `--crisis`, 34 nodos y 36 aristas). `--query "hasta el fuego"` → `intencion: ruta`,
   destino `ahuyentar_depredadores`, 5 pasos `observar_rayo → conservar_brasas → friccion
   → cocinar → ahuyentar_depredadores`, cada uno con `rama`, `origen`, `autor`, `tick` y
   arista. Comparado con mi BFS independiente sobre las aristas de la BD: **idéntico** (4
   aristas, todas existentes). `--json` con los 7 campos por paso. Variantes con exit 0:
   `llegar al fuego`, `llego hasta el fuego`, `¿Hasta el FUEGO?`, `que ruta llevo al fuego`,
   `que ruta llevo a la lasca`.
2. **Apagados con portador — CUMPLIDO.** `--query "que nodos murieron con el anciano"` →
   `intencion: apagados`, los mismos 3 nodos `apagado` de la BD (`raedera`,
   `caceria_dirigida`, `turnos_de_vigilia`) con rama, autor, `tick_apagado` y motivo
   (`sin portadores`); fila a fila coincide con el grafo. `fallecieron`/`desapareció`/
   `murió` también entran por la intención correcta. Sin inventar.
3. **Test sintético — CUMPLIDO.** `pytest tests/test_consulta.py -q` → **12 passed**.
   Camino mínimo (dos rutas), nodo inexistente sin excepción, vocabulario de ruta y de
   apagados, **arista inversa** (`lasca→guijarro` → camino `guijarro→lasca`), desempate
   estable (`raiz→alfa→fuego` con aristas insertadas `raiz→beta, raiz→alfa`), CLI sobre
   partida guardada, base basura y directorio.
4. **Gate — CUMPLIDO** (ejecutado en esta sesión).

## Bloqueantes de la ronda 1 — resueltos y verificados

1. **Vocabulario `hasta`/`murieron`.** `_PALABRAS_RUTA` incluye `hasta` (`consulta.py:40-42`)
   y `_PALABRAS_APAGADOS` cubre `murieron`/`murio`/`fallecieron`/`fallecio`/
   `desaparecieron`/`desaparecio` (`:46-55`); `consultar()` consulta ambos (`:209-215`).
   Docstring, README:666-673 y arquitectura:193-195 ya solo listan palabras que el código
   reconoce. Reproducido sobre la BD nueva: `"hasta el fuego"` → ruta (5 pasos) y
   `"que nodos murieron con el anciano"` (el ejemplo literal del objetivo) → apagados.
   Test: `test_vocabulario_documentado_de_ruta` y `…_de_apagados`.
2. **BFS no dirigido sin test.** `test_bfs_recorre_aristas_en_sentido_inverso` fija el
   recorrido inverso y `test_desempate_estable_entre_caminos_de_igual_longitud` fija el
   orden determinista. Ambos tienen dientes (ver mutaciones).

## Mutaciones (fichero mutado y restaurado con hash idéntico `253A67BF…`)

| Mutación | Resultado |
|---|---|
| BFS dirigido (quitar `adyacencia[destino].append(origen)`) | **1 failed, 11 passed** → cae `test_bfs_recorre_aristas_en_sentido_inverso` |
| `vecinos.sort()` → `pass` | **1 failed, 11 passed** → cae `test_desempate_estable…` |
| Quitar `hasta`/`murieron`/`murio` del vocabulario | **2 failed, 10 passed** → caen los dos tests de vocabulario |

Tras restaurar: `12 passed` y SHA256 del fichero igual al original.

## No bloqueante

- `vault/01_PROYECTO/arquitectura.md:193-194` resume el vocabulario omitiendo `llevo`,
  `llego`, `murio`, `fallecio` y `desaparecio`: es un subconjunto (no promete nada falso),
  pero conviene igualarlo al docstring y al README.
- Siguen abiertos los no bloqueantes preexistentes que ya anoté: `ultimo_portador` no se
  persiste en `store` (siempre `desconocido` al releer) y el JSON llama `arista` a la
  dirección de recorrido, que puede ser la inversa del prerrequisito guardado.
- `--db <directorio>` → `error: … no es un fichero`, **exit 2**, sin traza (arreglado y con
  test); base inexistente y fichero no-SQLite siguen en 2. `report db` conserva el
  comportamiento preexistente de `Repositorio.__init__` (ticket aparte).
- Alcance limpio: `pyproject.toml`/`uv.lock` intactos, sin `.tmp-*`, sin BDs en el repo
  (las mías en `%TEMP%`), `opencode.json` sin tocar, featureslist/current de `harness start`,
  F3-001..004 sin ficheros modificados.
- `secrets scan`: 13 hallazgos, todos fixtures preexistentes de `agents/tests/`; ninguno en
  `consulta.py`, `cli.py` ni `test_consulta.py`.

## Regresiones

`pytest -q` → **1003 passed, 15 skipped in 297.74s**; suites de F3-001..004
(`test_store`, `test_transmision`, `test_tradiciones`, `test_export`, `test_telemetria`,
`test_cli`, `test_arbol`) → **64 passed**; `ruff check tribal/ tests/ agents/` → All checks
passed; `ruff format --check tribal/ tests/` → 84 files already formatted; `mypy tribal/
tests/` → no issues in 84 files.
