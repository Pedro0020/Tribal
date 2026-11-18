# implementer · DESIGN-001

- **Fecha:** 2026-11-18
- **Veredicto:** ok

# implementer - DESIGN-001 (ronda 3: id del modelo LLM)

Veredicto: ok

## Que cambie

Solo `vault/01_PROYECTO/arquitectura.md`, 2 puntos. Ni codigo ni nada mas.

1. **Lineas 69-72 (§2.3, `cliente.py`)**: el cliente HTTP manda
   `model: tribal-llm`, no el id base. Anadido en la misma frase que
   `tribal-llm` es el alias del Modelfile y arranca con `num_ctx 8192`; el
   endpoint (`http://127.0.0.1:11434/api/chat`), el campo `format` y el timeout
   no cambian.
2. **Lineas 377-379 (§9, capa LLM que aun no existe)**: donde antes decia que
   el modelo era `qwen2.5:3b-instruct-q8_0`, ahora dice que el id que usa el
   codigo es `tribal-llm` y aclara en media linea que el base
   `qwen2.5:3b-instruct-q8_0` es solo el `FROM` del Modelfile, no el id del
   cliente; `num_ctx 8192`; el propio `tribal-llm` vive en el almacen de
   Ollama, fuera del repo.

Nada mas tocado: ni §1, ni §2.1/2.4/2.5/2.6, ni §4 (tabla de dependencias), ni
§5-§8, ni §10.

## Relectura del documento (394 lineas)

- grep de `qwen2.5|tribal-llm`: 4 lineas, 70 y 377-379. Las dos primeras son
  `tribal-llm` como id del cliente; las otras dos son el `FROM` y la aclaracion
  de que el base no es el id. Ninguna mencion usa el base como id.
- grep de `num_ctx|4096`: solo 71 y 378, ambos `num_ctx 8192`. No queda ninguna
  mencion a 4096 ni a un contexto por defecto: el documento asume el 8192 del
  Modelfile en los dos sitios donde el contexto importa (cliente y estado).
- Coherente con `stack-tecnologico.md:15,69-80,249` (alias `tribal-llm`,
  `FROM qwen2.5:3b-instruct-q8_0`, `num_ctx 8192`, `keep_alive` 15 min).

## Evidencia

`uv run python -m agents --json run harness gate` (exit=0):

```text
"success": true,
"ready": true,
"errors": 0,
"warnings": 0,
"detail": "7 passed in 0.30s"
```

`git grep --no-index -n -E "qwen2\.5|tribal-llm" -- vault/01_PROYECTO/arquitectura.md`:

```text
vault/01_PROYECTO/arquitectura.md:70:  `POST http://127.0.0.1:11434/api/chat` contra Ollama con `model: tribal-llm`
vault/01_PROYECTO/arquitectura.md:377:  Fase 0-1 no lo necesite. El id que usa el codigo es `tribal-llm` (Modelfile
vault/01_PROYECTO/arquitectura.md:378:  `FROM qwen2.5:3b-instruct-q8_0` con `num_ctx 8192`; el base es solo el
vault/01_PROYECTO/arquitectura.md:379:  `FROM`, no el id del cliente); el propio `tribal-llm` vive en el almacen de
```

(El binario `grep` no existe en este PowerShell; `git grep --no-index` da la
misma salida con numero de linea.)

`git status --short`: solo los cambios ya existentes de la feature, ninguno
nuevo fuera de `vault/01_PROYECTO/arquitectura.md`.

## Que falta

- Sigue fuera de alcance: RAG ciego (`agents/tools/rag_tool.py:601`),
  `pygame-ce` sin declarar (CORE-001), `project_version` 0.1.0 vs 0.1.1,
  `vault/.obsidian/workspace.json` sin trackear.
- El KPI (§1 prosa vs §8 consulta) queda como esta: es herencia literal de
  `objetivo.md` §3.2 y decidir si `llm` cuenta no es de esta feature.
