# Historial del arnés

Registro append-only de features completadas. Es el changelog del trabajo hecho
por agentes: qué se cerró, con qué evidencia y qué quedó pendiente.

Formato de cada entrada:

```
## <FEATURE-ID> — <título>

- **Cerrada:** YYYY-MM-DD
- **Verificación:** ./init.sh en verde · N tests pasando
- **Cambios:** rutas de los ficheros tocados
- **Decisiones:** lo que se eligió y por qué (solo si no es obvio desde el código)
- **Pendiente:** lo que se dejó fuera a propósito
```

---

_(sin features completadas todavía — el proyecto acaba de empezar)_

## BOOT-001 — Arranque en frio operativo: contratos inline + agente bootstrap

- **Cerrada:** 2026-08-04
- **Verificación:** ./init.sh en verde · 6 passed in 0.31s
- **Cambios:** agents/agents/bootstrap_agent.py; agents/prompts/bootstrap_agent.md (nuevo); agents/tests/test_bootstrap_agent.py (nuevo, 20 tests); agents/tests/test_contracts.py (+6 tests de contratos inline); conteo 23->24 y ficha de bootstrap en README.md, AGENTS.md, agents/README.md, agents/prompts/agents_reference.md, agents/prompts/orchestrator.md, .opencode/agents/orquestador.md, .opencode/agents/lider.md, .claude/agents/lider.md (regenerado)
- **Decisiones:** BootstrapAgent.describe() tapaba BaseAgent.describe() y reventaba 'python -m agents list' con TypeError. Arreglo: el metodo pasa a llamarse describe_project y la clave de accion sigue siendo 'describe', asi que la CLI no cambia. Queda un test de regresion generico sobre list_agents(). Pendientes reportados y NO tocados: (a) 'describe' esta en destructive, asi que el criterio de ONBOARD-001 tal como esta escrito en TICKETS_ARRANQUE es infalsable sin --yes; (b) status devuelve first_run=true en este repo pese a tener 7 features, relevante para BOOT-003; (c) el conteo de agentes en los docs se escapo dos veces: candidato a check en init.sh.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ make check
uv run ruff check app/ tests/ agents/
All checks passed!
uv run ruff format --check app/ tests/
6 files already formatted
uv run mypy app/ tests/
Success: no issues found in 6 source files
  typecheck OK
uv run pytest
======================= 490 passed, 15 skipped in 16.99s =======================
  check pasado: lint + typecheck + test + arnes OK
EXIT=0

$ uv run python -m agents.prompts_sync
Prompts y subagentes sincronizados con el codigo y con los contratos.
PROMPTS_EXIT=0

$ uv run python -m agents list | wc -l
24
```

</details>

## BOOT-002 — installer scaffold: creador de agentes autocontenidos

- **Cerrada:** 2026-08-04
- **Verificación:** ./init.sh en verde · 6 passed in 0.35s
- **Cambios:** agents/tools/agent_scaffold_tool.py (nuevo: AgentSpec + AgentScaffoldTool); agents/agents/installer_agent.py (accion scaffold); agents/contracts.py (solo el contrato de installer: scaffold en destructive); agents/prompts/installer_agent.md (prosa sobre scaffold + AUTOGEN); agents/tests/test_installer_scaffold.py (nuevo, 22 tests)
- **Decisiones:** El generador no puede reproducir el bug de BOOT-001: si una ACCION colisiona con un metodo de BaseAgent renombra el METODO (describe -> describe_action) y conserva el nombre de la accion; si el NOMBRE DEL AGENTE colisiona, rechaza. Verificado generando un agente con acciones describe/run/actions/can_handle: 'python -m agents list' sigue en exit 0. La logica de renderizado va en agents/tools/agent_scaffold_tool.py y no dentro del agente, siguiendo la convencion que declara _template_agent.py. owns con recurso ya adueñado se rechaza en validar(), no solo en validate_contracts(). name y description tienen default '' en vez de ser obligatorios para devolver success=False + needs en vez de un TypeError en la CLI (patron de git.commit_feature). DEUDA ANOTADA, no tocada: agents/permissions.py:70 decide con 'not kwargs.get(dry_run)', mirando los kwargs recibidos y no el default de la firma, asi que scaffold sin --dry_run explicito queda bloqueado por la puerta aunque no fuera a escribir nada. Falla del lado seguro; arreglarlo cambia la puerta para los 24 agentes y es feature aparte.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ make check
uv run ruff check app/ tests/ agents/
All checks passed!
uv run ruff format --check app/ tests/
6 files already formatted
uv run mypy app/ tests/
Success: no issues found in 6 source files
  typecheck OK
uv run pytest
======================= 512 passed, 15 skipped in 11.31s =======================
  check pasado: lint + typecheck + test + arnes OK
CHECK_EXIT=0

$ uv run python -m agents.prompts_sync
Prompts y subagentes sincronizados con el codigo y con los contratos.
P_EXIT=0

$ ls agents/external/   -> __init__.py  README.md  (ningun agente generado suelto)

Prueba de fuego del reviewer sobre una COPIA del repo, generando agentes reales con --dry_run false --yes:
  1 agente generado  -> make check: 517 passed, exit 0
  3 agentes generados -> make check: 535 passed, exit 0
  ./init.sh completo  -> ENTORNO LISTO, 0 avisos
  dry-run: md5 de todo el arbol identico antes/despues (solo cambia agents/workspace/audit/audit.jsonl, el log de BaseAgent.run)
  barrido AST: las 14 llamadas a AgentResult de los modulos generados tienen success=False, y las 14 acciones fallan con needs no vacio
```

</details>

## BOOT-004 — knowledge sync_agent_cards: las fichas del vault desde los contratos

- **Cerrada:** 2026-08-04
- **Verificación:** ./init.sh en verde · 6 passed in 0.34s
- **Cambios:** agents/agents/knowledge_agent.py (accion sync_agent_cards + helpers); agents/contracts.py (knowledge.destructive); agents/permissions.py (_es_dry_run resuelve el defecto de la firma); agents/core/base_agent.py (1 linea: pasa el metodo a la puerta); agents/prompts_sync.py (_splice acepta begin/end, reutilizado); agents/tests/test_knowledge_agent.py (+6 tests); agents/tests/test_permissions.py (+2 tests); agents/prompts/knowledge_agent.md; README.md; vault/05_AGENTES/ (24 fichas + fila de bootstrap en _index.md)
- **Decisiones:** El contrato de knowledge prometia desde el principio 'poblar vault/05_AGENTES/ con fichas desde contracts.py' y eso nunca estuvo implementado: un contrato que miente. Esta feature nace de ese hallazgo al bloquear BOOT-003. Las fichas se generan desde all_contracts() (no CONTRACTS) para que los agentes de contrato inline como bootstrap tengan ficha. El nombre de fichero sale de cls.__name__ y no del name del agente, para respetar la convencion existente (GitAgent.md, APIAgent.md). La prosa a mano de las fichas se conserva con el _splice de prompts_sync, reutilizado en vez de duplicado. _index.md NO se autogenera (agrupa por categorias humanas y lleva un mermaid que el contrato no contiene): la accion lo audita y avisa. Las fichas huerfanas se reportan, no se borran. EFECTO EN LA CAPA COMPARTIDA: marcar sync_agent_cards como destructive dejaba su propio dry-run pidiendo confirmacion, asi que se arreglo la puerta (agents/permissions.py) para que resuelva el defecto de la firma y no solo los kwargs recibidos. Acerca el codigo a lo que AGENTS.md ya documentaba ('un --dry-run nunca pregunta'). Auditadas las 14 acciones destructivas: ninguna irreversible perdio su confirmacion. AVISO: la revision del subagente reviewer se corto por limite de gasto de la API sin emitir veredicto; el bloque critico lo verifico el lider y lo que quedo sin revisar esta listado en harness/progress/reviewer-BOOT-004.md.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ make check
All checks passed!
6 files already formatted
Success: no issues found in 6 source files
  typecheck OK
======================= 520 passed, 15 skipped in 51.35s =======================
  check pasado: lint + typecheck + test + arnes OK
CHECK_EXIT=0

$ uv run python -m agents.prompts_sync
Prompts y subagentes sincronizados con el codigo y con los contratos.  P_EXIT=0

$ ./init.sh
  pytest  6 passed in 0.55s
  ENTORNO LISTO  0 aviso(s)

$ run knowledge sync_agent_cards            (dry-run)  -> md5 del arbol de vault/ identico antes y despues
$ run knowledge sync_agent_cards --dry_run false --yes  -> 24 fichas sincronizadas
$ segunda pasada real -> 0 nuevas, 0 actualizadas, 24 sin cambios; md5 identico (idempotente)
$ md5 de vault/ identico antes y despues de make check -> la suite no toca el vault real
$ ls vault/05_AGENTES/*.md | wc -l -> 25 (24 fichas + _index.md); BootstrapAgent.md presente

Auditoria de la puerta de permisos (14 acciones destructivas, ejecutada):
  las 12 acciones irreversibles siguen pidiendo confirmacion sin argumentos;
  solo installer.scaffold y knowledge.sync_agent_cards (dry_run=True por defecto) no la piden,
  y ambas la piden con dry_run=False explicito. No se abrio agujero.
```

</details>

## BOOT-003 — Protocolo de arranque en frio en el lider + documentacion

- **Cerrada:** 2026-08-04
- **Verificación:** ./init.sh en verde · 6 passed in 0.41s
- **Cambios:** .opencode/agents/lider.md (paso 0 + seccion de arranque en frio); .claude/agents/lider.md (regenerado con assistants-sync, no a mano); agents/agents/bootstrap_agent.py (criterio de ONBOARD-001 en TICKETS_ARRANQUE: --yes); agents/README.md (seccion installer scaffold); AGENTS.md (paso 0 + seccion Arranque en frio); harness/featureslist.json via bootstrap seed --yes (ONBOARD-001 y ONBOARD-002)
- **Decisiones:** La feature estuvo BLOQUEADA: el criterio del vault no era alcanzable porque ninguna accion escribia vault/05_AGENTES/ pese a que el contrato de knowledge lo prometia. Se abrio BOOT-004 para implementarlo y se reabrio esta. Sobre la puerta: se decidio NO sacar 'describe' de destructive (escribir la identidad del proyecto merece confirmacion y la puerta falla del lado seguro); lo que se arreglo fue el criterio de ONBOARD-001, que sin --yes era infalsable. El ciclo de arranque en frio deja explicito en el prompt del lider que las preguntas de 'describe' son para el usuario y no se deducen del codigo, y que suggest_agents da candidatos lexicos y no un veredicto. PENDIENTE DE DECISION DEL USUARIO: SCOPE-001 se solapa con ONBOARD-001 (los dos producen el objetivo del proyecto en el vault); no se borro nada porque harness no tiene accion de borrado y la decision es del usuario.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ make check
All checks passed!
6 files already formatted
Success: no issues found in 6 source files
  typecheck OK
================= 520 passed, 15 skipped in 188.32s (0:03:08) ==================
  check pasado: lint + typecheck + test + arnes OK
CHECK_EXIT=0

$ ./init.sh
  ENTORNO LISTO  0 aviso(s)

$ uv run python -m agents.prompts_sync
Prompts y subagentes sincronizados con el codigo y con los contratos.
(esto cubre tambien que .claude/agents/lider.md esta sincronizado con .opencode/agents/lider.md)

$ grep -n "Paso 0" .opencode/agents/lider.md
14: uv run python -m agents --json run bootstrap status
15: #   first_run=false -> sigue en el paso 1
16: #   first_run=true  -> arranque en frio antes de abrir ninguna feature
46: ## Paso 0 - arranque en frio
85: **Condicion de salida:** run bootstrap status devuelve description_pending: false

$ backlog
ONBOARD-001    pending      Entender el proyecto
ONBOARD-002    pending      Que se sabe ya y que agentes hacen falta

$ criterio de ONBOARD-001 corregido
uv run python -m agents run bootstrap describe --description \"<respuesta del usuario>\" --yes devuelve success=true

$ agents/README.md: linea 77 \"los 24 agentes\", linea 205 seccion \"installer scaffold\", linea 238 \"Los 24 agentes\"
$ AGENTS.md: linea 15 paso 0 en el bloque de protocolo, linea 26 seccion \"Arranque en frio\"
$ vault/05_AGENTES/BootstrapAgent.md presente con el contrato inline (generado por knowledge sync_agent_cards en BOOT-004)
```

</details>

## FIX-001 — app.__main__ rompe los imports: falta la guarda __name__

- **Cerrada:** 2026-08-04
- **Verificación:** ./init.sh en verde · 7 passed in 0.13s
- **Cambios:** app/__main__.py (guarda if __name__ == '__main__'); tests/test_main_import.py (nuevo: test de regresion que importa app.__main__ y barre el paquete)
- **Decisiones:** El test importa app.__main__ a nivel de modulo: si la guarda regresa, pytest muere en coleccion con SystemExit(2) y no solo falla un caso. Diagnosticado el alcance: pkgutil.walk_packages(app.__path__) importa app.__main__, por eso barrer el paquete mataba el proceso.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -c "import app.__main__; print('ok')"  ->  ok, EXIT=0 (sin usage)
$ uv run python -m pytest tests/ -q --no-header        ->  7 passed in 0.40s
$ uv run python -m app hello                           ->  Hola, mundo. EXIT=0
$ make check                                           ->  check pasado: lint + typecheck + test + arnes OK
$ ./init.sh                                            ->  ENTORNO LISTO  0 aviso(s)
```

</details>

## SCOPE-001 — Definir qué se quiere resolver

- **Cerrada:** 2026-11-18
- **Verificación:** ./init.sh en verde · 7 passed in 0.33s
- **Cambios:** vault/01_PROYECTO/objetivo.md (nuevo); README.md (frase de objetivo, tabla de documentacion y enlace al KPI); harness/progress/implementer-SCOPE-001.md; harness/progress/reviewer-SCOPE-001.md
- **Decisiones:** objetivo.md destila concepto.md y stack-tecnologico.md, no anade decisiones. El KPI de emergencia usa como denominador TODOS los nodos activos (no solo los de nivel 1-2), porque excluirlos daria 100 por construccion; umbral >= 50 por ciento. El criterio de hecho se comprueba con una consulta SQL concreta sobre la BD de la partida y un test del repo, no con una impresion. Rechazo de la ronda 1: se revirtieron pygame-ce de pyproject/uv.lock (su dueno es CORE-001) y se re-grabo el informe del implementer en ASCII; causa raiz del truncado de harness record anotada para QA-001.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
{
  "success": true,
  "agent": "harness",
  "action": "gate",
  "message": "ENTORNO LISTO - se puede trabajar.",
  "data": {
    "ready": true,
    "errors": 0,
    "warnings": 0,
    "checks": [ ... 14/14 ok ..., { "check": "featureslist", "detail": "4 features - 3 pending - 1 in_progress - 0 done - 0 blocked" }, { "check": "pytest", "detail": "7 passed in 3.24s" } ]
  }
}
$ Select-String -Pattern '^## ' vault/01_PROYECTO/objetivo.md
## 1. Problema
## 2. Usuario / consumidor
## 3. Criterio de hecho
## 4. Fuera de alcance
```

</details>

## DESIGN-001 — Decidir cómo se va a resolver

- **Cerrada:** 2026-11-18
- **Verificación:** ./init.sh en verde · 7 passed in 0.32s
- **Cambios:** vault/01_PROYECTO/arquitectura.md (nuevo, 394 lineas); app/ renombrado a tribal/ (4 ficheros, git mv); project.yml; pyproject.toml; Makefile; .pre-commit-config.yaml; tests/test_cli.py; tests/test_main_import.py; tests/test_paths.py; docs/source/index.rst; README.md; vault/00_META/IA_index.md; vault/01_PROYECTO/stack-tecnologico.md y harness/memory.md (alineados a Ollama/tribal-llm); uv.lock; harness/progress/{explorer,implementer,reviewer}-DESIGN-001.md
- **Decisiones:** Paquete renombrado app -> tribal con git mv; project_slug, scripts, hatch, coverage y MODULE coherentes; PACKAGE_DIR se deriva de __file__. arquitectura.md fija tres invariantes: el LLM nunca en el hilo de render, motor determinista por (semilla, config, orden de ticks) y cultura como grafo persistido. El backend LLM queda como cliente HTTP (Ollama, model tribal-llm con num_ctx 8192) y no como llama-cpp-python en proceso: es la decision que aparecio documentada en stack-tecnologico.md y harness/memory.md durante la feature, y la arquitectura se alineo a ella; llama-server/llama-cpp-python quedan como alternativas con su disparador de reapertura. Dueño unico del export en tribal/store/export.py y de sqlite3 en store. Deuda conocida que NO se toca aqui: agents/tools/rag_tool.py sigue con la fuente hardcodeada app, asi que el RAG no indexa tribal/ hasta la feature FIX-002.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
"success": true | "message": "ENTORNO LISTO - se puede trabajar." | "ready": true | "errors": 0 | "warnings": 0
checks 14/14 ok: paquete tribal/ presente (project.yml) | pytest 7 passed in 0.33s

$ uv run python -m tribal hello
Hola, mundo.

$ uv run python -m pytest tests -q
7 passed in 0.30s

$ uv run ruff check tribal/ tests/
All checks passed!
$ uv run ruff format --check tribal/ tests/
7 files already formatted
$ uv run mypy tribal/ tests/
Success: no issues found in 7 source files

$ git status --short (extracto)
RM app/__init__.py -> tribal/__init__.py
RM app/__main__.py -> tribal/__main__.py
RM app/cli.py -> tribal/cli.py
RM app/paths.py -> tribal/paths.py

$ referencias obsoletas (from app | import app | app/ | --cov=app | module app) en
  tribal/, tests/, pyproject.toml, Makefile, project.yml, README.md, docs/, .pre-commit-config.yaml
0 coincidencias
```

</details>

## CORE-001 — Primera pieza funcional de punta a punta (Fase 0)

- **Cerrada:** 2026-11-18
- **Verificación:** ./init.sh en verde · 25 passed in 1.51s
- **Cambios:** tribal/core/{modelos,mundo,recursos,acciones}.py; tribal/agents/{necesidades,instinto}.py; tribal/ui/{render,app}.py; tribal/sim.py; tribal/cli.py (subcomando run); tests/{test_motor,test_render,test_cli_run}.py; docs/img/fase0.png; README.md (Ejecutar Fase 0 con salida real y captura); pyproject.toml + uv.lock (pygame-ce 2.5.8)
- **Decisiones:** Motor puro sin pygame: sim.py importa tribal.ui.app de forma perezosa solo en modo ventana, y un test en subprocess exige que importar tribal.sim no meta pygame en sys.modules. Un unico random.Random(seed) en el mundo y lista de individuos ordenada por id: misma semilla y ticks dan el mismo JSON byte a byte. El bucle usa Clock().tick(60) y exactamente un step() por frame (test con ticks_max=5 por mutacion). ms_tick_medio sale solo por stderr con --benchmark: dentro del JSON hacia la salida no reproducible y el numero del README caducaba. Pixel art generado por codigo y cacheado (sin assets externos). Dataclasses de stdlib, sin Pydantic, en Fase 0. Fase 0 no incluye herencia/mutacion, cultura, LLM ni SQLite.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
"success": true | "message": "ENTORNO LISTO - se puede trabajar." | "ready": true | "errors": 0 | "warnings": 0
checks 14/14 ok | pytest 25 passed in 1.44s

$ uv run python -m tribal run --headless --json --ticks 600   (dos corridas)
{"seed": 42, "ticks": 600, "poblacion_inicial": 12, "poblacion_final": 12, "nacimientos": 0, "muertes": 0, "media_energia": 66.62, "media_sed": 42.32, "individuos_movidos": 12}
IDENTICOS=True (176 bytes cada una)

$ uv run python -m tribal run --seed 2 --headless --json --ticks 3000
{"seed": 2, ..., "poblacion_final": 11, "muertes": 1, "individuos_movidos": 12}   exit 0

$ uv run python -m tribal run --seed 7 --benchmark --headless --ticks 600
stderr: benchmark: 0.23 ms/tick, cabe en 16.67 ms   (stdout limpio, sin ms en el JSON)

$ app.bucle con SDL_VIDEODRIVER=dummy
120 frames en 1.960 s -> 61.2 fps ; mundo.tick = 120 (un step por frame)

$ uv run python -c "import tribal.sim, sys; print('pygame' in sys.modules)"
False

$ uv run pytest tests -q
25 passed in 1.42s
$ uv run ruff check tribal/ tests/
All checks passed!
$ uv run ruff format --check tribal/ tests/
22 files already formatted
$ uv run mypy tribal/ tests/
Success: no issues found in 22 source files
```

</details>
