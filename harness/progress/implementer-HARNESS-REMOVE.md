# implementer · HARNESS-REMOVE

- **Fecha:** 2026-11-20
- **Veredicto:** ok

## Qué cambié

- `agents/tests/test_harness_discard.py`: `test_remove_rechaza_done_e_in_progress`
  parametriza sobre `C-001` (sin dependientes) y afirma `data["status"]`; nuevo
  `test_remove_rechaza_blocked_y_discarded`; `test_finish_rechaza_una_descartada`
  monkeypatchea `harness.gate` con `success=True` y afirma el mensaje; nuevos
  `test_block_rechaza_una_descartada`, `test_discard_de_una_blocked_limpia_blocked_reason`
  y `test_discard_avisa_de_los_dependientes_sin_impedirlo`.
- `agents/agents/harness_agent.py`: `block` rechaza una `discarded`; `discard`
  limpia `blocked_reason` y devuelve los dependientes en `warnings`/`data`
  sin impedir el descarte.
- `agents/prompts/harness_agent.md`: rechazos actualizados (block + bloqueada
  descartada + aviso de dependientes); bloque autogenerado regenerado con
  `prompts_sync --write`.
- `agents/board.py`: no tocado ni referenciado.

## Criterios

1. Guardia "solo pending" de `remove` pinneada — `test_remove_rechaza_done_e_in_progress`
   sobre `C-001` + `data["status"]`, y `test_remove_rechaza_blocked_y_discarded`.
   Mutación `if status != "pending"` → `if False:`: **4 failed**.
2. `finish` de descartada pinneado — gate monkeypatcheado a `success=True` y
   mensaje "descartada"; mutar la guardia: **1 failed**.
3. `block` de descartada la rechaza (sigue `discarded`, sin `blocked_reason`);
   `discard` de blocked limpia `blocked_reason`; con dependientes avisa nombrados
   en `warnings`/`data.dependents` y descarta igual. Mutaciones cazadas: **1 failed** cada una.
4. `remove` de blocked/discarded cubierto por test parametrizado (byte-idéntico).
5. Conteo corregido: **26 casos** en el fichero (antes decía 24), **1080** en la suite.
6. `agents/board.py` (untracked ajeno) queda fuera del informe y del cambio.

## Evidencia

### Tests del fichero

```
$ uv run pytest agents/tests/test_harness_discard.py -q
26 passed in 5.68s
```

### Mutaciones (aplicadas y restauradas byte a byte)

```
[remove_status] pytest exit=1 (mutacion CAZADA)
  4 failed, 22 deselected in 1.52s
[finish_discarded] pytest exit=1 (mutacion CAZADA)
  1 failed, 25 deselected in 0.58s
[block_discarded] pytest exit=1 (mutacion CAZADA)
  1 failed, 25 deselected in 0.95s
[discard_blocked_reason] pytest exit=1 (mutacion CAZADA)
  1 failed, 25 deselected in 0.65s
```

### Suite completa

```
$ uv run pytest -q
1080 passed, 15 skipped in 397.76s (0:06:37)
```

### Lint / tipos / prompts

```
$ uv run ruff check tribal/ tests/ agents/
All checks passed!
$ uv run ruff format --check tribal/ tests/
91 files already formatted
$ uv run mypy tribal/ tests/
Success: no issues found in 91 source files
$ uv run python -m agents.prompts_sync
Prompts y subagentes sincronizados con el código y con los contratos.   (exit 0)
```

### Puerta

```
$ "C:\Program Files\Git\bin\bash.exe" init.sh --json   (exit 0)
{
  "ready": true,
  "errors": 0,
  "warnings": 0,
  ...
  { "status": "ok", "check": "pytest", "detail": "498 passed in 320.68s (0:05:20)" }
}
```

## Qué falta

- Nada bloqueante. Sin commit; temporales borrados. `agents/board.py` no se tocó.
