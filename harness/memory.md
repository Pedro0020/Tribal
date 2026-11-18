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

## Veredicto del modelo local (viabilidad, 2026-11-18)

- **`tribal-llm` decide bien SOLO eligiendo entre acciones candidatas** (6/8 con
  few-shot + temp 0.3), **no generando la acción desde cero** (1/6 con persona,
  2/4 con estado numérico). Sirve para **salida JSON** y **narración en español**.
- **En F2, contrato "candidatas → elige → valida":** las reglas proponen 2–4
  acciones viables, el LLM elige una y la justifica (`razon`/`dialogo`), y el
  motor corrige solo si viola una restricción dura. El instinto se queda lo
  trivial (sed→beber, lobo→huir); el LLM, los dilemas y lo social.
- Datos completos en `vault/01_PROYECTO/viabilidad-modelo.md`. Revisar
  concepto §10/§10b en consecuencia.
- La feature **`F2-CONTRATO`** está en la cola y codifica ese contrato con
  tests; **hacerla antes de `F2-001`** (que es el cliente HTTP de decisiones).

## Funciones de runtime pendientes (requisito del usuario)

Añadir al backlog features para:
- **Guardar y cerrar**: persistencia en SQLite + semilla/estado del RNG +
  `save_meta.json`; reanudar desde el `tick` guardado.
- **Nuevo mundo**: archivar/borrar el `world.db` actual y empezar de cero con
  semilla nueva, **con confirmación explícita** (destructivo).
Diseño en concepto.md §17 y stack-tecnologico.md §5.

## F1-004: la ventaja del divergente no puede ser "por decreto"

Antes de reimplementar la puerta F1→F2, leer
`vault/01_PROYECTO/emergencia-seleccion.md`. Resumen: borrar los 4 canales que
premian el rasgo `divergencia` directamente (penalización al comer, sed extra,
ventaja reproductiva, plasticidad numérica) y corregir la reproducción en crisis
(umbral ≥ calma, sin inyectar energía). La divergencia solo decide conducta; la
aptitud sale de lo que esa conducta produce. La puerta se mide por mecanismo
(descubridor vs no descubridor), no por proporción del rasgo.

**Secuencia para pasar la puerta F1 honestamente (decisión del usuario):**
tras CONNECT-001, DIVERGENCIA-002 y FIX-ENERGIA, implementar **EMER-002**
(utilidad situacional) y **EMER-003** (gradiente ambiental) **antes de F2**, y
reintentar la puerta F1. Sin payoff condicional la selección se diluye (EMER-001
dio 2/10 semillas, casi azar). No saltar a F2 con la puerta sin demostrar.

## Tests conocidos en rojo en Windows (plantilla)

`uv run pytest` deja 16 fallos **preexistentes** de la plantilla en Windows:

- `test_prompts_sync.py` — `read_text()` sin `encoding="utf-8"` (cp1252).
- `test_refactor_scope.py` — separadores `\` vs `/`.
- `test_installer_agent.py` — `shutil.rmtree` sobre objetos `.git` de solo lectura.

No bloquean la puerta (`init.sh` solo ejecuta `tests/`). Su arreglo pertenece a
**QA-001**; no los silencies saltándolos.
