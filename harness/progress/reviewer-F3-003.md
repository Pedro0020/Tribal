# reviewer · F3-003

- **Fecha:** 2026-11-19
- **Veredicto:** aprobado

## Criterios

1. **`export obsidian --db --out` escribe un `.md` por nodo con frontmatter (origen, rama, estado) y un wikilink por arista — CUMPLIDO.**
   Lo ejecuté yo, no lo leí:
   ```
   $ uv run python -m tribal run --headless --ticks 600 --db <tmp>/tribu.db
   $ uv run python -m tribal export obsidian --db <tmp>/tribu.db --out <tmp>/vault
   export obsidian: 30 nodos, 27 aristas, 31 ficheros -> <tmp>\vault
   $ ... exit 2 sin base ->
   error: no existe la base <tmp>\no.db
   ```
   Sobre ese vault real: 31 `.md` (30 notas + `index.md`), 54 wikilinks en notas
   (2 × 27), 30 wikilinks en `index.md`. Además construí una base **a mano** con
   38 nodos (ids con acentos, mayúsculas, espacios, `...`, `index`, `CON`, dos
   títulos repetidos y un nodo apagado) y comparé **campo a campo** el
   frontmatter contra el grafo cargado de la base: `id/rama/nivel/origen/estado/
   autor/tick/tick_apagado` correctos en las 38 notas, **0 fallos**; título y
   contenido presentes. Cada arista aparece en ambos extremos (0 faltantes de 64
   esperados) y el nodo apagado sale `estado: "apagado"`, `tick_apagado: 650`.

2. **Idempotente (mismos bytes) — CUMPLIDO.**
   Mismo bytes con la CLI sobre el vault real: hash de nombres+bytes
   `48c0c4f5575dc729d1e48193beb1a65096628687ca559d958db2778682d74ddc` en la
   1.ª y la 2.ª ejecución (idéntico, además, al que reporta el implementer: el
   número no es inventado). Con el grafo a mano: idéntico al reexportar sobre el
   mismo directorio **y** sobre uno nuevo, con títulos repetidos, colisiones de
   slug y un nodo apagado. UTF-8 sin BOM y sin `\r\n` (verificado en bytes).

3. **Test: nº de `.md` y de wikilinks coincide con nodos y aristas — CUMPLIDO.**
   `tests/test_export.py` deriva N y M de la base y exige N+1 ficheros,
   2×M wikilinks en notas y N en `index.md` (igualdades exactas, no `>=`), y
   recorre **cada** arista comprobando ambos extremos:
   `uv run pytest -q tests/test_export.py` → `4 passed in 1.92s`.

4. **gate — CUMPLIDO.** Ejecutado por mí en esta sesión:
   `"success": true`, `"ready": true`, `errors 0`, `warnings 0`,
   `pytest 425 passed in 222.62s`.

## Mutaciones (el test debe caer)

Rompí `tribal/store/export.py` a propósito y restauré después (fichero
byte-idéntico). `pytest -q tests/test_export.py` en cada mutación:

| Mutación | Resultado |
|---|---|
| M1 quitar el wikilink saliente | `1 failed, 3 passed` |
| M2 quitar `rama:` del frontmatter | `1 failed, 3 passed` |
| M3 meter un valor aleatorio en el frontmatter | `1 failed, 3 passed` |
| M4 desactivar el sufijo de colisión de slug | `2 failed, 2 passed` |
| M5 `index.md` sin enlaces a nodos | `1 failed, 3 passed` |
| M6 sin sección Relaciones (0 wikilinks) | `1 failed, 3 passed` |

## Otros checks

- **Sin `sqlite3`**: `grep` sobre `tribal/store/` lo deja solo en
  `repositorio.py`; `export.py` consume `Repositorio.cargar()`.
- **Nombre de fichero**: todos los slugs del grafo a mano son ASCII,
  0 colisiones, sin subdirectorios ni rutas raras; `index` (id) → `index-2`,
  `...` → `nodo`, `eco uno`/`eco-uno` → `eco-uno`/`eco-uno-2`, `Ñandú Ritual!`
  → `nandu-ritual-2`.
- **Ficheros viejos**: metí `nota-humana.md` y una nota huérfana en el vault y
  reexporté: **no se borra nada**. Está documentado en el docstring del módulo,
  en `--help`, en README §«Export a Obsidian» y en arquitectura §2.5/§6.
- **Alcance**: `pyproject.toml`/`uv.lock` sin tocar (sin deps), sin `.tmp-*`, sin
  `.db` ni `vault-tribu/` en el repo, `opencode.json` fuera del diff. No hay
  reformateos: el diff de `cli.py` es aditivo (+ docstring del módulo).
- **Regresiones**: `ruff check` limpio, `ruff format --check` 82 ficheros,
  `mypy` sin issues, `tests/test_store.py tests/test_transmision.py
  tests/test_arbol.py` → 37 passed (F3-001 y F3-002 intactos).
  `doctor checkup` 7/7. Suite completa: `uv run pytest -q` →
  **`981 passed, 15 skipped in 299.97s`** (981 = `tests` + `agents/tests`; los
  425 del gate son solo `tests/`, que es lo que corre `init.sh`; ambos números
  son consistentes, no hay discrepancia con el informe del implementer).
- `review_package`: ningún hallazgo en `export.py` ni en `test_export.py`.
  `secrets scan`: los 13 hallazgos son fixtures preexistentes de
  `agents/tests/test_redaction.py` y `test_secrets_agent.py`, ninguno en el diff.

## Bloqueantes

Ninguno.

## No bloqueante

1. **El test de frontmatter comprueba la clave, no el valor.** Mutación que
   verifiqué: fijar `estado: "activo"` u `origen: "arbol"` para todos los nodos
   → `4 passed`. Los valores reales son correctos (los comparé yo contra la
   base), pero una regresión de valor pasaría el test. Arreglo: comparar
   `f["origen"] == nodo.origen` etc. contra el nodo de la base.
2. **Nombres reservados de Windows sin guardar.** `_slug("CON")` → `con.md`;
   el fichero se escribe (Python usa rutas extendidas) pero Obsidian/Explorer no
   lo abren. Ningún id del catálogo cae ahí, por eso no bloquea; un sufijo
   `-nodo` para `con/prn/aux/nul/com1..` lo cerraría.
3. **`motivo_apagado` no se exporta.** Un nodo apagado pierde justo el dato que
   F3-002 se molestó en preservar. No está en los criterios; añadirlo al
   frontmatter (o al cuerpo) haría el vault más fiel.
4. **Etiqueta semántica de las aristas.** En `guijarro.md` sale
   `[[lasca]] — prerrequisito (saliente)`, que se lee como «lasca es
   prerrequisito»; es al revés. Sugerencia: `(saliente)` → «lo desbloquea» y
   `(entrante)` → «requiere».
5. **Arista colgante = KeyError con traza.** `_leer_grafo` no valida extremos;
   una base tocada a mano haría `salientes[arista.origen]` explotar en vez de
   salir con 2 y un mensaje. Solo alcanzable con una base corrupta.
6. **El reexport de `tribal/store/__init__.py` no lo usa nadie** (CLI y test
   importan `tribal.store.export` directamente). Es superficie pública muerta;
   o se usa desde `cli.py` o se quita.
7. El fixture del test no incluye ningún nodo apagado; lo cubrí a mano, pero el
   estado apagado no tiene test propio en el export.
