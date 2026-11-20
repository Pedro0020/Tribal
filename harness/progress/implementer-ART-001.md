# implementer · ART-001

- **Fecha:** 2026-11-20
- **Veredicto:** ok

# ART-001 — implementer (ronda 2)

## Qué cambié
- `README.md`: una fila en la tabla de *Documentación* (L21), insertada por
  `docs/art/enlazar_readme.py`. Diff: +1 línea.
- `docs/art/README.md`: reescrito **solo el §10** (L477-501), de "pendiente" a
  "hecho en ART-001". Diff: 1 bloque, -22/+16, sin tocar §1-§9 ni §11.
- `docs/art/`: ya versionado en `8395353` (75 ficheros). No toqué el arte.
- Sin cambios de producto: `TILE_PX` sigue en 8, `opencode.json` intacto y fuera
  del diff, `harness/` no editado a mano.

## Criterios de aceptación

1. **docs/art versionado** — OK.
   `git ls-files docs/art | Measure-Object` → 75.
   `git log --oneline -1 -- docs/art` → `8395353 chore: kit de pixel art y hojas de sprites`.
   `.git/info/exclude` sin `docs/art`. No hizo falta `git add -f`.

2. **README enlaza docs/art/README.md una sola vez** — OK.
   `uv run python docs/art/enlazar_readme.py` → `fila insertada en ...README.md (línea 21)`.
   `(Select-String -Path README.md -Pattern "docs/art/README.md").Count` → 1.
   Fila dentro de la tabla de Documentación, tras `arquitectura.md`.

3. **Sin secretos** — OK por la parte que importa: **0 tokens con forma de clave**.
   Barrido sobre los **497 ficheros versionados** (`git ls-files -z`, bytes):
   - `pixl_[A-Za-z0-9_-]{16,}` → **0**
   - `pixl_[A-Za-z0-9]{16,}` → **0**
   Hay **6 apariciones del literal `pixl_` en 5 ficheros, ninguna es una clave**:
   - `docs/art/README.md:413` — prosa de seguridad: `Bearer pixl_…` **redactado**, describe el incidente.
   - `docs/art/README.md:439` — placeholder de ejemplo: `setx PIXELLAB_API_KEY "pixl_..."`.
   - `harness/featureslist.json:827` — **el texto del propio criterio** ("grep ... de pixl_ ...").
   - `harness/progress/current.md:16` — copia del criterio.
   - `harness/progress/implementer-F2-004.md:64` — aviso histórico, token redactado como `pixl_…`.
   - `harness/progress/reviewer-F2-004.md:36` — aviso histórico, token redactado como `pixl_…`.
   No borré el texto del criterio. El "0 ficheros" literal es autocontradictorio
   porque el criterio se cita a sí mismo; la comprobación válida es la de tokens.

4. **Gate** — OK.
   `uv run python -m agents --json run harness gate` → `"success": true`,
   `"ready": true`, `"errors": 0`, `"warnings": 0`.

## Evidencia
```
uv run pytest -q  -> 1046 passed, 15 skipped in 390.57s (0:06:30)
harness gate      -> success=true, ready=true, errors=0, warnings=0
ruff check tribal/ tests/ agents/  -> All checks passed!   (ronda 1)
mypy tribal/ tests/                -> Success: no issues found in 90 source files  (ronda 1)
git diff --stat -> README.md +1; docs/art/README.md solo §10; harness/* del arnés
```

## Qué falta / avisos
- **Criterio 3**: si el reviewer exige el literal "0 ficheros", hay que reformular
  el texto en `featureslist.json` (lo posee `harness`), no tocar la evidencia.
- Los 2 PNG/ZIP y el resto de `docs/art` no contienen el patrón (escaneo byte a
  byte, no solo texto).
- `ruff format --check docs/art/` marcaría `make_sheets.py` y bloques de código del
  README de arte; fuera del target `lint` del Makefile, no los reformateé.
- Sin commit, como se pidió.
