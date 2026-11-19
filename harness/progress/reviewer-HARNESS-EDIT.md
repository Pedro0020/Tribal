# reviewer · HARNESS-EDIT

- **Fecha:** 2026-11-19
- **Veredicto:** aprobado

# reviewer · HARNESS-EDIT (ronda 3 — aprobado)

## Comprobaciones de esta ronda

**(a) `HARD-1` y `F2-001` vuelven a depender de `F1-004` — CUMPLIDO.**
`HARD-1 pending ["F1-004"]`, `F2-001 pending ["F1-004"]`. Audit: `2026-11-19T02:03:55Z · harness.edit ·
success=true · "'HARD-1' corregida (depends_on)"`.

**(b) `git diff harness/featureslist.json` sin mutaciones de deps — CUMPLIDO.**
Un único hunk, 4/2 líneas: `HARNESS-EDIT` `pending → in_progress` (+`started`, `review_rounds: 2`). El diff
feature-a-feature contra `HEAD` lo confirma: solo cambia `HARNESS-EDIT` en esos tres campos; ninguna otra feature
cambia (en particular, ninguna `depends_on`). No hay alta previa del líder pendiente en este diff.

**(c) El informe ya no contiene afirmaciones falsas — CUMPLIDO.**
Reconoce la mutación de HARD-1 (audit 01:43:09Z), la causa real (la raíz del contexto sale del paquete, no del cwd,
así que el «aislamiento» en `%TEMP%` no aislaba), el comando de restauración y su diff; y dice correctamente que
`F2-001` y `HARD-1` siguen en `["F1-004"]`, a decisión del líder. Verificado contra el JSON: coincide.

**(d) Gate verde y suite sin cambios — CUMPLIDO.**
`harness gate` (esta sesión): `success: true`, `ready: true`, `errors: 0`, `warnings: 0`, `ENTORNO LISTO`,
exit 0, pytest interno `241 passed in 137.80s`. Suite completa: `797 passed, 15 skipped in 204.38s`
(mismo resultado que las rondas anteriores).

## Criterios y extensión (ya validados en la ronda 2, sin cambios de código desde entonces)

1. `edit` corrige título/descripción/criterios sin tocar el JSON — CUMPLIDO (before/after reales, solo cambia el
   md5 del objetivo; no-op no reescribe).
2. Rechaza id inexistente y no-`pending` — CUMPLIDO (in_progress/done/blocked, sin escribir bytes).
3. Tests en `agents/tests` — CUMPLIDO (`27 passed`, 9 nuevos vía `run()` cubriendo bool/int y `criteria ";"`).
4. Gate `success=true` — CUMPLIDO.
Extensión: existencia de deps, ciclos (directo/transitivo/autodependencia, mensaje recortado), `--depends_on ""`
limpiando también en PowerShell (`True`), rechazo de `status`/`blocked_reason`, diff before/after — CUMPLIDO.

## No bloqueante (heredado, no impide aprobar)

- `add` conserva el agujero de tipos con flags sin valor: ticket aparte.
- `--title "True"`/`--title 3` no representables por CLI (el parser los convierte a bool/int): caso de borde.
- `.claude/agents/reviewer.md` (drift previo, regenerado) y errores preexistentes de `mypy agents/`: anotar en
  `history.md` si se quiere trazabilidad.
