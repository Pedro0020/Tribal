# reviewer · F1-002

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

## Criterios

1. **`tribal/culture/arbol.py` define las cinco ramas con niveles y prerrequisitos — CUMPLIDO.**
   `pytest tests/test_arbol.py -q` → `11 passed`. Verificado además a mano: 23 nodos, ids únicos,
   ramas exactas `{litica, fuego, lenguaje, roles, simbolico}`, escaleras completas
   (litica 0-4, fuego 0-4, lenguaje 0-3, roles 0-2, simbolico 0-3), cero requisitos inexistentes,
   cero ciclos, nivel 0 sin requisitos. Los cruces están justificados por escrito en
   `tribal/culture/arbol.py:5-11` (`mito` ← `proto_palabras`+`ritual`, `lider` ←
   `anciano`+`caza_cooperativa`); `anciano` tiene dos requisitos pero dentro de `roles`, no cruza.
   Coherente con concepto §8 (`vault/01_PROYECTO/concepto.md:131-139`).

2. **El motor rechaza sin prerrequisitos y registra el origen al crear — CUMPLIDO.**
   `Grafo().descubrir("lasca", autor=1, tick=10)` → `PrerequisitoFaltante: lasca: faltan
   prerrequisitos guijarro`, y `nodos == {}`, `aristas == []` (no deja rastro). Con `guijarro`
   → `Nodo(origen='arbol', autor=5, tick=42, estado='activo')` y arista `guijarro → lasca`.
   Idempotente: `descubrir("lasca", autor=99, tick=999, origen="combinacion")` devuelve el mismo
   objeto con `('arbol', 5, 42)`. Origen no reescribible por API: `nodo.origen = "llm"` y
   `nodo.__setattr__("origen","llm")` → `FrozenInstanceError`; `dataclasses.replace` crea otro
   objeto y el guardado sigue `arbol`. Mutación verificada: quitar el `raise` →
   `1 failed, 3 passed`; quitar el early-return idempotente → `1 failed, 6 passed`.

3. **Tests de los tres enunciados — CUMPLIDO.** `tests/test_arbol.py:54` (sin prerrequisito no hay
   nodo), `:65` (nace con origen `arbol`, autor, tick y arista), `:83` (no reescribible +
   idempotente). Los tres caen si se revierte el comportamiento (mutaciones 1 y 2).

4. **`report culture --json` imprime nodos, aristas y `pct_fuera_arbol` — CUMPLIDO.**
   Salida real: `{"seed": 42, "ticks": 600, ... "nodos": [5], "aristas": [4],
   "pct_fuera_arbol": 0.0, "nodos_por_origen": {"arbol": 5, ...}}`. Número, no cadena. No es
   constante: inyectando un nodo `combinacion` en el grafo, `pct_fuera_arbol()` → `33.3`
   (2 arbol + 1 combinacion). Dos subprocesos con mismo seed/ticks → salida idéntica
   (`Compare-Object` vacío). `--ticks 0` → error 2; `--ticks 1` → listas vacías y `0.0`.
   El hecho de que `llm` no cuente como "fuera" coincide con el SQL de `objetivo.md` §3.2
   (`origen IN ('combinacion','interaccion')`).

5. **`harness gate success=true` — CUMPLIDO.**
   `success: true`, `message: "ENTORNO LISTO — se puede trabajar."`, 0 errores, 0 avisos,
   `pytest 98 passed in 11.34s` (la puerta corre solo `tests/`; el total del repo es 627).

## Verificación extra

- **Integración**: `PRACTICAS = {'comer': ('recolectar', 'litica')}`. Gate de habilidad probado
  a mano: individual sin `recolectar` → `_practicar(..., "comer") == False` y `nodos == []`; con
  la habilidad → `True` y nace `guijarro`. Acción sin práctica (`beber`) → `False`.
  Instrumentando `Grafo.descubrir`: `{263: 1, 272: 1, 279: 1, 313: 1, 319: 1}`, máximo 1 por
  tick. `sim.resumen()` y `run --headless --json` deterministas en dos subprocesos.
- **Fuego sin lítica**: los nodos de fuego con prerrequisitos (`conservar_brasas`, `friccion`,
  `cocinar`) se rechazan sin su cadena. `observar_rayo` es nivel 0 y por diseño no exige nada
  (concepto §8), así que sí se puede descubrir sin `lasca`; en la corrida real no aparece porque
  no hay práctica de fuego en `PRACTICAS` (ramas descubiertas: solo `litica`).
- **Regresiones**: `uv run pytest -q` → `627 passed, 15 skipped`; F0+F1-001
  (`test_puerta_f0`, `test_habilidades`, `test_genoma`, `test_motor`) → `47 passed`;
  `--benchmark` → `0.47 ms/tick` (< 16.67); `pygame` no se importa al cargar
  `tribal.culture.*` ni `tribal.sim`.
- **Calidad**: `ruff check tribal/ tests/ agents/` → All checks passed; `ruff format --check` →
  35 files already formatted; `mypy tribal/ tests/` → no issues; cobertura 95.7 %
  (arbol 96.3 %, grafo 100 %); `doctor checkup` → 7/7.
- **Alcance**: diff solo `README.md`, `tribal/cli.py`, `tribal/sim.py`, `tests/test_cli_run.py`
  (+4 claves) y los nuevos `tribal/culture/*`, `tests/test_arbol.py`. Sin deps nuevas
  (`pyproject.toml` sin cambios), sin `.tmp-*`, sin `agents/` tocado. Los cambios en
  `harness/featureslist.json` y `current.md` son los que escribe `harness start`
  (`agents/agents/harness_agent.py:377-398`), no edición a mano.
- **Secretos**: `secrets scan` marca 13 hallazgos, todos en fixtures preexistentes de
  `agents/tests/test_redaction.py` y `test_secrets_agent.py`; ninguno en el diff.

## Bloqueantes

_(ninguno)_

## No bloqueante

1. **`tribal/sim.py:197-198`: el gate de habilidad y el tope de un nodo por tick no tienen test.**
   Quitando `if not individuo.habilidades.sabe(habilidad): return False` la suite sigue
   `98 passed`. Es comportamiento nuevo del motor y hoy nadie lo protege.
2. **`tribal/sim.py:122-125`**: el tope de un nodo/tick tampoco está fijado por test; solo lo
   garantiza el `and not descubierto`. Se verificó instrumentando `descubrir`, no con un test.
3. **`tribal/culture/grafo.py:90`**: el docstring dice «% de nodos activos de origen no `arbol`»
   pero `:94` solo cuenta `combinacion`/`interaccion` (excluye `llm`). Coincide con el SQL de
   `objetivo.md` §3.2, pero el texto debería decir «niveles 1 y 2».
4. **`tribal/culture/grafo.py:89-95`**: el camino no-cero de `pct_fuera_arbol` no tiene test;
   hardcodear `return 0.0` deja `98 passed`. Añadir un test con un nodo `combinacion`
   (esperado 33.3) convertiría la única evidencia en una aserción.
5. **`tribal/sim.py:48-50`**: `comer` + `recolectar` (que `core/habilidades.py:32` clasifica como
   rama `roles`) hace avanzar `litica`. Es un enlace causal débil y discrepa de la rama de la
   habilidad; conviene justificarlo o corregirlo cuando F1-003 añada transmisión.
6. **`tribal/culture/grafo.py:46`**: `nodos` es un dict público; `object.__setattr__` sobre el
   `Nodo` frozen también muta el nodo guardado. No hay API que reescriba `origen`, pero el
   invariante no está encapsulado (un `Mapping` de solo lectura o `_nodos` lo cerraría).
7. **`tribal/cli.py:29`**: `build_parser` ha pasado a 66 líneas (> umbral 60 de
   `review_package`). Es un smell, no un fallo; `report` añade ~30 líneas al mismo embudo.
8. **`tribal/culture/grafo.py:76-87`**: `avanzar` no vuelve a descubrir un nodo ya presente
   aunque su `estado` sea `apagado`, así que una rama «perdida» se queda sin salida. Hoy no hay
   `apagar()`, pero el campo `estado` ya existe; decidirlo antes de F1-004.
9. **`arbol.py:29` / `grafo.py:97`**: `llm` se cuenta en `nodos_por_origen` pero no es un nivel
   de §8b (0/1/2). Es coherente con la métrica de concepto, solo despista en el comentario.
10. `review_package` marca un `todo_comment` en `arbol.py:28`: es un falso positivo («todos»,
    minúscula, dentro de una frase).
11. **Automejora (este fichero)**: corregidos dos comandos muertos de mi propia definición —
    `test coverage_summary` no existe (es `coverage_report`) y `doctor` exige acción
    (`doctor checkup`). Queda pendiente que `harness` (dueño de `history.md`) anote el cambio.

## Línea de gate

`uv run python -m agents --json run harness gate` → `success: true` ·
`message: "ENTORNO LISTO — se puede trabajar."` · `errors: 0`, `warnings: 0`, `pytest 98 passed`.
