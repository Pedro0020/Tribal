# reviewer · HARNESS-REMOVE

- **Fecha:** 2026-11-20
- **Veredicto:** aprobado

## Criterios

Puerta ejecutada por el reviewer en esta sesión: `harness gate` → `success=true`,
"ENTORNO LISTO — se puede trabajar.", `pytest: 498 passed in 322.71s (0:05:22)`,
featureslist `54 features · 8 pending · 1 in_progress · 38 done · 7 blocked · 0 discarded`.
Suite completa: `uv run pytest -q` → **1080 passed, 15 skipped in 401.08s (0:06:41)**.
Todo lo funcional se probó en copias temporales (`agents/` + `harness/` en %TEMP%);
el backlog real solo tiene el diff de `harness start` (+ `review_rounds`).

1. **`discarded` en VALID_STATUS/evals/init.sh — CUMPLIDO.** `init.sh` (bloque del
   validador extraído tal cual del fichero) sobre backlog temporal: `ok | 1
   features · ... · 1 discarded` y `ok | sin trabajo pendiente`; con una pending
   más: `ok | 2 features · 1 pending · ... · 1 discarded` + `next | X-002`.
   Control negativo: status `inventado` → `fail | status 'inventado' no válido
   (pending|in_progress|done|blocked|discarded)`. `evals.runner --harness` verde.
   Mutar `discarded` fuera de `VALID_STATUS`: cazada.
2. **`discard` deja estado/motivo/fecha — CUMPLIDO.** `discarded_reason`,
   `discarded_on=2026-11-20`; sin motivo → `needs`, bytes idénticos (mutación
   "discard sin exigir motivo": cazada).
3. **Fuera de `next`/elegibles y contador propio — CUMPLIDO.** Con TMP-001
   descartada y TMP-002 dependiendo de ella: `next` → TMP-003, `status` →
   `3 features · 2 pending · ... · 1 discarded`.
4. **Línea en history.md con id, título y motivo — CUMPLIDO.**
   `- **Descartada:** TMP-001 · Uno · 2026-11-20 · motivo: ya no se quiere`
   (mutación "sin línea de history": cazada).
5. **`revive` y rechazo de `start`/`finish`/`block` — CUMPLIDO.** `revive` →
   pending sin `discarded_*`/`blocked_reason` y `review_rounds=0` (mutación
   "revive no limpia discarded_reason": cazada); `start`, `finish` y `block`
   sobre discarded → `success=false`, mensaje con "descartada" y "Revívela antes",
   bytes intactos. El test de `finish` monkeypatchea `gate` a `success=True`, así
   que **la guardia es el único motivo del rechazo**: quitarla deja `1 failed`.
   El de `block`, igual: `1 failed`. (En la ronda 1 estos dos no mordían; ahora sí.)
6. **`remove` solo pending y nombra dependientes — CUMPLIDO.** El test de
   done/in_progress usa ahora `C-001` (sin dependientes) y afirma
   `data["status"]`; nuevo test para blocked/discarded. Mutar
   `if status != "pending":` deja **4 failed**. Comportamiento verificado a mano:
   `remove` de blocked → rechazo y byte-idéntico; dependientes nombrados en
   `data.dependents` y en el mensaje (mutación "sin rechazo de dependientes":
   cazada).
7. **Destructiva: `needs` sin `--yes`, dry-run sin escribir — CUMPLIDO.**
   `run("remove", ...)` sin `confirm` → falla con `needs` y bytes idénticos;
   `dry_run` → `data.dry_run=True` sin escribir (mutación "remove ignora dry_run":
   cazada); `confirm=True` borra solo esa y conserva `explorer-TMP-003.md`
   (`reports_kept`). El contrato sigue marcando `remove` como `destructive`.
8. **Tests — CUMPLIDO.** 26 casos recogidos (`26 passed in 5.84s`), el conteo que
   declara el informe. 12 mutaciones aplicadas y restauradas byte a byte, todas
   cazadas (ver abajo). Nada nuevo en `tests/` fuera de `agents/tests/`.
9. **Gate y limpieza — CUMPLIDO.** Gate verde (arriba); `ruff check tribal/ tests/
   agents/` → *All checks passed*; `ruff format --check tribal/ tests/` (alcance
   de CI/Makefile) → `91 files already formatted`; `mypy tribal/ tests/` →
   `Success: no issues found in 91 source files`; `prompts_sync` → sincronizado
   (exit 0), y el prompt documenta `start/block/finish` de discarded, el limpiado
   de `blocked_reason` y el aviso de dependientes. Sin dependencias nuevas
   (`pyproject.toml`/`uv.lock` sin cambios) y `opencode.json` sin tocar.

## Bloqueantes

Ninguno. Los dos de la ronda 1 están cerrados y **verificados por mutación**, no
solo por lectura: `remove` con `C-001` + `data["status"]` (4 failed al quitar la
guardia) y `finish` con `gate` monkeypatcheado (1 failed al quitarla).

## No bloqueante

- `agents/board.py` y `tribal-board.cmd` siguen sin trackear y **no** están en el
  diff (`git diff` no los lista) ni referenciados en `harness_agent.py`, tests o
  prompts; el informe solo los menciona para decir que no se tocaron. Ajenos a
  esta feature: que no entren en el commit.
- `.opencode/agents/reviewer.md` y `.claude/agents/reviewer.md` (1 línea cada uno)
  son **míos**, de la ronda 1 (regla: mutar cada guardia nueva), no del
  implementer.
- `discard` avisa de los dependientes pero no impide el descarte (decisión
  explícita y documentada; se revierte con `revive`). Efecto secundario inocuo:
  `harness next` ya no los ofrece, mientras que `init.sh` sigue anunciándolos como
  "siguiente tarea" porque su validador nunca miró `depends_on` (preexistente,
  fuera del alcance de esta feature).
- `secrets scan`: 13 hallazgos, todos fixtures preexistentes
  (`agents/tests/test_redaction.py`, `agents/tests/test_secrets_agent.py`);
  detector heurístico propio porque `detect-secrets` no está instalado.
- `test coverage_report` sigue tardando más de lo que aguanta un timeout de 15
  min; la cobertura queda cubierta por la suite completa (1080) y la puerta.
