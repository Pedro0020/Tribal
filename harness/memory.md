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

## LLM local (Fase 2): Ollama, no llama.cpp

- El modelo es **`tribal-llm`** (base `qwen2.5:3b-instruct-q8_0`, `num_ctx` 8192,
  temperature 0.7), ya creado en Ollama. Servicio en `http://127.0.0.1:11434`.
  Medido: 66 tok/s, 3,6 GB de VRAM, 100 % GPU.
- **No instales `llama-cpp-python` ni descargues binarios de llama.cpp.** El
  cliente de la simulación es HTTP (`httpx`/`requests`) contra `/api/chat`.
- Salida estructurada: campo `format` con JSON schema (no GBNF).
- Comprobar disponibilidad: `curl.exe http://127.0.0.1:11434/api/tags`.
- **Presupuesto de GPU (obligatorio en F2):** `num_predict` ≤ 32, una
  inferencia en vuelo, ≥ 8 s entre consultas del mismo agente, ≤ 15
  decisiones/minuto, y `keep_alive: "15m"`. Objetivo: ≤ 30 % de ciclo de
  trabajo y < 78 °C. Está detallado en stack-tecnologico.md §8.

## Tests conocidos en rojo en Windows (plantilla)

`uv run pytest` deja 16 fallos **preexistentes** de la plantilla en Windows:

- `test_prompts_sync.py` — `read_text()` sin `encoding="utf-8"` (cp1252).
- `test_refactor_scope.py` — separadores `\` vs `/`.
- `test_installer_agent.py` — `shutil.rmtree` sobre objetos `.git` de solo lectura.

No bloquean la puerta (`init.sh` solo ejecuta `tests/`). Su arreglo pertenece a
**QA-001**; no los silencies saltándolos.
