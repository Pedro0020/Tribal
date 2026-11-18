# reviewer · DESIGN-001

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

# reviewer · DESIGN-001 (ronda 3)

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

## Criterios

1. **Piezas y flujo entre ellas — CUMPLIDO.** §2 (lineas 31-112) describe las
   seis piezas con carpeta y fase; §3 (lineas 116-134) da el flujo por frame:
   `RELOJ dt = 1/60 s`, `DECIDIR ... instinto.elegir(...)`, `ENCOLAR ... no
   bloquea: es un put_nowait con cola acotada`, `EVENTOS -> nodos de cultura
   (con su origen)`, `DRENAR ... get_nowait`, `DIBUJAR ... <-- aqui no hay
   ninguna llamada LLM`. La invariante de §1 sigue literal: "El LLM nunca se
   llama desde el hilo de render".
2. **Alternativa descartada con motivo — CUMPLIDO.** §5.1-5.6 (lineas
   219-298), cada una con motivo y disparador de reapertura.
3. **Riesgos y decisiones diferidas — CUMPLIDO.** §6 (10 riesgos con
   mitigacion, lineas 302-317) y §7 (7 decisiones aplazadas con cuando,
   lineas 321-334).
4. **Renombrado coherente — CUMPLIDO.** `uv run python -m tribal hello` ->
   `Hola, mundo.`; `project.yml:10 project_slug: tribal`; `Makefile:15 MODULE =
   tribal`; `pyproject.toml:43 tribal = "tribal.cli:main"`, `:50 packages =
   ["tribal"]`, `:82 source = ["tribal"]`; `git status --short` conserva los
   cuatro `RM app/* -> tribal/*`; `app/` no existe; 0 coincidencias de
   `from app`, `import app`, `"app"`, `app/`, `--cov=app` en tests/, tribal/,
   pyproject.toml, Makefile, project.yml, README.md y .pre-commit-config.yaml.
5. **Puerta en verde — CUMPLIDO.** Ejecutada en esta ronda:
   `"success": true`, `"message": "ENTORNO LISTO - se puede trabajar."`,
   `"ready": true`, `"errors": 0`, `"warnings": 0`, `pytest: 7 passed`.

## Bloqueantes

Ninguno.

## Verificado en el fichero real

- **Bloqueante ronda 2 resuelto.** `arquitectura.md:70-72`:
  "`POST http://127.0.0.1:11434/api/chat` contra Ollama con `model: tribal-llm`
  (el alias del Modelfile, que es el que arranca con `num_ctx 8192`), el campo
  `format` (JSON schema) y timeout corto".
  `arquitectura.md:377-380`: "El id que usa el codigo es `tribal-llm`
  (Modelfile `FROM qwen2.5:3b-instruct-q8_0` con `num_ctx 8192`; el base es
  solo el `FROM`, no el id del cliente)".
- **Coherencia con el stack, comprobada linea a linea:**
  `stack-tecnologico.md:15` (`Ollama (tribal-llm, base qwen2.5-3B Q8_0, ctx
  8192)`), `:69` (`FROM qwen2.5:3b-instruct-q8_0`), `:70` (`PARAMETER num_ctx
  8192`), `:77` (`ollama create tribal-llm -f tribal.Modelfile`), `:80`
  ("Identificador del modelo en el codigo: `tribal-llm`"), `:249` (`ollama
  stop tribal-llm`). Cero contradicciones; el id base solo aparece como `FROM`.
- **`num_ctx` solo en dos sitios y ambos 8192:** lineas 71 y 378 (grep sobre
  todo el documento; no hay otra aparicion).
- **Bloqueantes de la ronda 1 siguen corregidos:** linea 174
  (`core` -> solo stdlib/core.modelos; `agents` en "no puede importar", sin
  ciclo, coherente con la regla "las flechas no vuelven" de la 162); export con
  dueño unico `tribal/store/export.py` en lineas 39, 102-104, 111, 204 y 383;
  espejo SQLite escrito por `store` en §2.4 (lineas 84-85).
- **Sin cambios fuera de esas zonas:** §4 (lineas 162-207) intacta; §6, §7, §8
  y §10 intactas; el resto de la feature igual que en la ronda 2.

## Evidencia ejecutada esta ronda

```
uv run python -m agents --json run harness gate
"success": true   "ready": true   "errors": 0   "warnings": 0
pytest: 7 passed in 0.36s

uv run python -m tribal hello
Hola, mundo.

uv run python -m pytest tests -q
7 passed in 0.29s

uv run ruff check tribal/ tests/
All checks passed!

uv run ruff format --check tribal/ tests/
7 files already formatted

uv run mypy tribal/ tests/
Success: no issues found in 7 source files
```

`review review_package`: 4 archivos, 0 hallazgos. `agents/`: `git status` y
`git diff --stat` vacios. `app/` no existe y `git ls-files app` vacio. Sin
`.tmp-*`. `harness/featureslist.json` y `current.md` siguen siendo salida del
agente `harness`.

## No bloqueante

- `arquitectura.md:71` llama "alias del Modelfile" a `tribal-llm`; en Ollama un
  `ollama create` produce un modelo derivado, no un alias (`ollama cp`). La
  afirmacion operativa (arranca con `num_ctx 8192`) es correcta; sugerencia de
  redaccion, no defecto.
- Riesgo 8 (linea 313) sigue pidiendo "medir VRAM real antes de Fase 2" cuando
  el stack ya mide 3,6 GB y 95 %; acotarlo a "con embeddings cargados" en una
  pasada futura.
- KPI (§8): la prosa dice "origen distinto de arbol" y la consulta cuenta solo
  `combinacion`/`interaccion`; herencia literal de `objetivo.md` §3.2.
- `project.yml project_version: 0.1.0` frente a `pyproject 0.1.1`, e
  `IA_index.md` con 0.1.0: preexistente, fuera de alcance.
- `vault/.obsidian/workspace.json` sin trackear (lo genera Obsidian).
