# reviewer · F2-006

- **Fecha:** 2026-11-19
- **Veredicto:** aprobado

# reviewer · F2-006

- **Fecha:** 2026-11-19
- **Veredicto:** aprobado

## Criterios

### 1. E2E con backend guionizado y semilla fija: >= K nodos fuera que pasan plausibilidad — CUMPLIDO
`tests/test_puerta_f2.py::test_gate_f2_e2e_crea_nodos_y_rechaza_los_imposibles`
pasa (3000 ticks, semilla 1). Reproducción propia de
`report gate-f2 --seeds 1-5 --ticks 3000 --crisis`, fila por fila idéntica a la
del implementer: fuera = 13/14/14/12/15; llm = 8/9/9/7/10.

Auditoría mecánica de **todos** los nodos `origen="llm"` de las semillas 1, 3 y
5 (27 nodos): requisitos existentes y `activo`, rama propuesta igual a una de
las dos y las dos de la misma rama o adyacentes en `RAMAS`, id fuera de `ARBOL`
y de `COMBINACIONES`, y `tick` del requisito anterior al del nodo. **0
incumplimientos**. Ningún `propuesta_imposible_*`/`propuesta_lejana_*` inscrito.
Rechazos contados y con motivo: 4-5 por semilla (`prerrequisito`, `rama`).

El backend no inyecta nodos: solo devuelve JSON por el canal de la cola y el
único camino de escritura es `propuestas.validar` → `Grafo`.

### 2. Top-3 de saliencia concentra >= 50 % de las líneas de narración — CUMPLIDO
Reproducción propia: 0.6 / 0.8 / 0.5 / 0.8 / 0.6 (exactos 0.6429 y 0.5000 en
las semillas 1 y 3). Medido sobre `simulacion.diario.entradas` con
`narrada and narrador_id is not None` (14/17/16/16/15 líneas), no sobre pesos.
`concentracion = líneas de los 3 con más peso acumulado / líneas narradas`.

No hay truco de un solo individuo: el reparto real es 4-5 narradores por
partida y la cuota máxima de una persona es 0.43 / 0.50 / 0.47 (semillas 1, 3,
5), nunca > 90 %. La mutación de abajo demuestra que el número mide algo: con
narrador aleatorio cae a 0.167.

### 3. `report culture --json` muestra nodos fuera del árbol con origen y autor — CUMPLIDO
Ejecutado el comando literal (sin `--crisis`, 600 ticks por defecto): 7 nodos
`interaccion` con `origen`, `autor` y `tick` (`tradicion_ritual` autor 9 tick
12, `tradicion_lider` autor 6 tick 511, ...). Con `--crisis --ticks 3000`
aparecen además las 5 `combinacion` con autor y tick. El campo se calcula
filtrando `grafo["nodos"]` en `_report`; no está hardcodeado.

### 4. Gate — CUMPLIDO
`uv run python -m agents --json run harness gate` → `success=true`,
`ready=true`, `errors=0`, `warnings=0`, `pytest: 378 passed in 207.64s`.

## Verificaciones adicionales
- **Determinismo síncrono:** dos `report gate-f2 --seed 1 --ticks 3000 --json`
  con hash idéntico. Asíncrono está documentado como no reproducible en
  `README.md` (líneas 144-148) y `arquitectura.md` (247-250); `--llm-sincrono`
  es el default de `gate-f2`.
- **Control negativo:** `--llm off` → `success=false` con
  `al_menos_un_llm=false`, `concentracion_top3=false`,
  `rechazo_demostrado=false`. El veredicto no está cableado a `true`.
- **K no es el catálogo entero:** el canal `llm` por sí solo da 7-10 nodos
  (>= 5) en las cinco semillas; `combinacion + llm` no depende de contar el
  catálogo.
- **Mutaciones** (aplicadas y revertidas; `tribal/sim.py` restaurado con hash
  idéntico):
  1. `puede_proponer = False` → el e2e falla en `assert fila.por_origen["llm"]
     >= 1` (`0 >= 1`).
  2. Narrador aleatorio (`azar.choice` en `_narrador`) → el test de
     concentración falla en ambas semillas (`0.167 >= 0.5`).
- **Regresiones:** `uv run pytest -q` → **934 passed, 15 skipped** (coincide
  con el informe; incluye `agents/tests`). `tests/` sigue en 378. `ruff check`,
  `ruff format --check` y `mypy` en verde (73 ficheros). El test de 60 fps
  (`test_benchmark_cabe_en_el_presupuesto_de_frame`) va en esa suite.
  F2-002/003/004/005 no tienen ficheros de test modificados.
- **Alcance:** `pyproject.toml` y `uv.lock` sin cambios (sin deps), sin
  canales de fitness nuevos (`genoma`/beneficios intactos), sin `.tmp-*`,
  `opencode.json` y `docs/art` fuera del diff.
- **Secretos:** `secrets scan` sale con 13 hallazgos, **todos** en
  `agents/tests/test_redaction.py` y `agents/tests/test_secrets_agent.py`
  (fixtures de esos agentes, preexistentes); ninguno en `tribal/`.

## Bloqueantes
Ninguno.

## No bloqueante
1. **El guion siempre propone el mismo menú.** `_propuesta` ordena por id y
   toma el primer par, así que los 8-10 nodos `llm` de cada semilla son
   `cruce de ahuyentar_depredadores y X` y los ids se repiten entre semillas
   (`llm_577c0387d5bd`, `llm_e4abd1ab39cf`, ...). Demuestra el canal y la
   validación, no la variedad del inventor. Para F3, rota el nodo pivote o
   muestrea el par.
2. **Los documentos prometen más K del que el código exige.** README y §9.4
   dicen que K=5 son «todos los cruces del catálogo»; el veredicto solo pide
   `combinacion + llm >= 5` y `llm >= 1`. Con `--llm off` el criterio K sigue
   en `true` (combinacion=5). Lo que caza el canal apagado es `llm_ok`, no K.
   Conviene redactarlo así.
3. **Margen justo en la semilla 3:** concentración exactamente 8/16 = 0.500.
   Cualquier cambio que mueva una línea rompe el test. El test fija 1 y 3; la
   tabla publica las cinco. Añadir la 4 o la 5 daría margen.
4. **El top-3 final está dominado por muertos** (semilla 1: 9, 16 y 2, los tres
   muertos; el 16 narra 0 líneas). La métrica es conservadora —un muerto no
   narra, así que solo puede bajar el número— pero la columna `top3` del
   informe se lee como si fueran narradores activos. Marcar vivos/muertos o
   congelar el peso al morir lo aclararía.
5. **`_lejana` puede devolver una pareja adyacente real:** `lenguaje` y `roles`
   son vecinas en `RAMAS` y están en las listas de `primera`/`segunda`. Solo lo
   salva el orden del bucle (siempre entra `litica` primero). Si alguna vez no
   hubiera nodos de `litica` activos, esa «lejana» se aceptaría como `llm`.
   Latente.
6. `PeticionNodo.valida_hasta` se calcula y no se usa: `drenar_propuestas`
   compara contra `propuesta.tick + self.ventana`. Campo muerto.
7. `report culture` corre sin cola LLM, así que su `fuera_arbol` nunca podrá
   contener un nodo `llm`, aunque el comentario del CLI y el README digan que
   lo publica. Cierto en el filtro, imposible en la práctica.
8. El working tree arrastra `HARD-2` (blocked) y `HARNESS-REMOVE` (nueva) en
   `featureslist.json`. El log de auditoría confirma que los hizo el líder con
   `harness block/add/edit` (12:00-12:06), no el implementer, y no viola la
   regla de dueño. Solo conviene que no se mezclen en el commit de F2-006.
