# Memory

Instrucciones, correcciones y preferencias guardadas por el usuario para
recordar en futuras sesiones. Este archivo lo lee el agente al inicio de
cada sesión — cualquier anotación aquí persiste entre sesiones.

---

## Entorno: Windows 11, sin `make`

- **`make` no está instalado.** Usa los equivalentes con `uv`:
  - `make setup` → `uv sync --extra dev` + `uv run pre-commit install`
  - `make init` → `uv run python -m agents --json run harness gate`
  - `make test` → `uv run pytest`
  - `make check` → `uv run ruff check app/ tests/ agents/` + `uv run ruff format --check app/ tests/` + `uv run mypy app/ tests/` + `uv run pytest` + `bash init.sh --quick`
- **`bash` del PATH es el de WSL y está roto.** Usa Git Bash
  (`C:\Program Files\Git\bin\bash.exe`). El agente `harness` ya lo resuelve solo;
  desde la terminal, ejecuta la puerta con `uv run python -m agents ... run harness gate`
  en vez de `./init.sh`.
- **Python del proyecto: 3.12** (`.python-version`). El `python3` del sistema es 3.13;
  no lo uses para el proyecto.

## Tests conocidos en rojo en Windows (plantilla)

`uv run pytest` deja 16 fallos **preexistentes** de la plantilla en Windows:

- `test_prompts_sync.py` — `read_text()` sin `encoding="utf-8"` (cp1252).
- `test_refactor_scope.py` — separadores `\` vs `/`.
- `test_installer_agent.py` — `shutil.rmtree` sobre objetos `.git` de solo lectura.

No bloquean la puerta (`init.sh` solo ejecuta `tests/`). Su arreglo pertenece a
**QA-001**; no los silencies saltándolos.
