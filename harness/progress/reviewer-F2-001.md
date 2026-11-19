# reviewer · F2-001

- **Fecha:** 2026-11-19
- **Veredicto:** aprobado

## Criterios

1. **`esquema.py` fija el esqueleto y deja libres los textos — CUMPLIDO.**
   `ACCIONES = get_args(NombreAccion)` se **deriva**, no se duplica: comprobado
   que `ACCIONES == get_args(NombreAccion)` (11) y que el `enum` del schema es
   idéntico. Pruebas propias de validación:
   `accion:"volar"` → `ErrorValidacion("accion fuera del vocabulario: 'volar'")`;
   falta `razon` → `falta 'razon' o no es texto`; `razon:5` → idem;
   `accion:3` → `falta 'accion' o no es texto`; lista en vez de objeto → error.
   Texto libre aceptado: `objetivo:"una charca verde con juncos"`,
   `razon:"¿por qué no?"`, `dialogo:"«agua» dice"` → `Decision('beber')`.
   `required` = accion+3 textos, `additionalProperties:false`.

2. **`cliente.py`: `/api/chat`, `tribal-llm`, `format` schema, timeout corto — CUMPLIDO.**
   Verificado con transporte inyectado: POST `http://127.0.0.1:11434/api/chat`,
   `model:"tribal-llm"`, `format == ESQUEMA_RESPUESTA`, `temperature 0.3`,
   `stream:false`. Timeout: el transporte real pasa `timeout=3.0` a
   `urlopen` (medido); con servidor que acepta y calla y `timeout=0.5`, `decidir`
   devuelve `degradado` en **0.544 s** de reloj → el corte lo aplica el socket,
   no un contador de mentira. No importa pygame (`'pygame' in sys.modules` → False).

3. **Backend falso; inválido/timeout/caído no lanzan — CUMPLIDO.**
   Inyectados uno a uno: ok→`ok`; JSON roto en `content`→`error "el contenido no es JSON"`;
   `TimeoutError`→`degradado`; `URLError(connection refused)`→`degradado`;
   HTTP 500→`degradado`; sobre no-JSON→`error`; sin `message`→`error`.
   **Ninguna excepción escapó** en ningún caso. `backend_falso` consume en orden
   (test de secuencialidad presente) y `decidir([])` corta sin llamar al transporte.

4. **`llm selfcheck --json` sin romper — CUMPLIDO.**
   Con Ollama real levantado: `{"disponible": true, "endpoint":
   "http://127.0.0.1:11434", "modelo": "tribal-llm", "latencia_ms": 36.3,
   "error": null}`, **exit 0**. Con endpoint muerto `127.0.0.1:9`:
   `disponible:false`, `latencia_ms:null`, `error:"servicio caído: <urlopen error
   [WinError 10061] ...>"`, **exit 0 y sin traza**. Usa `GET /api/tags` y sí mide
   latencia (`perf_counter`).

5. **La suite no hace red — CUMPLIDO (verificado por mí, no solo leído).**
   `tests/conftest.py` es fixture `autouse` que sustituye
   `urllib.request.urlopen` por un lanzador de `AssertionError`. Creé un test
   temporal que llama a `urlopen` real: pasó el `pytest.raises` con el mensaje
   «la suite no debe abrir red» → la guarda muerde; fichero eliminado después
   (`git status -- tests/` solo muestra los 3 ficheros del feature).
   Además, `importlib.reload(urllib.request)` con socket que no responde
   confirma que el producto sí usa HTTP real solo cuando no hay inyección.

6. **Gate `success=true` — CUMPLIDO.** Ejecutado en esta sesión:
   `success: true`, `ready: true`, `errors: 0`, `warnings: 0`,
   `pytest 286 passed in 156.98s`, exit 0.

**Regresiones (verificadas en esta sesión):** suite completa propia
`uv run pytest -q` → **842 passed, 15 skipped in 219.93s, exit 0** (coincide con
el informe). `ruff check` y `ruff format --check` sobre lo tocado → limpio.
`mypy` sobre `tribal/llm/` + tests nuevos → `Success: no issues found`. Prompt
few-shot determinista (misma entrada → mismo JSON con `sort_keys`).
`review_package` no señala nada nuevo en `tribal/llm/`; `secrets scan` no
encuentra nada en los ficheros del feature.

**Alcance:** `pyproject.toml` sin tocar (cero deps nuevas; solo stdlib),
`tribal/sim.py`, `tribal/core/`, `tribal/agents/` sin cambios, sin `.tmp-*`.
Los cambios en `harness/featureslist.json` y `current.md` son el formato exacto
que escribe `harness start` (`started`, `review_rounds`), no edición a mano.
`secrets scan` da 13 hallazgos, todos fixtures preexistentes de
`agents/tests/test_redaction.py` y `test_secrets_agent.py`: ninguno del diff.

**Contrato de candidatas:** ya preparado en esta feature — el system prompt dice
«No inventes una acción: elige exactamente una de las acciones candidatas», el
prompt lista las candidatas y `decidir()` rechaza una acción válida que no esté
entre ellas (`accion fuera de candidatas`). Falta el filtro 2–4 y la generación
de candidatas, que son de `F2-CONTRATO`.

## Bloqueantes

_(ninguno)_

## No bloqueante

1. **`selfcheck` no comprueba que `tribal-llm` exista.** Solo mira HTTP 200 de
   `/api/tags`; el campo `modelo` es un eco del argumento. Hoy `/api/tags`
   devuelve `tribal-llm` y `qwen2.5:3b-instruct-q8_0`, pero si alguien borra el
   modelo, `selfcheck` seguiría diciendo `disponible:true` y la primera decisión
   fallaría con `http 404`. Arreglo barato: parsear `models[].name` y añadir
   `modelo_presente`, o devolver `disponible:false` con `error:"modelo ausente"`.
2. **README pide un fichero que no existe.** `ollama create tribal-llm -f
   tribal.Modelfile` y no hay `tribal.Modelfile` en el repo (buscado en todo el
   árbol). Quien clone no puede reproducir el modelo. Añadir el Modelfile o
   escribir los parámetros inline.
3. **`validar()` acepta campos extra.** El schema lleva
   `additionalProperties:false` (Ollama lo respeta), pero un dict con una clave
   de más pasa la validación Python. Si el validador va a ser la última puerta
   antes del motor, conviene rechazar extras ahí también.
4. **Candidatas fuera de 2–4 no se rechazan** en `decidir()`; se delega en
   quien llama. Es lo que toca (`F2-CONTRATO`), pero el día que la cola de
   F2-002 llame con 8 candidatas nadie se quejará.
5. **`vault/01_PROYECTO/arquitectura.md` es del agente `knowledge`** según la
   tabla de `AGENTS.md`; el implementer lo editó directamente. El contenido es
   correcto y útil, pero si la propiedad se toma en serio, ese cambio debería
   pasar por el agente dueño.
6. **Falso positivo del escáner:** marca «TODO» en `cliente.py:40` dentro de
   «(mé**todo**, url, cuerpo…)». Cosmético; no requiere acción.
7. **`current.md` sigue con las casillas sin marcar y bitácora
   «(pendiente)».** Es de `harness`; el cierre con `harness finish` debería
   reflejar la evidencia.
