# implementer · F2-001

- **Fecha:** 2026-11-19
- **Veredicto:** ok

## Qué cambié

- `tribal/llm/__init__.py` — paquete vacío.
- `tribal/llm/esquema.py` — `ACCIONES` derivadas de `get_args(NombreAccion)`, `ESQUEMA_RESPUESTA` con `enum` y campos obligatorios, `Decision`/`ErrorValidacion`, `validar()` y `construir_prompt()` con few-shot.
- `tribal/llm/cliente.py` — `ClienteLLM` (GET `/api/tags`, POST `/api/chat`, `model: tribal-llm`, `format` schema, timeout 3 s), `Resultado` ok/degradado/error sin excepciones, `backend_falso()` determinista y transporte stdlib inyectable.
- `tribal/cli.py` — subcomando `llm selfcheck --json`.
- `tests/conftest.py` — guarda autouse que bloquea `urllib.request.urlopen` en toda la suite de `tests/`.
- `tests/test_llm_esquema.py` — 13 tests del vocabulario, esquema, validación y prompt.
- `tests/test_llm_cliente.py` — 18 tests del cliente, fallos sin excepción, backend falso y selfcheck.
- `README.md` — sección «Capa LLM local» con Ollama, `tribal-llm` y selfcheck.
- `vault/01_PROYECTO/arquitectura.md` — §2.3 (contrato de candidatas, timeout y degradación) y §9 (estado real).

## Criterios de aceptación

1. **`esquema.py` fija el esqueleto y deja libres los textos.**
   `uv run pytest -q tests/test_llm_esquema.py` → `13 passed`.
   Cubre: acción dentro del vocabulario, campos obligatorios, tipos de texto, few-shot.
2. **`cliente.py` habla HTTP con `/api/chat`, `tribal-llm`, `format` y timeout corto.**
   `uv run pytest -q tests/test_llm_cliente.py` → `18 passed`.
   `test_decidir_manda_modelo_formato_y_timeout` comprueba método, URL, `model`, `format` y timeout; `test_disponible_consulta_api_tags` comprueba GET `/api/tags`.
3. **Backend falso determinista; inválido/timeout/caído no lanzan.**
   `backend_falso` consume respuestas en orden; `test_backend_falso_es_determinista_y_secuencial`, `test_decidir_json_roto_es_error_sin_excepcion`, `test_decidir_fallo_de_transporte_degrada_sin_excepcion` y `test_decidir_http_no_200_degrada`.
4. **`llm selfcheck --json` informa disponible true/false sin romper.**
   Con Ollama levantado y sin servicio (puerto 9): salidas abajo; exit 0 en ambos casos.
5. **`uv run pytest -q` no abre red.**
   `tests/conftest.py` parchea `urllib.request.urlopen` para toda la suite; `test_la_suite_no_abre_red` lo verifica y todos los tests del cliente inyectan transporte falso.
6. **Gate en verde.**
   `uv run python -m agents --json run harness gate` → `"success": true`, `ready: true`, `errors: 0`.

## Evidencia

`make` no está en el PATH de esta shell Windows; se ejecutan los comandos equivalentes del Makefile directamente.

### `llm selfcheck --json` (servicio disponible)

```
{"disponible": true, "endpoint": "http://127.0.0.1:11434", "modelo": "tribal-llm", "latencia_ms": 96.4, "error": null}
```

### `llm selfcheck --json --endpoint http://127.0.0.1:9` (sin servicio, exit 0)

```
{"disponible": false, "endpoint": "http://127.0.0.1:9", "modelo": "tribal-llm", "latencia_ms": null, "error": "servicio ca\u00eddo: <urlopen error [WinError 10061] No se puede establecer una conexi\u00f3n ya que el equipo de destino deneg\u00f3 expresamente dicha conexi\u00f3n>"}
```

### Tests del LLM

```
$ uv run pytest -q tests/test_llm_esquema.py
.............                                                            [100%]
13 passed in 0.28s

$ uv run pytest -q tests/test_llm_cliente.py
..................                                                       [100%]
18 passed in 0.30s
```

### `uv run pytest -q` (suite completa)

```
........................................................................ [  8%]
........................................................................ [ 16%]
........................................................................ [ 25%]
........................................................................ [ 33%]
........................................................................ [ 42%]
........................................................................ [ 50%]
........................................................................ [ 58%]
........................................................................ [ 67%]
........................................................................ [ 75%]
..................................................................s.ssss [ 84%]
ssssssss..s............................................................. [ 92%]
........................................................................ [100%]
842 passed, 15 skipped in 219.95s (0:03:39)
```

### `ruff check` / `format --check` / `mypy`

```
$ uv run ruff check tribal/ tests/ agents/
All checks passed!

$ uv run ruff format --check tribal/ tests/
55 files already formatted

$ uv run mypy tribal/ tests/
Success: no issues found in 55 source files
```

### `./init.sh`

```
━━ init.sh · arnés de Tribal ━━

Entorno
  ✔ python                 ./.venv/Scripts/python.exe 3.12
  ✔ uv                     uv 0.10.7 (08ab1a344 2026-02-27)
  ✔ venv                   .venv presente

Arnés
  ✔ AGENTS.md              presente
  ✔ featureslist.json      presente
  ✔ current.md             presente
  ✔ history.md             presente
  ✔ subagentes             lider, implementer, reviewer, explorer

Backlog
  ✔ featureslist           43 features · 20 pending · 1 in_progress · 19 done · 3 blocked
  ✔ siguiente tarea        F2-001 — Cliente LLM HTTP con esquema de acciones [in_progress]

Proyecto
  ✔ paquete                tribal/ presente (project.yml)
  ✔ pyproject              presente
  ✔ tests                  24 ficheros de test

Verificación
  ✔ pytest                 286 passed in 155.91s (0:02:35)

━━ ENTORNO LISTO ━━  0 aviso(s)
Puedes trabajar. Siguiente paso: lee harness/progress/current.md y elige la primera feature pendiente.
```

### `harness gate`

```
{
  "success": true,
  "agent": "harness",
  "action": "gate",
  "message": "ENTORNO LISTO — se puede trabajar.",
  "data": {
    "ready": true,
    "errors": 0,
    "warnings": 0,
    "checks": [
      {"status": "ok", "check": "python", "detail": "./.venv/Scripts/python.exe 3.12"},
      {"status": "ok", "check": "uv", "detail": "uv 0.10.7 (08ab1a344 2026-02-27)"},
      {"status": "ok", "check": "venv", "detail": ".venv presente"},
      {"status": "ok", "check": "AGENTS.md", "detail": "presente"},
      {"status": "ok", "check": "featureslist.json", "detail": "presente"},
      {"status": "ok", "check": "current.md", "detail": "presente"},
      {"status": "ok", "check": "history.md", "detail": "presente"},
      {"status": "ok", "check": "subagentes", "detail": "lider, implementer, reviewer, explorer"},
      {"status": "ok", "check": "featureslist", "detail": "43 features · 20 pending · 1 in_progress · 19 done · 3 blocked"},
      {"status": "ok", "check": "siguiente tarea", "detail": "F2-001 — Cliente LLM HTTP con esquema de acciones [in_progress]"},
      {"status": "ok", "check": "paquete", "detail": "tribal/ presente (project.yml)"},
      {"status": "ok", "check": "pyproject", "detail": "presente"},
      {"status": "ok", "check": "tests", "detail": "24 ficheros de test"},
      {"status": "ok", "check": "pytest", "detail": "286 passed in 151.95s (0:02:31)"}
    ]
  },
  "warnings": [],
  "needs": []
}
```

## Qué falta

- La cola asíncrona, la selección por saliencia y la aplicación diferida son F2-002; no se tocó `sim.py` ni el bucle.
- El `tribal.Modelfile` no vive en el repo: el README explica que `tribal-llm` se crea con `ollama create` a partir de la base `qwen2.5:3b-instruct-q8_0`.
