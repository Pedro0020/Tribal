# reviewer · ART-001

- **Fecha:** 2026-11-20
- **Veredicto:** aprobado

## Criterios

**1. `git ls-files docs/art` > 0 — CUMPLIDO**
`git ls-files docs/art | Measure-Object -Line` → **75**. `git ls-tree -r --name-only HEAD -- docs/art` → **75** (coincide con disco). `8395353` es ancestro de HEAD (`git merge-base --is-ancestor` → exit 0). `.git/info/exclude` sin ninguna entrada activa. `git status --porcelain -- docs/art` → solo ` M docs/art/README.md`; los 74 restantes están limpios en HEAD.

**2. README enlaza docs/art/README.md una sola vez en la tabla de Documentación — CUMPLIDO**
`(Select-String README.md -Pattern "docs/art/README.md" -SimpleMatch).Count` → **1**, en la línea 21, última fila de la tabla *Documentación* (cabecera en L17, justo tras la fila de `arquitectura.md`). Ruta relativa correcta: `docs/art/README.md` existe y está versionado. Idempotencia probada ejecutando `uv run python docs/art/enlazar_readme.py` → `la fila ya está en el README, nada que hacer`, y `git diff --stat README.md` sigue en `1 insertion(+)`: el script no reescribe ni el CRLF ni añade segunda fila.

**3. Sin secretos — CUMPLIDO en la comprobación verificable**
`git grep -n -E "pixl_[A-Za-z0-9_-]{16,}"` sobre ficheros versionados → **0** coincidencias. `git grep -n "pixl_"` → 6 líneas en 5 ficheros, todas prosa/placeholder/aviso redactado:
- `docs/art/README.md:413` — `Authorization: Bearer pixl_…` (redactado, describe el incidente de F2-004)
- `docs/art/README.md:439` — `setx PIXELLAB_API_KEY "pixl_..."` (placeholder de ejemplo)
- `harness/featureslist.json:827` y `harness/progress/current.md:16` — el texto del propio criterio
- `harness/progress/implementer-F2-004.md:64` y `reviewer-F2-004.md:36` — avisos históricos con `pixl_…` redactado

Barrido amplio del árbol de trabajo completo (`pixl_[A-Za-z0-9_-]{10,}`) → **0** resultados. `secrets scan` → 13 hallazgos, **todos** en `agents/tests/test_redaction.py` y `agents/tests/test_secrets_agent.py` (fixtures del propio detector, preexistentes y fuera del diff). Ningún hallazgo en `docs/`, `README.md`, `harness/` ni `opencode.json`.

**4. Gate — CUMPLIDO**
`uv run python -m agents --json run harness gate` → `success: true`, `ready: true`, `errors: 0`, `warnings: 0`, `pytest: 490 passed in 321.14s (0:05:21)`, `siguiente tarea: ART-001 [in_progress]`.

## Verificaciones adicionales

| Comprobación | Resultado |
|---|---|
| Alcance del diff | `git diff --numstat` → `README.md +1/-0`, `docs/art/README.md +16/-26` (hunk único `@@ -474,35 +474,25 @@`, solo §10), `harness/featureslist.json` y `harness/progress/current.md` = escrituras del arnés (`status pending→in_progress`, `started`, `review_rounds`, current.md). Cero reformateos, cero refactors. |
| §10 correcto | Afirma commit `8395353` con 75 ficheros (verificado), retirada de `.git/info/exclude` (verificado: sin entradas), enlace único en *Documentación* (verificado) y script idempotente (ejecutado). §1-§9 y §11 intactos. |
| Producto sin tocar | `TILE_PX = 8` en `tribal/core/modelos.py:26`. Cero ficheros `.py` de producto en el diff. |
| Arte sin tocar | Ningún PNG/ZIP modificado (`git status --porcelain -- docs/art` → solo el README). |
| `opencode.json` | Versionado y limpio (`git status` vacío para él), fuera del diff. |
| Lint | `ruff check tribal/ tests/ agents/` → **All checks passed!** · `ruff format --check tribal/ tests/` (target real de `make lint`) → **90 files already formatted** · `mypy tribal/ tests/` → **Success: no issues found in 90 source files** |
| `doctor checkup` | **7/7 verificaciones superadas** (`tribal v0.1.34`, `uv.lock` sincronizado, arnés completo) |
| `review_package` | Sin bloqueantes: 5 grupos de duplicación AST, 6 `high_complexity`, 5 `todo_comment`, todos en `tribal/` (código preexistente, fuera del diff) |
| docs/art/README sin promesas falsas | Las 4 afirmaciones nuevas de §10 son comprobables y ciertas. Ninguna promesa de cableado del kit al motor ni de subida de `TILE_PX`. |

## Bloqueantes

(ninguno)

## No bloqueante

1. **El criterio 3, leído al pie de la letra, es insatisfacible**: la cadena `pixl_` está en su propio texto (`featureslist.json:827`, `current.md:16`) y en dos avisos históricos. La comprobación válida —0 tokens con forma de clave en ficheros versionados— da 0. Convendría reformularlo a esa forma, pero el dueño del backlog es `harness`, no esta feature.
2. **§10 L492 transcribe la fila sin el enlace markdown**: escribe `| docs/art/README.md | … |` cuando la fila real es ``| [`docs/art/README.md`](docs/art/README.md) | … |``. Cosmético, pero el documento presume de evidencia exacta.
3. **Cabecera de `docs/art/README.md` (L4-6)** sigue diciendo «los únicos cambios en el repo son ficheros nuevos bajo `docs/art/`»; ahora también cambia `README.md`. Es una nota fechada (2026-11-19) y §10 la supersede; no engaña a quien lea el §10.
4. **`harness/progress/history.md` no tiene aún entrada de ART-001** — la escribe `harness finish` al cerrar, no el implementer.
5. **`make lint` no cubre `docs/art/`**: `ruff format --check docs/art/` marcaría `make_sheets.py` y los bloques de código del README. Preexistente y fuera del diff; no reformatear en esta feature.
6. **Sin test que congele el enlace**: la feature es docs+git y no hay suite donde encajarlo, pero un test de una línea que afirme que `README.md` contiene `docs/art/README.md` exactamente una vez es barato y evita que un futuro reformateo del README rompa el criterio en silencio.
7. **`ruff format --check agents/`** reformatearía 88 ficheros, pero `agents/` no está en el target de `make lint` (`$(MODULE)/ tests/`). Preexistente, no es regresión de esta feature.
