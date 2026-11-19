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

## QA-001 — Batería de calidad en verde

- **Cerrada:** 2026-11-18
- **Verificación:** ./init.sh en verde · 26 passed in 1.54s
- **Cambios:** agents/agents/installer_agent.py (bug de ruta + borrado tolerante); agents/agents/harness_agent.py (--content-file); agents/cli.py y agents/prompts_sync.py (salida UTF-8); agents/prompts/harness_agent.md; agents/tests/{test_installer_agent,test_refactor_scope,test_git_tag_release,test_git_commit_feature,test_git_commit_with_changelog,test_harness_agent,test_prompts_sync,test_cli_utf8}.py; tribal/__init__.py (version desde metadata); tests/test_version.py; .pre-commit-config.yaml (pre-push); .github/workflows/ci.yml (nuevo)
- **Decisiones:** Los 16 fallos eran tres cosas distintas: un bug de producto en installer_agent (una ruta local de Windows hacia que workdir / <abs> colapsara sobre el origen y shutil.rmtree borrase el repo del usuario, y .git ReadOnly hace fallar rmtree en Windows), un test que comparaba rutas con separador fijo, y ~12 lecturas/escrituras sin encoding en tests. Los dos primeros se arreglan en el codigo, no en el fixture. La version pasa a leerse de importlib.metadata: habia tres valores (0.1.1 en __init__, 0.1.4 en pyproject y README) y el test exige que coincidan. record gana --content-file porque --content truncaba con comillas/no-ASCII desde PowerShell. CI nuevo corre exactamente lo mismo que la puerta local, sin pre-commit --all-files (reformatearia agents/). DEUDA ABIERTA: commit_feature sube el patch en pyproject pero no ejecuta uv lock; hay que re-lockear antes de commitear o uv sync --frozen fallara en CI.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
"success": true | "message": "ENTORNO LISTO - se puede trabajar." | "ready": true | "errors": 0 | "warnings": 0
checks 14/14 ok | pytest tests/: 26 passed

$ uv run pytest -q          (suite completa: tests/ + agents/tests, shell limpia sin PYTHONUTF8)
547 passed, 15 skipped in 58.50s   exit 0
(baseline al abrir la feature: 16 failed, 523 passed, 15 skipped)

$ uv run ruff check tribal/ tests/ agents/
All checks passed!
$ uv run ruff format --check tribal/ tests/
23 files already formatted
$ uv run mypy tribal/ tests/
Success: no issues found in 23 source files

$ uv run pre-commit run check-yaml --all-files
Passed
$ uv lock --check
exit 0

$ uv run python -m agents describe cicd        (consola cp1252 real, sin PYTHONUTF8)
exit 0   (antes: UnicodeEncodeError '\u2192')
$ uv run python -m agents.prompts_sync
exit 0   (antes: UnicodeEncodeError en prompts_sync.py:242)

Producto (installer): _repo_dir_name parte por '/', '\\', ':' y quita .git;
_rmtree_force con onexc + chmod S_IWRITE para .git ReadOnly de Windows.
  rmtree plano sobre clon -> WinError 5 ; _rmtree_force -> OK
  test_installer_agent.py cubre ruta local Windows, URL https y scp git@host:a/b

Harness: record --content-file lee UTF-8 y conserva comillas, tildes, flechas y
saltos de linea (probado byte a byte). La causa del truncado queda cerrada.
```

</details>

## FIX-005 — commit_feature idempotente: CHANGELOG y lock

- **Cerrada:** 2026-11-18
- **Verificación:** ./init.sh en verde · 26 passed in 1.67s
- **Cambios:** agents/agents/git_agent.py (snapshot y rollback, version desde HEAD, uv lock + --check antes del commit); agents/agents/documentation_agent.py (entrada de CHANGELOG idempotente por feature_id y reutiliza la [Unreleased] del dia); agents/tools/git_tool.py (show_file, restore_staged, indexed_files); agents/tests/test_commit_feature_idempotente.py (nuevo, 4 casos); agents/prompts/git_agent.md; agents/README.md
- **Decisiones:** La version del siguiente patch se lee de git show HEAD:pyproject.toml, no del working tree: un reintento tras un fallo sumaba otro patch (0.1.6 -> 0.1.7) y dejaba el arbol sucio. El rollback restaura el contenido previo de los cuatro ficheros (no HEAD) para no borrar trabajo del usuario y saca solo esos del indice; el resto de la feature sigue staged. lock y lock --check corren despues del bump y antes del commit, con needs si no cuadran. El CHANGELOG deduplica por feature_id. Trade-off documentado: si el worktree tiene una version mas alta sin commitear, el cierre usa la de HEAD; y un segundo cierre exitoso del mismo id sube otro patch aunque no duplique la entrada.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
"success": true | "ready": true | "errors": 0 | "warnings": 0 | ENTORNO LISTO

$ uv run pytest -q
551 passed, 15 skipped in 60.9s

$ uv run pytest agents/tests -q
525 passed, 15 skipped

$ uv run ruff check tribal/ tests/ agents/
All checks passed!
$ uv run ruff format --check tribal/ tests/
23 files already formatted
$ uv run mypy tribal/ tests/
Success: no issues found in 23 source files
$ uv run python -m agents.prompts_sync
exit 0

Secuencia en COPIA del repo con hook pre-commit exit 1 (CLI real):
run1: success=False needs=<corrige lo que tumbo git commit (hook)> | version 0.1.5 | commits 1
run2: success=False needs=<idem>                 | version 0.1.5 | commits 1
run3 (sin hook): success=true (version 0.1.6)    | 1 seccion [Unreleased] | 1 entrada FIX-005
uv lock --check: 0 | commits 2 | status limpio | CHANGELOG+README+pyproject+uv.lock dentro del commit

Rollback verificado en copia: fichero nuevo sin trackear y fichero trackeado modificado
intactos; pyproject/README/CHANGELOG/uv.lock vuelven a su md5 previo y salen del indice;
sin commit. Camino feliz: git show --stat HEAD incluye el fichero nuevo y los 10 de la feature.

$ uv run python -m agents run git commit_feature ... --dry-run true
md5 de pyproject/README/CHANGELOG/uv.lock identicos antes y despues; git status identico.
```

</details>

## FIX-002 — El RAG indexa el paquete real, no un nombre hardcodeado

- **Cerrada:** 2026-11-18
- **Verificación:** ./init.sh en verde · 26 passed in 1.55s
- **Cambios:** agents/tools/rag_tool.py (_FUENTES_FIJAS + _fuentes(root) que antepone project_slug; RagTool.fuentes(root) y FUENTES calculada al importar; _documentos usa el slug); agents/tests/test_rag_fuentes.py (nuevo, 4 tests)
- **Decisiones:** La fila del paquete se deriva de project_slug y se deduplica con las fuentes fijas. RagTool.FUENTES se congela al importar por compatibilidad, pero el camino real de indexacion usa RagTool.fuentes(root), que si sigue al project.yml de cada raiz. Sin slug no se inventa un directorio: la fuente simplemente no se anade. FUERA DE ALCANCE, anotado: agent_installer_tool.py:36 sigue con el literal app (heuristica, no indexa nada) y EXCLUIDOS compara con '/tests/' mientras el origen usa os.sep, asi que en Windows se cuelan los tests de agents al indice (preexistente).
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -c "from agents.tools.rag_tool import RagTool; print([f[0] for f in RagTool.FUENTES])"
['tribal', 'api', 'chat', 'monitoring', 'tuning', 'agents', 'agents/prompts', 'docs', 'vault', 'harness/progress']

$ git grep -n '"app"' -- agents/tools/rag_tool.py
0 coincidencias

$ uv run pytest agents/tests/test_rag_fuentes.py -q
4 passed in 0.33s
  tribal presente | project.yml en tmp_path con otro_paquete -> otra fuente |
  sin slug no hay fila vacia | slug repetido deduplicado

$ uv run python -c "... _documentos(cwd) ..."
230 documentos | 16 de tribal/ | 0 de app/ | repo sin project.yml -> 9 filas fijas y ninguna excepcion

$ uv run pytest -q
555 passed, 15 skipped in 62.08s
$ uv run ruff check tribal/ tests/ agents/  -> All checks passed!
$ uv run ruff format --check tribal/ tests/ -> 23 files already formatted
$ uv run mypy tribal/ tests/                -> Success: no issues found in 23 source files

$ uv run python -m agents --json run harness gate
"success": true | "ready": true | "errors": 0 | "warnings": 0 | pytest 26 passed
```

</details>

## HARD-000 — Reproducibilidad por semilla y configuracion (Fase 0)

- **Cerrada:** 2026-11-18
- **Verificación:** ./init.sh en verde · 48 passed in 2.45s
- **Cambios:** tribal/config.py (nuevo: SimConfig frozen/slots + validacion tipada + desde_json/a_json); tribal/core/mundo.py (crear recibe config; _mancha parametrizada); tribal/agents/necesidades.py (evolucionar recibe tasas con defaults); tribal/sim.py (config en crear/run y en resumen); tribal/cli.py (--config y precedencia); tests/test_config.py (nuevo, 22 casos); tests/test_cli_run.py (CLAVES); docs/config-ejemplo.json; README (Configuracion y semilla)
- **Decisiones:** SimConfig es la unica fuente de parametros y se serializa al resumen, para que una partida se pueda repetir desde el JSON que la describe. Defaults identicos a Fase 0 (60x34, 0.16/0.15/0.6, 12 individuos): el comportamiento no cambia. La validacion es tipada y nombra clave y valor, porque dos configs que pasaban antes reventaban con traza dentro del motor. MIN_LADO=9 es el minimo real del mapa por el radio de la mancha de recursos. La precedencia es CLI > fichero > defaults y esta documentada. Tests de determinismo a nivel de proceso (subprocess), no solo intra-proceso.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m tribal run --headless --config docs/config-ejemplo.json --ticks 600 --json
{"seed": 42, "ticks": 600, ..., "media_energia": 66.62, "media_sed": 42.32, "individuos_movidos": 12,
 "config": {"seed": 42, "individuos": 12, "ancho": 60, "alto": 34,
            "tasa_sed": 0.16, "tasa_energia": 0.15, "tasa_salud": 0.6}}
(dos procesos CLI distintos -> stdout byte a byte identico)

$ uv run python -m tribal run --config docs/config-ejemplo.json --headless --json --seed 7 --individuos 9
poblacion_inicial 9 | config.seed 7 | config.individuos 9   (precedencia CLI > fichero > defaults)

$ configs invalidas -> exit 2, error con la clave, sin Traceback
ancho 6 -> debe ser al menos 9 tiles | ancho 60.7 -> debe ser un entero
tasa_sed "0.2" -> debe ser un numero | seed "hola" -> debe ser un entero
individuos true -> no vale bool | individuos 5 -> entre 8 y 15
tasa_salud -0.1 -> mayor que 0 | clave gravedad -> claves desconocidas: gravedad

$ uv run pytest tests/test_config.py -q
22 passed
$ uv run pytest -q
577 passed, 15 skipped in 61.81s
$ uv run ruff check tribal/ tests/ agents/  -> All checks passed!
$ uv run ruff format --check tribal/ tests/ -> 25 files already formatted
$ uv run mypy tribal/ tests/                -> Success: no issues found in 25 source files

$ uv run python -m agents --json run harness gate
"success": true | "ready": true | "errors": 0 | "warnings": 0 | pytest 48 passed

Mutacion verificada por el reviewer: quitar el cableado de tasas en sim.step ->
test_cambiar_una_tasa_cambia_el_resumen FALLA (1 failed, 21 passed); restaurado.
```

</details>

## F0-002 — Puerta F0 a F1: reproduccion y comportamiento emergente

- **Cerrada:** 2026-11-18
- **Verificación:** ./init.sh en verde · 63 passed in 5.99s
- **Cambios:** tribal/core/modelos.py (Genoma.longevidad; Individuo edad/madurez/cooldown/huyendo; Depredador; Mundo.depredadores); tribal/core/depredador.py (nuevo: persecucion, mordisco, digestión, no entra al agua); tribal/core/{mundo,acciones}.py (reproduccion, vejez, huida); tribal/agents/instinto.py (huida prioritaria); tribal/sim.py (orden homeostasis -> depredador -> enterrar -> decisiones; resumen con nacimientos, agrupamiento_max, huidas y depredador); tribal/config.py (depredadores, depredador_activo, cooldown_reproduccion); tribal/cli.py; tribal/ui/render.py (depredador y crias); tests/test_puerta_f0.py (nuevo); tests/{test_motor,test_config,test_cli_run}.py; docs/config-ejemplo.json; docs/img/fase0-puerta.png; README
- **Decisiones:** Orden del tick: homeostasis -> depredador.mover -> _enterrar -> decisiones. El chequeo de muerte tiene que ir DESPUES del dano; con el orden anterior la recuperacion de salud resucitaba a la presa (0 -> 0.02) y el depredador no podia matar nunca. La reproduccion exige pareja adulta a <=2 tiles, energia > 65 y cooldown 600; la cria hereda la media de los padres con mutacion acotada al 5 por ciento del genoma. El agrupamiento se mide como maximo de individuos a <=2 tiles de un tile de agua (no bebiendo a la vez) y el test no es vacuo: con la sed congelada el pico cae de 11 a 5. La huida se mide por distancia euclidea real al depredador, no por el flag. depredador_activo=false desactiva de verdad (test). Limitacion conocida: si un anciano muere de vejez el mismo tick en que lo muerden, la muerte se acredita al depredador.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
"success": true | "ready": true | "errors": 0 | "warnings": 0 | pytest 63 passed

$ uv run python -m tribal run --headless --json --ticks 3000 --seed 2
{"seed": 2, "ticks": 3000, "poblacion_inicial": 12, "poblacion_final": 10, "nacimientos": 10,
 "muertes": 12, "media_energia": ..., "media_sed": ..., "individuos_movidos": ...,
 "agrupamiento_max": 11, "huidas": 3688,
 "depredador": {"activos": 1, "ataques": 8, "muertes": 3},
 "config": {...}}
   final = inicial + nacimientos - muertes, exacto en 6 semillas (1,2,3,7,42,123)

$ letalidad del depredador (presa sana acorralada, isla de 1 tile)
salud 100 -> 70 -> 43.20 -> 14.80 -> 0.00 ; muere en el tick 248 ; muertes=1 = depredador.muertes
control identico sin depredador: viva a 300 ticks, salud 100.00, muertes=0
Mutacion: revertir el orden de _enterrar -> test de letalidad FALLA (assert 0 == 1);
_morder sin restar dano -> FALLA igual. Restaurado (sha256 verificado) y gate repetido en verde.

$ agrupamiento: seed 2 pico 11 (umbral 6); inicio 1/12. Con la sed congelada el pico baja a 5:
  lo produce beber, no el spawn.
$ huida: distancia euclidea real al depredador; 4-5 de 5 suben en cada tramo.

$ uv run pytest -q
592 passed, 15 skipped
$ uv run ruff check tribal/ tests/ agents/  -> All checks passed!
$ uv run ruff format --check tribal/ tests/ -> 27 files already formatted
$ uv run mypy tribal/ tests/                -> Success: no issues found in 27 source files
```

</details>

## F1-001 — Genoma y habilidades heredables

- **Cerrada:** 2026-11-18
- **Verificación:** ./init.sh en verde · 87 passed in 7.72s
- **Cambios:** tribal/core/genoma.py (nuevo: 8 rasgos, heredar con media*(1+clamp) y rango); tribal/core/habilidades.py (nuevo: catalogo de 5 habilidades con rama y Habilidades); tribal/core/{modelos,mundo,acciones}.py (genoma en fundadores con varianza, verbo ensenar, bonus de habilidad, resistencia simetrica); tribal/agents/{instinto,necesidades}.py (ensenar en ocio, fallback deambular, sed con resistencia); tribal/sim.py y tribal/cli.py (media_genes, habilidades_distintas); tests/test_genoma.py y tests/test_habilidades.py (nuevos, 24 casos); tests/test_cli_run.py; README
- **Decisiones:** Herencia multiplicativa con clamp del 5 por ciento y rango final [0.5,1.5]: los tests de borde y un rasgo con media 0.6 distinguen la formula multiplicativa de la aditiva y el clamp de su ausencia (el reviewer comprobo que las cuatro mutaciones caen). Los fundadores sortean los siete rasgos funcionales en 0.85-1.15 con mundo.azar: sin varianza inicial la seleccion no tendria sobre que actuar. La resistencia es simetrica (0.8-1.2 de factor de sed) porque un rasgo de una sola cara no evoluciona en las dos direcciones. Las habilidades no se heredan geneticamente: se aprenden por ensenar o imitar, y el bonus afecta al rendimiento del recurso (+50 por ciento). divergencia existe y se hereda pero no se usa hasta F1-003.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
"success": true | "ready": true | "errors": 0 | "warnings": 0 | pytest 87 passed

$ uv run python -m tribal run --headless --json --ticks 3000
"media_genes": {"velocidad": ..., "metabolismo": ..., "longevidad": ..., "fuerza": 1.037,
                "resistencia": 0.957, "inteligencia": 0.984, "salud": ..., "divergencia": 0.56},
"habilidades_distintas": 1, "habilidades": {...}

$ herencia: 100 nacimientos con semilla fija
  todos dentro de [0.5, 1.5]; media a +-0.008 del punto medio parental; mutacion simetrica
  (484-524 de 1000 con signo positivo); dos subprocesos identicos en 600 y 3000 ticks
$ bordes: padres 1.46/1.48 y 0.52/0.54 -> clamp 1.5 / 0.5 verificados
$ fundadores: 12/12 genomas unicos; misma semilla identicos, otra semilla distintos; 0 fuera de rango en 50 semillas

$ habilidades: +50 % real (bayas 40 -> 60, caza 60 -> 90); sin bonus con la habilidad equivocada
  ensenar transfiere (2 tests); imitacion a <=2 tiles si, a 9 no; resistencia 0.8 -> sed x1.08, 1.2 -> x0.92
$ ensenar sin aprendiz: el instinto no la elige; un fallo no clava el tick (deambula)

Mutaciones verificadas por el reviewer (todas en rojo, hashes restaurados):
  quitar clamp | media+m en vez de media*(1+m) | ensenar sin transferir | BONUS=0 |
  factor_resistencia=1.0 | sensibilidad 0.4->0.2 | quitar fallback deambular | quitar varianza fundadora

$ uv run pytest -q
616 passed, 15 skipped
$ uv run ruff check tribal/ tests/ agents/  -> All checks passed!
$ uv run ruff format --check tribal/ tests/ -> 31 files already formatted
$ uv run mypy tribal/ tests/                -> Success: no issues found in 31 source files
```

</details>

## F1-002 — Arbol de conocimiento con progresion y origen de nodo

- **Cerrada:** 2026-11-18
- **Verificación:** ./init.sh en verde · 102 passed in 8.32s
- **Cambios:** tribal/culture/arbol.py (nuevo: Nodo frozen y catalogo de 23 nodos en 5 ramas); tribal/culture/grafo.py (nuevo: descubrir con validacion, aristas, pct_fuera_arbol, a_json); tribal/sim.py (grafo en la simulacion, PRACTICAS, maximo un nodo por tick, resumen con nodos); tribal/cli.py (report culture); tests/test_arbol.py (nuevo, 15 casos); tests/test_cli_run.py; README; .opencode/agents/reviewer.md (el reviewer corrigio dos comandos muertos de su propia definicion: test coverage_summary -> coverage_report y doctor -> doctor checkup)
- **Decisiones:** El arbol es andamiaje de plausibilidad, no guion: cada nodo declara requisitos y el grafo los valida; descubrir sin ellos lanza PrerequisitoFaltante. El origen se escribe al crear el nodo y el Nodo es frozen: no hay API para reescribirlo (setattr revienta). pct_fuera_arbol cuenta solo combinacion e interaccion, como objetivo.md §3.2; llm no entra en el KPI (es origen de propuesta, no nivel de §8b) y el docstring ya lo dice. La integracion es minima y determinista: con la habilidad de la rama y los requisitos cumplidos se descubre el siguiente nodo; maximo uno por tick. Se cerraron por adelantado los huecos de test que el reviewer dejo abiertos (gate de habilidad, tope por tick, porcentaje no cero).
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
"success": true | "ready": true | "errors": 0 | "warnings": 0 | pytest 102 passed

$ uv run python -m tribal report culture --json
{"nodos": 5, "aristas": 4, "pct_fuera_arbol": 0.0,
 "nodos_por_origen": {"arbol": 5, "combinacion": 0, "interaccion": 0, "llm": 0}, ...}
  dos subprocesos identicos

$ catálogo: 23 nodos | 5 ramas | ids unicos | 0 requisitos inexistentes | 0 ciclos
  litica 0-4 | fuego 0-4 | lenguaje 0-3 | roles 0-2 | simbolico 0-3
  cruces justificados: mito = proto_palabras + ritual | lider = anciano + caza_cooperativa

$ descubrir sin prerrequisito -> PrerequisitoFaltante: faltan prerrequisitos guijarro (sin nodo ni arista)
  con prerrequisito -> origen arbol, autor 5, tick 42
  segundo intento con origen combinacion -> sigue arbol/5/42 ; setattr -> FrozenInstanceError

$ gate de habilidad: sin recolectar 0 nodos, con recolectar descubre (test)
$ tope: maximo 1 nodo por tick (test con 3 comedores)
$ pct_fuera_arbol: nodo combinacion + interaccion -> 40.0 ; llm no cuenta (test)

$ uv run pytest -q
631 passed, 15 skipped
$ uv run ruff check tribal/ tests/ agents/  -> All checks passed!
$ uv run ruff format --check tribal/ tests/ -> 33 files already formatted
$ uv run mypy tribal/ tests/                -> Success: no issues found in 33 source files
```

</details>

## F1-003 — Divergentes y conformistas: variacion y transmision

- **Cerrada:** 2026-11-18
- **Verificación:** ./init.sh en verde · 115 passed in 15.57s
- **Cambios:** tribal/culture/combinaciones.py (nuevo: 5 cruces plausibles fuera del arbol); tribal/culture/grafo.py (descubrir combinaciones con origen forzado, veces_usado/imitado); tribal/core/genoma.py (clasificacion por divergencia), tribal/core/recursos.py (crisis); tribal/config.py (crisis, sequia_ticks); tribal/sim.py (intentos solo de divergentes, imitacion solo de conformistas, contadores en el resumen); tribal/cli.py (--crisis); tests/test_divergencia.py (nuevo, 13 casos); tests/{test_config,test_cli_run}.py; docs/config-ejemplo.json; README
- **Decisiones:** Divergente > 0.6, conformista < 0.4, neutro en medio: los neutros ni intentan ni imitan. Los cruces son nivel 1 de §8b (origen combinacion) y solo se intentan en crisis: sin crisis, 10/10 semillas dan 0 intentos y 0 combinaciones, con crisis 9/10 dan al menos una. La crisis reduce la regeneracion de agua/bayas a la mitad y sube la sed un 25 por ciento. La transmision se mide con veces_usado e imitado, y solo los conformistas suman imitaciones: el reviewer ancla ambas mitades del criterio con tests negativo y positivo. LIMITACION ABIERTA para F1-004: la proporcion de divergentes no sube en crisis con el modelo actual (15 vs 33 por ciento); la puerta F1 exige que reaccione, asi que F1-004 tiene que meter seleccion real (ventaja de supervivencia o reproduccion del divergente en crisis) y demostrarla en varias semillas.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
"success": true | "ready": true | "errors": 0 | "warnings": 0 | pytest 115 passed

$ uv run python -m tribal run --headless --json --ticks 5000 --crisis
"n_divergentes": 4, "n_conformistas": 2, "n_neutros": 21,
"intentos_divergentes": 2, "combinaciones_logradas": 1, "imitaciones": ...,
"nodos_por_origen": {"arbol": 5, "combinacion": 1, "interaccion": 0, "llm": 0},
"pct_fuera_arbol": 16.7   -> nodo raedera (lasca + conservar_brasas) en el tick 349

$ misma semilla SIN crisis
"intentos_divergentes": 0, "combinaciones_logradas": 0, "nodos_por_origen.combinacion": 0
  10/10 semillas sin crisis: 0 intentos y 0 combinaciones; 9/10 con crisis: >=1 combinacion

$ transmision: autor divergente + usuarios divergente/neutro -> veces_usado 2, imitado {}
  mismo montaje con conformista -> imitado {"guijarro": 1}
  contadores reales: caza_cooperativa 7/3 a 600 ticks -> 46/12 a 1500

Mutaciones verificadas por el reviewer (SHA-256 restaurado):
  quitar es_conformista -> CAE | quitar registrar_uso -> CAE | no forzar origen -> CAE |
  sin filtro de requisitos -> CAE | quitar gate de crisis -> CAE

$ uv run pytest -q
644 passed, 15 skipped
$ uv run ruff check tribal/ tests/ agents/  -> All checks passed!
$ uv run ruff format --check tribal/ tests/ -> 33 files already formatted
$ uv run mypy tribal/ tests/                -> Success: no issues found in 33 source files
```

</details>

## CONNECT-001 — Conectar las ramas del arbol a sus practicas

- **Cerrada:** 2026-11-18
- **Verificación:** ./init.sh en verde · 160 passed in 33.21s
- **Cambios:** tribal/agents/instinto.py (practicas por rama en ocio, rotacion determinista, sesgo de cohesion); tribal/core/acciones.py (tallar, frotar_madera, hablar, cuidar, pintar con coste y efecto); tribal/core/recursos y mundo (apoyo); tribal/sim.py (PRACTICAS verbo->rama y descubrimiento por practica); tribal/culture/{beneficios,tradiciones,combinaciones}.py (base de EMER-001); tests/test_practicas.py (nuevo, 19 casos) y tests/test_tradiciones.py; tests/test_arbol.py; README; vault/01_PROYECTO/arquitectura.md (§9.1 ramas y verbos)
- **Decisiones:** Cada rama tiene verbo con efecto real (energia, salud o transmision) y el instinto solo practica en ocio: con urgencia no hay tiempo para cultura. Eso hace alcanzables las cinco ramas y los cinco cruces, no solo litica, y el test e2e de canto_ritual sale de la dinamica (control: con una sola practica solo aparece raedera). El arbol de trabajo incluye el codigo de EMER-001, que esta BLOQUEADA por su criterio 5 (2/10 semillas): aqui se conserva porque es la base correcta (sin canales de fitness por decreto, beneficios y tradiciones) y lo que falta -utilidad situacional y gradiente ambiental- va en UTIL-001 y AMB-001, con la puerta retada en F1-005. El criterio 3 del backlog decia 'en F1 solo avanza la litica'; esa premisa ya es falsa y no se puede reescribir el criterio sin la accion harness edit (HARNESS-EDIT, pendiente): la documentacion dice lo que realmente avanza.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
"success": true | "ready": true | "errors": 0 | "warnings": 0 | pytest 160 passed

$ run 600 ticks, seed 42 (calma)
ramas descubiertas: litica 5, fuego 5, lenguaje 4, roles 7, simbolico 6
cinco practicas: tallar -> litica | frotar_madera -> fuego | hablar -> lenguaje |
                 ensenar/cuidar -> roles | pintar -> simbolico
solo en ocio (con urgencia no practica) y rotacion determinista por (id + tick)

$ e2e de combinacion distinta de raedera (seed 42, 600 ticks, --crisis)
canto_ritual = proto_palabras + ritual, creado por _intentar_combinacion ->
grafo.descubrir(origen=combinacion) en el tick 76; tambien con seeds 7, 123 y 2026
control: con PRACTICAS reducido a comer->litica solo aparece raedera y proto_palabras/
ritual quedan inactivos

$ efectos reales (y tests de su coste)
tallar -0.5 energia | frotar_madera -1.0 | pintar -0.2 | cuidar +0.5 salud (solo salud < 100) |
hablar puede transmitir (probabilistico; la rama avanza igual)
Mutaciones: costes a 0 y SALUD_PARA_CUIDAR=101 -> sus tests caen.

$ pct_fuera_arbol: 14.8 en calma y 30.3 en crisis (seed 42, 600 ticks); hay semillas en
calma con 0.0, y el README ahora lo dice.

$ uv run pytest -q
689 passed, 15 skipped
$ uv run ruff check tribal/ tests/ agents/  -> All checks passed!
$ uv run ruff format --check tribal/ tests/ -> 40 files already formatted
$ uv run mypy tribal/ tests/                -> Success: no issues found in 40 source files
```

</details>

## DIVERGENCIA-002 — La divergencia es conducta tambien en calma, no solo en crisis

- **Cerrada:** 2026-11-18
- **Verificación:** ./init.sh en verde · 176 passed in 31.54s
- **Cambios:** tribal/agents/instinto.py (radio de deambulacion 3/5/10 por temperamento, sesgo de cohesion firmado, rumbo recordado en Individuo.paseo); tribal/core/modelos.py (campo paseo); tribal/sim.py (descubridores, supervivencia con y sin descubrimiento, diferencial_seleccion); tests/test_divergencia_calma.py (nuevo, 16 casos); README; arquitectura.md §9.2
- **Decisiones:** La divergencia solo decide conducta: en calma cambia el radio explorado (3/5/10 tiles) y el sesgo de cohesion, y nunca la urgencia. La aptitud se mide, no se decretada: diferencial_seleccion = supervivencia de descubridores - no descubridores, con las crias en el denominador y descubridores = autores de nodos origen combinacion (no imitadores). La vigilancia contra ventajas por decreto pasa a ser un guard por lista blanca de accesos a divergencia recorriendo funciones de todo tribal/, mas cuatro tests conductuales (bocado, sed al beber 50/90, umbral de cria +-1, genoma congelado a 500 ticks): las cinco mutaciones probadas caen. LIMITES ANOTADOS: el whitelist es por funcion, no por linea, asi que una ventaja dentro de _intentar_combinacion o via temperamento() aun pasaria; se cierra en F1-005 con snapshots alrededor de las funciones permitidas. La proporcion de divergentes aun no sube de forma sistematica (4/10): es lo que atacan UTIL-001, AMB-001 y la puerta F1-005, no se maquilla aqui.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
"success": true | "ready": true | "errors": 0 | "warnings": 0 | pytest 176 passed

$ conducta en calma (pradera 60x34, 1 individuo, 120 ticks, misma semilla)
div 0.1 -> radio medio 6.15 | 0.5 -> 7.61 | 0.7 -> 9.00 | 0.9 -> 10.04
8/8 semillas radio(0.9) > radio(0.1); con sed critica los tres devuelven la misma accion
paseo no es genoma, no se hereda y no se serializa

$ sin ventaja directa: mutaciones que deben caer, y caen
M1 comer -20 % al divergente        -> falla (guard + test conductual)
M2 beber sacia -20 % al divergente  -> falla
M3b umbral de cria -10 al divergente-> falla
M4 divergencia += 0.01 por tick     -> falla
E1 getattr(ind, genoma).divergencia > 0.5: energia += 1 dentro de una funcion -> falla
  (whitelist AST de accesos a divergencia; 5 modulos; hashes restaurados)

$ telemetria de seleccion (seed 42, 2000 ticks, crisis)
descubridores [1,2,7,9] | supervivencia descubridores 1.0 | no descubridores 17/19 = 0.895
diferencial_seleccion +0.105 ; en calma descubridores [] y diferencial 0.0
descubridores == autores de nodos origen combinacion en 6/6 semillas

$ uv run pytest -q
705 passed, 15 skipped
$ uv run ruff check tribal/ tests/ agents/  -> All checks passed!
$ uv run ruff format --check tribal/ tests/ -> 41 files already formatted
$ uv run mypy tribal/ tests/                -> Success: no issues found in 41 source files
```

</details>

## FIX-ENERGIA — La reproduccion conserva la energia, sin inyeccion neta

- **Cerrada:** 2026-11-18
- **Verificación:** ./init.sh en verde · 181 passed in 48.09s
- **Cambios:** tribal/sim.py (_nacer conserva la energia: aportado = min(ENERGIA_CRIA, energia de la madre); resumen con coste_reproduccion; docstring de la constante); tests/test_reproduccion.py (nuevo, 5 casos: conservacion, madre sin energia, pareja bajo umbral en calma y crisis, guard de umbral por regimen, auditoria de 8000 ticks); tests/test_cli_run.py (CLAVES); README
- **Decisiones:** La conservacion se garantiza por construccion, no por confiar en el umbral: el camino normal (umbral 65 > coste 50) ya era neutro, pero una madre con menos de 50 creaba energia (30 -> 0 y cria 50). Ahora la cria recibe min(50, energia de la madre) y no hay inyeccion posible; el padre no paga y no hay segunda cria. Se midio que la crisis no subsidia: 0.2762 nacimientos por 1000 persona-ticks en calma frente a 0.2788 en crisis (10 semillas), con dE = 0 auditado en cada nacimiento; la diferencia de poblacion final es ruido caotico, no natalidad. La cria nace a sed 0 y salud 100, pero en 211 nacimientos la madre estaba igual (inyeccion neta 0).
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
"success": true | "ready": true | "errors": 0 | "warnings": 0 | pytest 181 passed

$ conservacion de energia en el parto (_nacer)
aportado = min(ENERGIA_CRIA=50, energia_madre) ; madre -= aportado ; cria = aportado
barrido 30/49/50/51/64.9/65/65.1/70/100 -> delta_total = +0.000000 en todos
cria == min(50, madre) ; solo hay dos Individuo() en el repo (fundo y _nacer) ; el padre no paga

Codigo viejo (max(0.0, ...) + cria fija 50) reproducido: madre 30 -> cria 50, test FALLA (50.0 == 30.0)

$ pareja con energia baja: 64 (= umbral 65 - 1) -> 0 nacimientos en calma y en crisis
$ energia auditada por nacimiento en 8000 ticks: dE = 0 en todos
$ 10 semillas x 8000 ticks: calma 227 nacimientos / 0.2762 por 1000 persona-ticks;
  crisis 238 / 0.2788 (+0.94 %); umbral identico en ambos regimenes (guard AST que falla si
  aparece UMBRAL_REPRODUCCION_CRISIS=30)

$ uv run pytest -q
710 passed, 15 skipped
$ uv run ruff check tribal/ tests/ agents/  -> All checks passed!
$ uv run ruff format --check tribal/ tests/ -> 43 files already formatted
$ uv run mypy tribal/ tests/                -> Success: no issues found in 43 source files
```

</details>

## UTIL-001 — Utilidad situacional: el invento vale segun el estado

- **Cerrada:** 2026-11-18
- **Verificación:** ./init.sh en verde · 186 passed in 49.52s
- **Cambios:** tribal/culture/beneficios.py (utilidad situacional por escasez, densidad de portadores y gancho de estacion; se elimina el multiplicador fijo); tribal/sim.py (situacion por tick, beneficio por individuo, utilidad_media/escasez/estacion en el resumen); tribal/core/acciones.py (aplica la utilidad, sin mirar temperamento); tests/test_utilidad.py (nuevo, 5 casos); tests/test_divergencia*.py y test_cli_run.py (CLAVES); README (tabla nominal, densidad y salidas reales de 600 y 5000 ticks)
- **Decisiones:** La utilidad es condicional, no un buff: en abundancia vale 1.0 exacta y solo se acerca a su efecto nominal cuando el recurso escasea; ademas se diluye con la densidad de portadores (utilidad de oportunidad, no de rasgo). Se calcula una vez por tick desde las cantidades reales de mundo.recursos, no desde constantes. La prueba es la misma semilla en calma y crisis: +0.00 frente a +3.32 de energia media, y las dos mutaciones de la escasez tumban el test por lados opuestos. estacion queda como gancho null hasta AMB-001 y esta documentado como no implementado, no como hecho. El temperamento no entra en la cuenta (AST limpio y guard de DIVERGENCIA-002 verde).
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
"success": true | "ready": true | "errors": 0 | "warnings": 0 | pytest 186 passed

$ formula: utilidad = 1 + (efecto_nominal - 1) * escasez * 1/(1 + 0.1*portadores)
  escasez = 1 - cantidad/capacidad, calculada de mundo.recursos
  abundancia -> utilidad 1.0 exacta; densidad con portadores reales (15/16 -> 1.0833)
  temperamento: cero accesos a divergencia/genoma en beneficios.py

$ tabla con la MISMA semilla (energia media, 3000 ticks; calma vs crisis)
semilla:      1       2       3       4       5      media
calma dif: +0.00   +0.00   +0.00   +0.00   +0.00    +0.00
crisis dif:+1.95   +4.63   +2.58   +2.90   +4.53    +3.32
(reproducido por el reviewer con 7 semillas: calma +0.00 en todas)

$ mutaciones (caen los dos lados)
escasez := 1.0 -> en calma +4.40, test FALLA | escasez := 0.0 -> crisis +0.00, test FALLA

$ run --headless --json --ticks 5000 (crisis)
"utilidad_media": {"raedera": 1.0868, "caceria_dirigida": 1.19, "turnos_de_vigilia": 0.8245, ...},
"escasez": {"agua": 0.5, "bayas": 0.833, "caza": 0.688}, "estacion": null
  (cuentas independientes: 120/120, 26/156, 5/16)

$ uv run pytest -q
715 passed, 15 skipped
$ uv run ruff check tribal/ tests/ agents/  -> All checks passed!
$ uv run ruff format --check tribal/ tests/ -> 44 files already formatted
$ uv run mypy tribal/ tests/                -> Success: no issues found in 44 source files
```

</details>

## AMB-001 — Gradiente ambiental: parches que se agotan y migran

- **Cerrada:** 2026-11-18
- **Verificación:** ./init.sh en verde · 206 passed in 58.14s
- **Cambios:** tribal/core/modelos.py (Parche y Mundo.parches/estacion); tribal/core/recursos.py (agrupacion en parches, agotamiento local, migracion con umbral y cooldown, reubicacion con distancia minima fuente-a-fuente y validacion de terreno); tribal/core/mundo.py (siembra de parches y estacion); tribal/config.py (migracion, ticks_por_estacion, umbral_agotamiento); tribal/sim.py (estacion, parches y migraciones en el resumen; invierno en la utilidad); tribal/ui/render.py (tinte de estacion y marcador de parche agotado); tests/test_ambiente.py (nuevo, 15 casos); tests/{test_config,test_cli_run}.py; docs/config-ejemplo.json; README
- **Decisiones:** El filtro de destino exigia 2 tiles entre TODAS las fuentes del mismo tipo; con 30-40 fuentes de bayas sobre el bosque daba 0/2000 centros validos y las bayas no migraban nunca. Ahora el filtro es fuente-a-fuente con 1 tile (prohibe apilar, deja pasar vecinas) y se toma la primera casilla valida de un orden barajado con Mundo.azar: 7 candidatos validos para bayas y 100 por ciento de migraciones en 10 combinaciones semilla-mapa. El agua no migra porque es terreno, no fauna. Las estaciones son opt-in (ticks_por_estacion=0) para no romper Fase 0: con migracion=false y sin estaciones, 37 claves del resumen son identicas a HEAD. El test de mecanismo usa el mismo mundo, casilla, genoma y sexo: la unica diferencia es la politica, y las cuatro mutaciones lo tumban.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
"success": true | "ready": true | "errors": 0 | "warnings": 0 | pytest 206 passed

$ migracion de parches (barrido 2 mapas x seeds 1,2,3,5,42)
11-14 de 11-14 parches de comida migran, bayas y caza; 0 de agua
0 fuentes en agua, 0 fuera del mapa, 0 casillas apiladas, >=6 tiles del centro viejo
bayas en crear(42): migra a 12.14 tiles, relleno 4/4, todo pisable, centro en BOSQUE
misma semilla -> mismas posiciones; 7 semillas -> 7 destinos distintos por tipo
mutaciones: saltar BAYAS -> caen 2 tests; quitar guard de agua -> cae su test;
quitar pisable -> cae su test

$ estacion (ticks_por_estacion=10): regeneracion 159 vs 99 en 400 ticks (0.62x en invierno)
sin estaciones (0): null y factor 1.0 ; migracion=false + estaciones 0: 37 claves
comunes identicas a HEAD (solo difiere config)

$ mecanismo (mismo mundo, misma casilla 4.5/4.0, mismo Genoma(), mismo sexo)
politica que sigue el parche: viva a 1200 ticks, salud 100.0
politica que patrulla la zona agotada: salud 0.0 en el tick 834
mutaciones: quedarse=sigue -> CAE ; sin migracion -> CAE ; migra sin comida -> CAE

$ resumen real: "estacion primavera parches 17 migraciones 4"
  parches[{id,tipo,activo,abundancia,x,y}] y migraciones, en JSON y en texto
$ dos subprocesos con la misma semilla: JSON identico (7154 bytes a 1200 ticks)

$ uv run pytest -q
735 passed, 15 skipped
$ uv run ruff check tribal/ tests/ agents/  -> All checks passed!
$ uv run ruff format --check tribal/ tests/ -> 45 files already formatted
$ uv run mypy tribal/ tests/                -> Success: no issues found in 45 source files
```

</details>

## F1-006 — Puerta F1 a F2 medida en la descendencia

- **Cerrada:** 2026-11-19
- **Verificación:** ./init.sh en verde · 241 passed in 134.32s (0:02:14)
- **Cambios:** tribal/agents/instinto.py (memoria condicional al entorno y copia del vecino con mas energia); tribal/core/recursos.py (en calma se regenera en el sitio; en crisis migra a >=10 tiles; horizonte); tribal/core/{modelos,mundo}.py (estado de memoria/parche); tribal/config.py (ticks_migracion, balance del mundo); tribal/sim.py (S_fecundidad, S_viabilidad, nacidos, descubrimientos por temperamento, imitaciones, longevidades, media/sigma); tribal/gate_f1.py (barrido 1..10, tabla y veredicto primaria/secundaria); tribal/cli.py (report gate-f1); tests/test_puerta_f1.py (nuevo) y ajustes en test_cli_run/test_config/test_divergencia_calma; README; vault/01_PROYECTO/arquitectura.md (§9.3)
- **Decisiones:** La medida primaria de la puerta es la respuesta en la descendencia: S_fecundidad = media del rasgo de los reproductores - media inicial del brazo. Con 12 fundadores el porcentaje de vivos es binomial y ruidoso (un desplazamiento pequeño de la media lo mueve de 0 a 100), asi que se publica como secundario y no decide. El criterio corregido por el usuario es S>0 en crisis (el cambio selecciona divergentes) y S<0 en calma (manda la tradicion): 7/10 y 7/10. La memoria del conformista solo envejece si el entorno cambia: en calma el parche agotado se regenera en el sitio y la copia sigue siendo valida; en crisis migra fuera del horizonte de 4 tiles. N=50 confirma la senal (9/10 y 6/10) pero pierde crisis<=calma; se documenta como salvedad de escala. F1-005 queda bloqueada y sustituida por esta feature; F1-004 y EMER-001 siguen bloqueadas como historia del diagnostico.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
"success": true | "ready": true | "errors": 0 | "warnings": 0 | pytest 241 passed

$ uv run python -m tribal report gate-f1 --seeds 1-10 --ticks 8000
VEREDICTO PRIMARIO (S): S crisis>0 7/10 | S calma<0 7/10 | PRIMARIA True
SECUNDARIO (div%, no decide): sube 4/10 | empata 3/10 | baja 3/10 |
  crisis<=calma>=6/10 True | extinciones crisis<=calma True
columnas por semilla y brazo: div%, nac_div, S_fec, S_via, desc/divergente, desc/conformista,
  imit/desc, long_divergente, long_conformista, media, sigma, nacidos, nodos, poblacion, ext

Aritmetica comprobada a mano (seed 1): inicial 0.460245; calma 37 reproductores media 0.421055
-> S = -0.0392 ; crisis 38 reproductores media 0.463637 -> S = +0.0034
S sale de REPRODUCTORES, no de vivos, y contra la media inicial del brazo.

Mutaciones que caen (hash restaurado):
  _memoria_vigente -> True | quitar habilidades.aprender | leer .divergencia en comer |
  DISTANCIA_MINIMA_MIGRACION = 4 | migrar tambien en calma

$ memoria condicional al entorno
calma: parche agotado se regenera en el sitio (memoria valida, conformista compite)
crisis: el parche migra a >=10 tiles (fuera del radio 4 del conformista, dentro del 14 del divergente)

$ N=50 (salvedad documentada): S crisis 9/10 y calma 6/10 confirman la senal,
  pero crisis<=calma cae a 4/10 y hay una extincion en crisis. La puerta se mide a N=12,
  el default del juego (concepto §1b); la salvedad queda escrita, no oculta.

$ uv run pytest -q
770 passed, 15 skipped
$ uv run ruff check tribal/ tests/ agents/  -> All checks passed!
$ uv run ruff format --check tribal/ tests/ -> 49 files already formatted
$ uv run mypy tribal/ tests/                -> Success: no issues found in 49 source files
```

</details>

## HARNESS-EDIT — Anadir accion edit al agente harness

- **Cerrada:** 2026-11-19
- **Verificación:** ./init.sh en verde · 241 passed in 134.99s (0:02:14)
- **Cambios:** agents/agents/harness_agent.py (accion edit: validacion de tipos, title/description/criteria/depends_on, deteccion de ciclos, diff before/after, sin tocar status/blocked_reason); agents/contracts.py (describe de harness); agents/prompts/harness_agent.md (accion, precedente y flags sin valor en PowerShell); agents/tests/test_harness_edit.py (nuevo, 27 casos); .claude/agents/reviewer.md (regenerado por prompts_sync desde la fuente)
- **Decisiones:** edit no es un atajo para maquillar criterios: solo toca features pending, devuelve el diff before/after, rechaza status/blocked_reason y no reescribe si no hay cambio. La validacion de tipos existe porque PowerShell convierte '--flag' sin valor en True y '--depends_on ""' en True: los campos de texto se rechazan y depends_on=True se interpreta como limpiar, documentado. Es la herramienta que faltaba para corregir criterios y dependencias sin editar el JSON a mano; se usa para reapuntar HARD-1 y F2-001 a F1-006 (el gate real) en una decision del lider posterior a este cierre, no dentro de esta feature. INCIDENCIA: durante la revision el implementer ejecuto una prueba contra el repo real y muto HARD-1; se detecto por el audit, se restauro y el informe se corrigio. El aislamiento en %TEMP% no aislaba porque la raiz del contexto sale del paquete instalado, no del cwd: queda anotado.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
"success": true | "ready": true | "errors": 0 | "warnings": 0 | pytest 241 passed

$ harness edit --id EMER-002 --title "..." --description "..." --criteria "a;b"
success=true ; data.changes {before, after} ; solo cambia esa feature (md5 del resto intacto)

$ rechazos (success=false, fichero byte-identico)
id inexistente | feature in_progress (HARNESS-EDIT) | done (F1-006) | blocked (F1-004) |
dep inexistente | ciclo A->B->A | autodependencia | status/blocked_reason |
title/description/criteria sin valor (True) | criteria ";" | tipos no-str

$ depends_on
--depends_on "" (PowerShell) -> limpia con diff {before:["F2-002"], after:[]}
--depends_on "A;B" valida existencia y ciclos ; "" limpia ; no-op no reescribe bytes

$ 27 tests en agents/tests/test_harness_edit.py (9 via run()/CLI)
$ uv run python -m agents.prompts_sync  -> exit 0 (prompt y contrato de harness con edit)
$ uv run pytest -q
797 passed, 15 skipped
$ uv run ruff check tribal/ tests/ agents/  -> All checks passed!
$ uv run ruff format --check tribal/ tests/ -> 49 files already formatted
$ uv run mypy tribal/ tests/                -> Success: no issues found in 47 source files
```

</details>

## HARD-1 — Endurecimiento tras Fase 1: semilla, telemetria y docs

- **Cerrada:** 2026-11-19
- **Verificación:** ./init.sh en verde · 255 passed in 151.14s (0:02:31)
- **Cambios:** tribal/sim.py (run_muestreado y Simulacion.muestra: telemetria por intervalo); tribal/cli.py (report telemetry con --seed/--ticks/--intervalo/--config/--crisis y tabla legible); tests/test_semillas.py (nuevo, 10 semillas con dos subprocess) y tests/test_telemetria.py (nuevo); README (Estado tras Fase 1 + telemetria, numeros recalculados); vault/01_PROYECTO/arquitectura.md (§9/§10 estado real y comandos)
- **Decisiones:** La reproducibilidad se comprueba donde duele: en procesos distintos y comparando bytes, no solo claves; y se complementa con la config no-default. La telemetria muestrea por intervalo y se contrasta contra run(N) en los extremos, de modo que una fila no pueda inventarse. README y arquitectura se regeneran con los comandos ejecutados y se comprobaron byte a byte por el reviewer; §9 solo lista modulos que existen. No se toco ningun mecanismo: el diff de core/agents/culture esta vacio (insercion pura en sim/cli). Deuda anotada: project.yml sigue en 0.1.0 mientras pyproject va por 0.1.19 (doctor lo canta) y el epigrafe 'Ejecutar (Fase 0)' del README sobrevive bajo 'Estado tras Fase 1'; ambos se cierran en HARD-3.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
"success": true | "ready": true | "errors": 0 | "warnings": 0 | pytest 255 passed

$ uv run pytest tests/test_semillas.py -q
10 passed in 14.98s
  parametrizado range(1,11): dos subprocess de `-m tribal run --headless --json --ticks 600 --seed N`
  con assert primera.stdout == segunda.stdout (bytes) y comparacion con el resumen in-process

$ uv run python -m tribal report telemetry --json --seed 42 --ticks 600 --intervalo 60
10 muestras (60..600, no 600 filas) con tick, poblacion, divergentes, conformistas, neutros,
nodos, aristas, media_energia y media_sed
  tick 60  -> 12/3/7/2/15/12/75.56/20.6   = run(60,42)
  tick 600 -> 16/3/8/5/30/27/75.23/34.51  = run(600,42)
dos ejecuciones byte-identicas; sin --json, tabla legible
bordes: --ticks 130 -> 60/120/130 ; --intervalo 0 y --ticks 0 -> exit 2

$ README y arquitectura
JSON de 600 ticks byte-identico al stdout real; seed 7 benchmark y seed 2/3000 identicos;
report culture (30 nodos, 27 aristas, 23.3 %) y gate-f1 (7/10, 7/10, PRIMARIA True) coinciden
docs/config-ejemplo.json = el JSON del README ; §9 solo lista lo que existe (llm/ y store/ aun no)

$ uv run pytest -q
811 passed, 15 skipped
$ uv run ruff check tribal/ tests/ agents/  -> All checks passed!
$ uv run ruff format --check tribal/ tests/ -> 49 files already formatted
$ uv run mypy tribal/ tests/                -> Success: no issues found in 49 source files
$ git diff tribal/core tribal/agents tribal/culture -> vacio (sin cambios de mecanismo)
```

</details>

## F2-001 — Cliente LLM HTTP con esquema de acciones

- **Cerrada:** 2026-11-19
- **Verificación:** ./init.sh en verde · 286 passed in 151.88s (0:02:31)
- **Cambios:** tribal/llm/{__init__,esquema,cliente}.py (nuevos: vocabulario derivado, JSON schema, validacion, prompt con few-shot, cliente HTTP con transporte inyectable y backend falso); tribal/cli.py (llm selfcheck); tests/conftest.py (guarda de red de la suite); tests/test_llm_esquema.py y tests/test_llm_cliente.py (nuevos, 31 casos); README (LLM y arranque de Ollama); vault/01_PROYECTO/arquitectura.md (§2.3 contrato, timeout y degradacion)
- **Decisiones:** El vocabulario de acciones se deriva de tribal.core.acciones (get_args del Literal), no se duplica: un enum copiado a mano es la primera cosa que se desincroniza. El cliente no importa pygame y usa urllib de stdlib con timeout corto; el transporte es inyectable y los tests no abren red (guarda global en conftest). Devolver estado (ok/degradado/error) en vez de lanzar es lo que permite que el bucle siga por instinto; la cola que lo consume es F2-002. Selfcheck informa aunque el servicio este caido y exit 0: no disponible no es un fallo del comando. Deuda anotada: selfcheck no verifica que tribal-llm este en /api/tags, el README cita tribal.Modelfile y ese fichero no esta en el repo, y validar() acepta campos extra que el schema prohibe (se cierran en HARD-2).
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
"success": true | "ready": true | "errors": 0 | "warnings": 0 | pytest 286 passed

$ uv run python -m tribal llm selfcheck --json     (Ollama levantado)
{"disponible": true, "endpoint": "http://127.0.0.1:11434", "modelo": "tribal-llm",
 "latencia_ms": 36.3, "error": null}   exit 0
$ ... --endpoint http://127.0.0.1:9
{"disponible": false, "error": "conexion rechazada", ...}  exit 0, sin traza

$ esquema: ACCIONES = get_args(NombreAccion)  (derivado del vocabulario real, no duplicado)
  prueba: accion fuera del vocabulario | campo faltante | tipo erroneo | texto libre (aceptado)
$ cliente: 7 casos inyectados (ok, JSON roto, timeout, conexion rechazada, 500, sobre no-JSON,
  sin message) -> ninguno lanza excepcion; timeout=0.5 corta en 0.544 s; no importa pygame
$ red en tests: guarda global sobre urllib.request.urlopen; un test temporal que la forzaba
  fue abortado por la guarda (verificado por el reviewer y borrado despues)

$ uv run pytest -q
842 passed, 15 skipped
$ uv run ruff check tribal/ tests/ agents/  -> All checks passed!
$ uv run ruff format --check tribal/ tests/ -> 55 files already formatted
$ uv run mypy tribal/ tests/                -> Success: no issues found in 55 source files
```

</details>

## F2-002 — Cola asincrona de inferencia que no frena el mundo

- **Cerrada:** 2026-11-19
- **Verificación:** ./init.sh en verde · 298 passed in 156.23s (0:02:36)
- **Cambios:** tribal/llm/cola.py (nuevo: hilo dedicado, colas acotadas, ventana de validez, cierre acotado con en_vuelo a 0); tribal/llm/cliente.py (backend_stub determinista por SHA-256, worker blindado); tribal/core/modelos.py (intencion_llm con caducidad); tribal/sim.py (encolar un dilema por tick, drenar al final, aplicar intencion con fallback, resumen llm); tribal/cli.py (--llm off|stub|http, --llm-sincrono, --llm-max-en-vuelo); tests/test_llm_cola.py (nuevo, 12 casos); README; vault/01_PROYECTO/arquitectura.md (§3)
- **Decisiones:** El bucle nunca llama al LLM: encola con put_nowait, drena con get_nowait y aplica una intencion con caducidad; si no llega o caduca, el instinto manda. El cierre es el punto dificil: hay que dejar de aceptar, vaciar pendientes (descartadas), poner el centinela y esperar como maximo una inferencia, no N; el reviewer reprodujo el fallo original (en_vuelo=2 y hilo vivo) y ahora n=1,2,4 cierran en ~250 ms con en_vuelo=0 y sin hilos. Contadores separados: fallos son errores del transporte y descartadas incluye fuera de ventana y pendientes al cerrar. El modo sincrono solo existe para tests con stub; con http se rechaza para no congelar el bucle. En asincrono el resumen completo no es reproducible por construccion (el tick de llegada varia); el determinismo se prueba con --llm-sincrono. Deuda: ACCIONES_SIN_PARAMETROS duplica parte del vocabulario sin test de sincronia y la eleccion de dilema no usa saliencia (F2-004).
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
"success": true | "ready": true | "errors": 0 | "warnings": 0 | pytest 298 passed

$ backend lento 200 ms, 1200 ticks
1200 ticks en 0.91 s ; durante cada peticion (0.218 s reales) avanzaron 318/266/244 ticks
coste por tick: 0.754 ms medio, 1.697 ms maximo, p99 1.20  (presupuesto 16.67)
todas las llamadas asincronas registradas en el hilo `tribal-llm`

$ cola
max_en_vuelo 1/3/7 -> en_vuelo_max exactamente 1/3/7 ; rechazo con cupo lleno en 0.19-0.57 ms
drenar no bloquea ; decision con tick fuera de ventana -> descartada, sin intencion viva

$ cierre (bloqueante de la ronda 1)
n=1,2,4 con transporte que consume el timeout: True en ~250 ms, en_vuelo=0, hilos=[]
segunda llamada idempotente ; invariante enviadas == aplicadas+descartadas+fallos+en_vuelo
--llm http sin servicio: 3.97 s, exit 0, {"peticiones":4,"aplicadas":0,"descartadas":3,
  "fallos":1,"en_vuelo":0}, cero hilos huerfanos en dos partidas seguidas

$ run --headless --json --llm stub --ticks 1200
{"peticiones": 88, "aplicadas": 2, "descartadas": 1, "fallos": 0, "en_vuelo": 0}
--llm off -> resumen byte-identico a HEAD
--llm-sincrono --llm http -> exit 2 con mensaje (no congela el bucle)
guard: moverse/ensenar/cuidar/huir sin parametros no se aplican; resumen identico a instinto puro

$ uv run pytest -q
854 passed, 15 skipped
$ uv run ruff check tribal/ tests/ agents/  -> All checks passed!
$ uv run ruff format --check tribal/ tests/ -> 55 files already formatted
$ uv run mypy tribal/ tests/                -> Success: no issues found in 55 source files
```

</details>

## F2-CONTRATO — F2: contrato candidatas -> elige -> valida para la decision

- **Cerrada:** 2026-11-19
- **Verificación:** ./init.sh en verde · 322 passed in 159.18s (0:02:39)
- **Cambios:** tribal/llm/candidatas.py (nuevo: 2-4 acciones viables filtradas por reglas y borde sin terreno); tribal/llm/decision.py (prompt few-shot, enum restringido, temp 0.3, validacion dura con motivo); tribal/llm/eval.py (20 escenarios y acierto); tribal/llm/{esquema,cliente,cola}.py; tribal/sim.py (uso del contrato y corregidas en el resumen); tribal/instinto.py; tribal/cli.py (llm eval); tests nuevos y test_llm_cola.py; README; arquitectura.md §2.3
- **Decisiones:** El contrato es 'candidatas -> elige -> valida': las reglas proponen 2-4 acciones fisicamente viables (sin agua no hay beber, sin amenaza no hay huir), el LLM elige con few-shot y temp 0.3, y el motor solo corrige si la eleccion no esta entre las candidatas o viola una restriccion dura; una eleccion valida no se segundea. La invariante 2-4 se garantiza anadiendo moverse/descansar; el unico borde (sin terreno pisable) devuelve 1 y no pide decision, documentado. llm eval con backend simulado mide el contrato y el filtrado (>70 por ciento), no la calidad del modelo: el acierto real del modelo se mide con --backend http, fuera de CI. Deuda: docstring de sim._intencion_llm desactualizado, corregidas se cuenta al aceptar (no en registrar_aplicada) y _encolar_dilema calcula candidatas de todos cada tick (barato a 12, a vigilar con mas poblacion).
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
"success": true | "ready": true | "errors": 0 | "warnings": 0 | pytest 322 passed

$ candidatas() (2-4 con al menos dos acciones viables)
(100,0) sin recursos -> ['moverse','descansar']  ; _hay_dilema False
(45,60) sin recursos -> ['descansar','moverse']  ; _hay_dilema True
mundo todo agua      -> ['descansar']            ; _hay_dilema False (borde documentado)
20 estados aleatorios: 2-4 salvo todo-agua; toda candidata es viable y moverse lleva destino pisable

$ contrato
2 few-shot (o 1 inyectado por el cliente) ; temperature 0.3 en el payload real
enum del schema restringido a las candidatas ; ESQUEMA_RESPUESTA abierto de F2-001 intacto
valida: comer con [beber, comer] NO se corrige ; fuera de candidatas -> corrige ;
huir sin amenaza -> corrige ; transporte caido -> sin decision
correccion tardia no cuenta (0), en ventana si (1) ; corregidas en resumen()["llm"]

$ llm eval --backend simulado --json -> 20 escenarios, acierto 1.0 (test exige >0.70)
  el backend "competente" es una regla: mide el contrato y el filtrado, no el modelo
$ llm eval --backend http sin servicio -> sin_decision, exit 0

$ no regresion F2-002: cola, ventana de validez, cierre sin hilos, 1200 ticks con backend de 200 ms
  y determinismo del stub entre procesos; 60 fps (benchmark 1.18 ms/tick con 12)
$ --llm off identico a HEAD (seed 42, 600 ticks, hash 481326460)

$ uv run pytest -q
878 passed, 15 skipped
$ uv run ruff check tribal/ tests/ agents/  -> All checks passed!
$ uv run ruff format --check tribal/ tests/ -> 55 files already formatted
$ uv run mypy tribal/ tests/                -> Success: no issues found in 55 source files
```

</details>

## F2-003 — Embeddings en CPU y recuperacion de memoria

- **Cerrada:** 2026-11-19
- **Verificación:** ./init.sh en verde · 335 passed in 160.11s (0:02:40)
- **Cambios:** tribal/llm/embeddings.py (nuevo: Embedder, hashing determinista, Ollama CPU, IndiceRecuerdos con coseno y guarda de hilo); tribal/llm/http.py (transporte compartido); tribal/sim.py (indice de hitos, combinaciones y tradiciones; top-3 al contexto; memoria en el resumen); tribal/cli.py (selfcheck con embeddings); tests/test_embeddings.py (nuevo, 13 casos) y test_cli_run.py; README; arquitectura.md §2.3/§3
- **Decisiones:** El backend de tests es hashing con blake2b, no `hash()`: el segundo cambia con PYTHONHASHSEED y rompe la reproducibilidad entre procesos. La recuperacion devuelve top-k con coseno, orden (-score, id) y `zip(strict=True)`: dimensiones distintas son un error, no un recorte silencioso. La guarda de contexto es real (hilo tribal-llm y pila de tribal.ui.render, tambien a 2 niveles) y se probo mutandola. La integracion tiene test que captura la Peticion y exige memoria con ids reales y scores ordenados, de modo que renombrar la clave o desactivar el indexado ahora rompe la suite (M1 y M5 caen). Se indexan hitos, combinaciones y tradiciones; no se exige recuerdos == nodos porque no todo nodo tiene texto indexable. Coste medido: 1.43 ms/tick medio con 24-28 hitos.
- **Pendiente:** _(nada)_

<details><summary>Evidencia</summary>

```
$ uv run python -m agents --json run harness gate
"success": true | "ready": true | "errors": 0 | "warnings": 0 | pytest 335 passed

$ embeddings
EmbedderHashing: blake2b, 256 dims, L2 (norma 1.0); vacio -> vector nulo; dim<1 -> ValueError
mismo vector y mismo orden con PYTHONHASHSEED 0/1/2/12345 (4 subprocess)
top-1 exacto en 10 consultas; empates ordenados por id; k > recuerdos no rompe
EmbedderOllama con servicio caido -> vector nulo + ultimo_error, sin excepcion
usa_gpu false en los tres backends

$ guarda de hilo
llamada desde `tribal-llm` o desde la pila de `tribal.ui.render` -> RuntimeError
(probado tambien a 2 niveles); app.bucle no anida step/render (sin falso positivo)

$ selfcheck
"embeddings": {"backend": "hashing", "usa_gpu": false, "dim": 256}

$ integracion (600 ticks, seed 7)
recuerdos 22 == nodos 22 (incluye 4 tradiciones) ; recuperaciones 337
seed 42: 24==24, 287 peticiones, 0 sin memoria, 0 ids fuera del indice, scores descendentes
seeds 1/2/3/5/7: recuerdos == nodos ; --llm off -> memoria {0,0} e identico entre runs
coste: tick 1.43 ms medio, p95 1.90, max 2.83 (presupuesto 16.67)

Mutaciones detectadas: M1 contexto["memoria"] renombrado | M5 _registrar_recuerdo no-op |
tradiciones sin indexar | zip strict=False | hash() | quitar guarda | desempate por insercion

$ uv run pytest -q
891 passed, 15 skipped
$ uv run ruff check tribal/ tests/ agents/  -> All checks passed!
$ uv run ruff format --check tribal/ tests/ -> 55 files already formatted
$ uv run mypy tribal/ tests/                -> Success: no issues found in 66 source files
```

</details>
