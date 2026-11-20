# Auditoría del LLM — estado y hoja de soluciones

> **Estado:** CERRADO el 2026-11-19. Documento de análisis, no de implementación.
> **Propósito:** dejar anotado el diagnóstico del uso del LLM y una hoja de
> soluciones completa, para que en el futuro se pueda volver aquí, auditar,
> decidir y añadir tareas al backlog **a mano**. No se toca el backlog desde
> aquí.
> **Método:** análisis estático del código y de los documentos de diseño. §1
> añade además la medición de acciones de MEDIR-LLM: una corrida real con
> `--llm http` y otra con el stub determinista, con su comando.
> **Alcance:** toda la capa `tribal/llm/`, sus puntos de integración en
> `tribal/sim.py`, el instinto, la saliencia, la memoria, el diario, el árbol de
> cultura y el KPI de emergencia.

---

## 0. Cómo usar este documento

1. Leer el **resumen ejecutivo** (§1) para el veredicto.
2. Ir al **inventario** (§2) para el detalle de cada pieza con su referencia de
   código exacta (archivo + símbolo).
3. Ir a la **hoja de soluciones** (§4) para las propuestas; cada una lleva un id
   (A1, B2, …) para poder citarla al crear una feature.
4. Cuando se retome, leer **decisiones pendientes** (§7) y convertir las
   soluciones elegidas en features del backlog con sus criterios de aceptación.
5. Al terminar una ronda de cambios, volver a **§8** para re-auditar.

---

## 1. Resumen ejecutivo (veredicto)

**El LLM está infrautilizado: decide el 0,0 % de las acciones en el modelo real
y el 9,5 % con el stub determinista, y lo hace como un selector de candidatas,
no como el "motor central" que promete `concepto.md §2`.**

Medido con `resumen()["llm"]["acciones"]` (MEDIR-LLM), no con las peticiones
enviadas: una acción cuenta para el LLM solo si aplicó una intención vigente;
encolar no cuenta y una corrección del motor tampoco.

| Corrida | Acciones LLM | Acciones instinto | % LLM |
|---|---|---|---|
| Modelo real `tribal-llm` | 0 | 24 972 | **0,0 %** |
| Stub determinista | 1 400 | 13 359 | **9,5 %** |

```bash
# modelo real: 1 petición enviada, 3 descartadas al cerrar, 0 acciones decididas
uv run python -m tribal run --headless --json --llm http --ticks 2000 --seed 1 --crisis
# stub: techo del cableado, no del modelo
uv run python -m tribal run --headless --json --llm stub --llm-sincrono --ticks 1200 --seed 42
```

En la corrida real el tick corre mucho más rápido que la inferencia: la partida
termina antes de que el modelo responda. El 9,5 % del stub mide el cableado
—qué decidiría si respondiera a tiempo—, no la calidad de `tribal-llm`.


El modelo entra en exactamente **tres sitios** de `tribal/sim.py`, todos
estrechísimos:

| Canal | Dónde | Gatillo real | Magnitud por partida |
|---|---|---|---|
| **Decidir** | `_encolar_dilema()` | `_hay_dilema`: sed crítica **Y** energía baja a la vez, o salud crítica | Muy raro: en calma casi nadie lo cumple |
| **Narrar** | `_hito()` | Solo hitos (fuego, palabra, rito, caza, muerte de anciano) **y** solo si hay narrador con saliencia > 0 | ~6–15 frases |
| **Proponer** | `_solicitar_propuesta_llm()` | Solo en **crisis** + individuo **divergente** + **cada 200 ticks** | ~15, y la mayoría delega al catálogo |

Todo lo demás —beber, comer, huir, moverse, descansar, deambular, enseñar,
cuidar, practicar— lo cubre `instinto.elegir`, una política **determinista sin
LLM** (≈100 % de las acciones en la corrida real y ≈90,5 % con el stub: 12
individuos × 3000 ticks ≈ 36.000 acciones por partida).

### Los tres principios rectores que salen del análisis

1. **El árbol no se define, se descubre.** Las ramas y las eras no deben
   hardcodearse; deben *emerger* de lo que la tribu realmente combinó, transmitió
   y seleccionó. El árbol se dibuja *después*, no se escribe *antes*.
2. **El pensamiento debe persistir.** Hoy el LLM piensa un instante
   (`accion + razon + dialogo`) y lo que dice se descarta. Un sistema que
   "piensa, profundiza y evoluciona" necesita un **bucle cerrado**:
   pensar → decir/hacer → quedar escrito en memoria/grafo → informar el próximo
   pensamiento.
3. **Modelo multi-nivel con router y límites de hardware.** Un modelo pequeño y
   barato para lo trivial, otro más potente (con offload VRAM+RAM) para razonar,
   narrar e inventar, y un enrutador que elige el nivel según la profundidad de
   la decisión, respetando un presupuesto de hardware (freno térmico, duty
   cycle).

---

## 2. Inventario por pieza (análisis exhaustivo)

### 2.1 El modelo — `tribal.Modelfile`, `tribal/llm/cliente.py`
- **Qué es:** alias de Ollama `tribal-llm`, base `qwen2.5:3b-instruct-q8_0`.
  Parámetros del alias: `num_ctx 8192`, `temperature 0.7`, `top_p 0.9`,
  `repeat_penalty 1.1`.
- **Dónde se sirve:** `127.0.0.1:11434/api/chat`. Medido ~66 tok/s, ~3.6 GB VRAM
  en RTX 2060 6 GB (stack §2).
- **Embeddings:** `qwen3-embedding:0.6b`, pedido en CPU.
- **Observaciones de auditoría:**
  - `temperature 0.7` en el Modelfile convive con `TEMPERATURA = 0.3` que el
    cliente manda por petición (`cliente.py`, `decision.py`). Hay que confirmar
    que `options.temperature` de Ollama **sobreescribe** el default del alias; si
    no, se estaría decidiendo a 0.7 y no a 0.3.
  - `MAX_TOKENS = 64` (decisión/narración) y `128` (propuesta) en `cliente.py`
    contradicen el presupuesto de `stack §8` (`num_predict ≤ 32`).
  - El modelo es **único** para los tres roles (decidir, narrar, inventar). No
    hay separación de modelos ni de parámetros por rol.
  - El modelo base es de la generación **Qwen2.5** (una generación por detrás
    del estado del arte local de 2026). El catálogo de candidatos y el veredicto
    de sustitución están en §9.

### 2.2 El transporte — `tribal/llm/http.py`
- `Transporte = Callable[(método, url, cuerpo, timeout) -> (estado, bytes)]`,
  con `transporte_http` sobre `urllib` stdlib. Inyectable para tests.
- **Correcto y minimalista.** Sin deuda relevante. Es la base sobre la que un
  futuro router multi-modelo puede apoyarse sin cambio de contrato.

### 2.3 El cliente — `tribal/llm/cliente.py`
- `ClienteLLM` síncrono: `decidir`, `narrar`, `proponer`, `intercambiar`,
  `disponible`. **Nunca lanza** (todo fallo → `degradado`/`error`).
- Backends falsos: `backend_stub` (determinista por SHA-256), `backend_falso`
  (cola para tests).
- **Correcto.** La deuda está en el *uso* que se le da (un solo modelo, un solo
  timeout de 3 s, `num_predict` plano), no en la mecánica.

### 2.4 El esquema y los prompts — `tribal/llm/esquema.py`
- Tres roles con prompt y JSON schema propios:
  - **Decididor** (`SISTEMA`): "eres un homínido… elige una candidata".
  - **Cronista** (`SISTEMA_NARRACION`): "una frase en español sobre el hito".
  - **Inventor** (`SISTEMA_PROPUESTA`): "propón una técnica que combine dos
    técnicas activas".
- Few-shot `EJEMPLOS` (2 ejemplos de estado→acción).
- **Observaciones:**
  - El system prompt es **único para todos los individuos**. El genoma
    (inteligencia, divergencia), las habilidades, la saliencia, el rol y la
    historia personal **no llegan al prompt** salvo un `estado` plano de números.
  - El cronista escribe español fluido desde el tick 0, aunque el hito sea
    "primera palabra". No hay **evolución del lenguaje**.
  - El inventor queda atado a "misma rama o adyacente" (la validación real está
    en `propuestas.py`, no en el prompt).

### 2.5 Las candidatas — `tribal/llm/candidatas.py`
- `estado_para()` serializa el estado a datos planos (energía, sed, salud,
  `agua_al_alcance`, `comida_al_alcance`, `amenaza`, `vecino`, `bosque`,
  `agua_cerca`).
- `candidatas()` filtra 2–4 acciones físicamente viables. Invariante 2–4.
- **Correcto y bien acotado.** Es el corazón del contrato "candidatas → elige".
  El problema no está aquí, está en que este filtro **es lo único** que ve el
  LLM: no hay contexto social, cultural ni de memoria relevante en el prompt.

### 2.6 La validación — `tribal/llm/decision.py`
- `decidir_con_candidatas()` valida y corrige solo violaciones duras (`huir` sin
  amenaza, `beber` sin agua, `comer` sin comida). Una elección válida no se
  segundea.
- **Correcto.** Refuerza el principio "el LLM elige, el motor valida".

### 2.7 La cola — `tribal/llm/cola.py`
- Hilo daemon único + colas acotadas. `max_en_vuelo=4`, ventana de validez
  `180` ticks. Métricas: enviadas, aplicadas, descartadas, fallos, corregidas,
  en_vuelo, latencia media.
- **Correcto y robusto.** El presupuesto de inferencia está bien implementado.

### 2.8 Los embeddings y la memoria — `tribal/llm/embeddings.py`
- `EmbedderHashing` (determinista, default) y `EmbedderOllama` (real, CPU).
- `IndiceRecuerdos.buscar()` devuelve top-k por coseno, con guarda de contexto
  (no corre en hilo de render ni del LLM).
- **Observaciones (críticas):**
  - La recuperación solo inyecta `{"id", "score"}` en el contexto
    (`sim.py _recuperar_memoria`), **no el contenido del recuerdo**. El texto
    no viaja al prompt: el LLM no "lee" la memoria, solo recibe IDs.
  - La narración y el diálogo **no escriben** en la memoria. El bucle está
    abierto: se lee (IDs) pero no se escribe lo que el LLM produce.

### 2.9 El eval — `tribal/llm/eval.py`
- 20 escenarios con una acción claramente correcta. En CI corre con
  `backend_competente` (simulado, elige por utilidad): mide el **contrato**, no
  la calidad del modelo.
- `llm eval --backend http` existe para correrlo contra el modelo real, pero la
  calidad del modelo real **no tiene una métrica publicada** comparable entre
  commits (a diferencia del RAG, que tiene `eval-rag`).

### 2.10 El gatillo del pensamiento — `tribal/sim.py`
- `_encolar_dilema()`: hasta `max_pensando` (default 4) peticiones por tick,
  ordenadas por saliencia.
- `_hay_dilema()`: `(sed_critica AND energia_baja) OR salud_critica`, y ≥2
  candidatas.
- **Observaciones (críticas):**
  - El gatillo es un **embudo de dos condiciones AND**. En una partida sana casi
    nadie tiene sed y hambre críticas a la vez, así que "pensar" es raro.
  - La saliencia ordena *quién* piensa, pero si nadie tiene dilema, **nadie
    piensa**.
  - El instinto ya cubre esos dilemas con acierto total; el LLM no aporta en el
    caso trivial, y no se le convoca en los casos donde aporta (lo social, la
    innovación, la interpretación).

### 2.11 La saliencia — `tribal/agents/saliencia.py`
- Peso narrativo ganado por hitos (`primer_nodo`, `combinacion`, `tradicion`,
  `ensenanza`, `rescate`, `crisis`), con decaimiento `0.999` y techo `10`.
- **Correcto como mecanismo**, pero su único uso es *racionar* la cola y *elegir
  narrador*. No alimenta el prompt ni la personalidad: un individuo saliente no
  piensa "más profundo", solo "más a menudo".

### 2.12 El instinto — `tribal/agents/instinto.py`
- Política determinista que cubre el resto de las acciones: sed→beber,
  hambre→comer, lobo→huir, ocio→enseñar/cuidar/practicar/deambular. Medido con
  `resumen()["llm"]["acciones"]` (MEDIR-LLM, §1): **100 % en la corrida real y
  ≈90,5 % con el stub**.
- **Observación (de fondo):** el instinto está **bien** y debe seguir como
  *sustrato determinista*. El error no es que exista, es que **no deja sitio** al
  LLM más que en un dilema estrecho. El instinto debería ser el nivel 0 de un
  router (reflejos), no el que se traga toda la vida mental.

### 2.13 El diario y la narración — `tribal/culture/diario.py`
- La entrada se registra siempre; la frase del cronista llega después (asíncrona)
  y se guarda tal cual (`narrada=True`).
- **Observación:** la narración es **decorativa**. El texto no vuelve al mundo:
  no afecta la cultura, la saliencia, el grafo ni la memoria. Es un `texto` que
  nadie lee dentro de la simulación.

### 2.14 El habla / diálogo — (no existe como canal)
- El campo `dialogo` de una decisión se vuelca al diario (`sim.py _drenar`) y se
  acabó. Dos individuos no conversan; no hay turnos, no hay transmisión de
  lenguaje, no hay proto-palabras → vocabulario. **Es la dimensión más ausente.**

### 2.15 El inventor y las propuestas — `tribal/culture/propuestas.py`
- `parsear` valida forma; `validar` decide plausibilidad contra el grafo.
- Regla: si el id está en `COMBINACIONES` → se delega al catálogo
  (`origen=combinacion`); si es nuevo → solo si los dos requisitos están activos
  y son de la misma rama o adyacente en `RAMAS` → `origen=llm`.
- **Observaciones (críticas):**
  - El catálogo tiene **prioridad** sobre el LLM (`sim.py _intentar_combinacion`):
    solo se propone al inventor cuando el catálogo se agota.
  - La validación `_ramas_plausibles` **ancla la categoría a `RAMAS`**: es el
    guion hecho código. El LLM no puede inventar una categoría nueva.
  - `origen=llm` es residual: casi todo lo "nuevo" es `combinacion` (guionado).

### 2.16 El árbol, las ramas y el catálogo — `tribal/culture/arbol.py`, `combinaciones.py`
- `RAMAS = (litica, fuego, lenguaje, roles, simbolico)` — **hardcodeado**.
- `ARBOL` = 23 nodos fijos con niveles y prerrequisitos. `COMBINACIONES` = 5
  cruces fijos.
- **Observación (de fondo):** hay tres capas mezcladas y solo una debería ser
  fija:
  1. **Acciones** (`beber`, `comer`…) → fija (es la "física" de lo que un cuerpo
     puede hacer). Correcto.
  2. **Nodos** (conocimiento) → debería ser semiabierto (emerger por combinación).
  3. **Ramas/eras** (categorías) → debería ser **derivada** del grafo, no una
     tabla. Aquí está el "siempre paleolítico": las 5 categorías son punto de
     partida **y** de llegada.

### 2.17 Las tradiciones — `tribal/culture/tradiciones.py`
- Nodo de `origen=interaccion` cuando un nodo se imita lo suficiente (3
  imitadores o 5 imitaciones en ventana). `rama` fija: técnicas→`roles`, resto→
  `simbolico`.
- **Correcto como mecanismo social**, pero también ancla su `rama` a una regla
  fija (`RAMAS_TECNICAS`). No hay tradición con contenido del LLM.

### 2.18 El KPI de emergencia — `tribal/culture/grafo.py`
- `pct_fuera_arbol()` = % de nodos activos con origen `combinacion` o
  `interaccion`. **`llm` NO cuenta** como fuera del árbol.
- `nodos_por_origen()` reporta los cuatro orígenes.
- **Observaciones:**
  - El KPI presupone un árbol fijo para medir "fuera de". Si las ramas emergen,
    el KPI debe pasar a "% fuera del **seed inicial**".
  - Al excluir `origen=llm`, el KPI desincentiva precisamente el canal que se
    quiere potenciar. Es una señal de que el canal LLM se considera "adorno".

### 2.19 La CLI y los informes — `tribal/cli.py`
- Comandos: `run --llm {off,stub,http}`, `report {culture,telemetry,diary}`,
  `gate`, `gate_f2`, `llm {selfcheck,eval}`.
- **Observación:** `report diary` y `report culture` existen, pero no hay un
  informe que muestre la *calidad* del modelo (coherencia, acierto real). El
  `resumen()` expone `llm.peticiones/aplicadas/descartadas/fallos`, pero no
  "cuánto pensó de verdad".

### 2.20 La configuración — `tribal/config.py`
- `max_pensando=4` (pensadores por tick), `max_en_vuelo=4` (cola). No hay
  parámetros para: modelo por rol, profundidad de razonamiento, presupuesto de
  hardware (freno térmico), ni umbral de dilema configurable.

---

## 3. Diagnóstico del subuso (causas de raíz)

1. **La conclusión de viabilidad se volvió techo — pero el diagnóstico es una
   falsa dicotomía.** `viabilidad-modelo.md` dijo "el 3B no genera acciones
   desde cero, sí elige entre candidatas" y se construyó el contrato
   candidatas→elige para el rol *decidir*, que era lo correcto (generar desde
   cero fallaba 1/6). Lo que nunca se construyó no fue eso, sino los otros roles
   de `concepto.md §10` donde el modelo sí aporta: el diálogo (A) y el contenido
   simbólico (E3). No se "abandonó una fortaleza a favor de una debilidad": se
   construyó un canal y se dejaron los demás sin construir.
2. **Gatillo del pensamiento estrecho** (`_hay_dilema`: dos condiciones AND).
3. **Narración decorativa** (no retroalimenta el mundo).
4. **Habla inexistente** (el `dialogo` no conversa con nadie).
5. **Inventor capado** por el catálogo y por `_ramas_plausibles`.
6. **Prompt único** (sin persona ni contexto cultural).
7. **Un solo modelo** para todo, con discrepancias de temperatura/tokens.

---

## 4. Hoja de soluciones (por dimensión)

Cada ítem lleva **id** (para citarlo al crear features), **problema**, **solución**
y **criterio esbozado**. El orden dentro de cada bloque es de menor a mayor
alcance.

### A. Habla / diálogo

- **A1 — Conversación entre individuos.** `hablar` hoy solo transmite habilidades
  por probabilidad. Convertirlo en un canal LLM de turnos (dos individuos, un
  intercambio corto) cuando ambos tienen saliencia o un vínculo.
  *Criterio:* un test con backend falso muestra un diálogo de ≥2 turnos asociado
  a los dos individuos; el diálogo se indexa en memoria.
- **A2 — Evolución del lenguaje.** El diálogo y la narración deben **depender de
  la rama `lenguaje`**: sin `proto_palabras` → gestos/onomatopeyas; con
  `proto_palabras` → frases de 2–3 palabras; con `vocabulario` → sintaxis.
  *Criterio:* el mismo hito narrado con y sin `proto_palabras` produce textos de
  distinta complejidad; el nivel lingüístico se refleja en la salida.

### B. Razonamiento

- **B1 — Razonamiento escalonado por profundidad.** Tres niveles de inferencia:
  (0) instinto, (1) elección corta (temp 0.3, ~32 tokens), (2) razonamiento rico
  (temp 0.6–0.8, más tokens, `razon` en cadena) para dilemas sociales, invención
  e interpretación. La profundidad la decide la era + saliencia + gravedad.
  *Criterio:* un test distingue los tres niveles por temperatura/tokens y por el
  modelo llamado.
- **B2 — `razon` persistente.** El `razon` de cada decisión se guarda como
  recuerdo (no solo el `dialogo`), para que el individuo "acumule" motivos.
  *Criterio:* tras N decisiones, la memoria del individuo contiene sus razones y
  una consulta las recupera.

### C. Persona / personalidad

- **C1 — Prompt por individuo.** Inyectar al prompt del decididor: rasgos del
  genoma (inteligencia, divergencia → *cómo* decide), habilidades conocidas,
  saliencia, rol emergente, historia personal (hitos propios).
  *Criterio:* dos individuos con distinto genoma y la misma situación reciben
  prompts distintos; un test lo verifica.

### D. Memoria (bucle cerrado)

- **D1 — Contenido, no IDs.** `_recuperar_memoria` debe inyectar el **texto** del
  recuerdo en el contexto, no solo `{id, score}`.
  *Criterio:* el prompt de una decisión incluye el texto de los recuerdos top-k.
- **D2 — Escribir lo producido.** La narración y el diálogo se indexan como
  recuerdos (cierran el bucle). *Criterio:* un hito narrado queda recuperable por
  similitud en ticks posteriores.
- **D3 — Memoria persistente por individuo.** La memoria hoy es un índice global.
  Asociar recuerdos al individuo (y a la tribu) para que la "vida interior" sea
  de alguien. *Criterio:* la consulta de memoria de un individuo no devuelve
  recuerdos de otro sin vínculo.

### E. Innovación / emergencia

- **E1 — Despenalizar `origen=llm`.** El KPI debe contar `origen=llm` como fuera
  del árbol (o redefinir el KPI, ver §I). *Criterio:* `nodos_por_origen` y el KPI
  tratan `llm` como emergencia.
- **E2 — Inventor sin prioridad de catálogo.** El inventor propone *siempre que
  un divergente experimenta* (no solo cuando el catálogo se agota), y el catálogo
  pasa a ser un *caso particular* de validación, no la primera opción.
  *Criterio:* con backend falso guionizado, aparecen nodos `origen=llm` sin que
  el catálogo se haya agotado.
- **E3 — Canal de contenido simbólico.** Mitos, tabúes y rituales con **texto del
  LLM** que persiste en el grafo (hoy el mito es solo un nodo con `contenido`
  fijo). *Criterio:* un mito/rito generado por el LLM queda en el grafo con su
  contenido y es recuperable.

### F. Ramas y eras emergentes

- **F1 — Ramas derivadas del grafo.** Sustituir `RAMAS` fija por **clustering**
  de los nodos (similitud de embeddings de `contenido` + co-transmisión). La
  "rama" es un clúster recalculado al entrar nodos nuevos.
  *Criterio:* quitar la tabla `RAMAS` no rompe el motor; las ramas se derivan y
  dos ejecuciones con la misma semilla dan el mismo clustering.
- **F2 — Validación por restricciones, no por categorías.** `_ramas_plausibles`
  deja de anclar a `RAMAS`; pasa a validar plausibilidad local (los dos padres
  activos, el material existe, no contradice nada). *Criterio:* un nodo nuevo
  propuesto con padres plausibles se acepta aunque no pertenezca a una rama
  predefinida.
- **F3 — Eras emergentes.** La "era" es un **resumen narrativo** de los clústeres
  dominantes, nombrado por el LLM, no una etapa que impone el rumbo.
  *Criterio:* el informe muestra la era actual derivada del grafo; cuando cambia
  la cultura, cambia la era.
- **F4 — KPI redefinido.** Pasar de "% fuera del árbol" a "% fuera del **seed
  inicial**" (todo lo que la tribu sabe y no estaba en el arranque mínimo).
  *Criterio:* el SQL de `objetivo.md §3.2` y `pct_fuera_arbol` miden contra el
  seed, no contra un árbol fijo.

### G. Modelo multi-nivel + router + hardware

- **G1 — Router por profundidad.** Un enrutador que mapea "profundidad de la
  decisión" → modelo (instinto / pequeño / potente), según era + saliencia +
  gravedad del dilema. *Criterio:* el router elige el modelo correcto en cada
  nivel; un test lo verifica con backends falsos.
- **G2 — Modelos separados por rol.** Un modelo pequeño/rápido para decidir
  (temp 0.3) y otro más potente/creativo para narrar/inventar (temp 0.7–0.9).
  Los candidatos concretos y el veredicto están en §9. *Criterio:* narrar y
  decidir usan modelos distintos; `llm selfcheck` lo reporta.
- **G3 — Offload VRAM+RAM.** Evaluar un modelo mayor (7–8B) con capas en CPU
  (offload, como hacen los repos de `llama.cpp` / `num_gpu` de Ollama),
  combinando VRAM y RAM. *Criterio:* el modelo potente corre sin pasarse de la
  VRAM disponible; la latencia se mide.
- **G4 — Límites de seguridad de hardware.** Implementar el "freno térmico" de
  `stack §8` (hoy es solo documento): duty cycle ≤30%, temp <78 °C, util <95 %,
  `keep_alive`, `ollama stop` al cerrar. *Criterio:* el router deja de encolar si
  se supera el presupuesto térmico; un test simula el umbral.

### H. Evaluación de modelos

- **H1 — Métrica de calidad del modelo real.** Extender `llm eval --backend http`
  para publicar acierto, latencia, coherencia del español y **comparación entre
  modelos** (respuestas similares entre el actual y el candidato), como ya hace
  `viabilidad-modelo.md` pero automatizado. *Criterio:* un comando produce un
  número comparable entre commits y entre modelos.
- **H2 — Decisión de cambio con datos.** Antes de instalar un modelo mayor, correr
  H1 contra el 3B y contra el candidato; decidir con números, no con fe.

### I. Medición / KPI

- **I1 — "Cuánto piensa de verdad".** Añadir al `resumen()` métricas que
  distingan instinto de LLM (acciones por origen), no solo peticiones enviadas.
  *Criterio:* el resumen expone el % de acciones decididas por LLM frente a
  instinto por tramo/era.

---

## 5. Arquitectura objetivo

```
nivel 0  instinto (sin modelo)          → reflejos, supervivencia
nivel 1  modelo pequeño (3B, temp 0.3)  → elecciones cotidianas
nivel 2  modelo potente (7-8B, offload) → razonar, narrar, inventar, mito
              ↑
        router por profundidad
        (era + saliencia + gravedad del dilema)
              ↑
     freno térmico / presupuesto de hardware

bucle cerrado de pensamiento:
  pensar → decir/hacer → escribir en memoria/grafo → informar el próximo pensamiento

ramas/eras emergentes:
  grafo → clustering (embeddings + co-transmisión) → ramas derivadas
        → resumen narrativo (LLM) → era emergente
```

La pieza **pivote** es el router (G1): desbloquea B (razonamiento por nivel),
C (persona), G2/G3 (modelos por rol) y G4 (hardware) a la vez, y da a la
memoria (D) un lugar natural donde vivir.

---

## 6. Hoja de ruta (orden y dependencias)

> Revisada: la secuencia original ponía H1/H2 primero, E1 en el paso 6 e I1 en el
> 9. La corrección es: primero arreglar la medida (E1 + I1), luego el bucle y los
> canales, y diferir G/H/nube. Cada paso ya es una feature del backlog (entre
> paréntesis).

1. **E1 + I1 — medir de verdad, primero** (`F3-006` en curso, `MEDIR-LLM` ya
   hecho). Despenalizar `origen=llm` (E1) y medir el uso real por acciones, no
   peticiones (I1). Sin esto no se sabe si el resto de la auditoría arregla algo.
2. **D1 + D2 + D3 — cerrar el bucle de memoria** (`MEM-LOOP`). Contenido, no IDs;
   escribir lo producido; memoria por individuo. Barato y desbloquea casi todo.
3. **C1 — prompt por individuo** (`PERSONA`, depende de `MEM-LOOP`).
4. **A1 + A2 — habla y evolución del lenguaje** (`HABLA`, depende de `MEM-LOOP` y
   `PERSONA`). El canal de §10 que no existe.
5. **E3 — contenido simbólico real** (`CONTENIDO`, depende de `PERSONA`). Mito o
   rito con texto del LLM, no plantilla fija.
6. **E2 — inventor sin prioridad de catálogo** (`INVENTOR`, depende de `PERSONA`).
7. **F1 + F2 + F3 + F4 — ramas/eras emergentes + KPI contra el seed**
   (`RAMAS-EMERGENTES`, depende de `INVENTOR` y `CONTENIDO`). El cambio de rumbo
   grande.
8. **Motor social** (`SOCIAL`, depende de `MEM-LOOP`). Prestigio + necesidad
   social + edad; son los ejes 2 y 4 de `refinamiento-hoja-de-ruta.md`, ausentes
   de esta auditoría y necesarios para que `interaccion` sea real.

**Diferido (no ahora):** G1–G4 (router, modelos por rol, offload, freno térmico),
H1/H2 (catálogo y comparación de modelos), N1–N3 (nube) y O1–O5 (tokens). Son
prematuros: pulen hardware/proveedor antes de arreglar el experimento. Se retoman
cuando lo anterior esté medido.

Dependencias clave: F depende de E (canal de innovación antes de que las
categorías emerjan); el bucle D alimenta a C, A y SOCIAL.

**Camino nube (alternativa, §10):** O1–O5 → N1 → N2 → N3. Diferido; se activa
solo si se quiere el PC aparte.

---

## 7. Decisiones pendientes (cuando se retome)

- **E1 y F4 no son alternativas: son secuenciales.** E1 (añadir `origen=llm` al
  numerador) es el arreglo inmediato de la métrica y va primero; F4 (redefinir a
  "% fuera del seed") es el cambio profundo que llega después, cuando las ramas
  emerjan (§2.18, §4).
- **Temperatura y tokens** — ahora `LLM-CONFIG` en el backlog: confirmar que
  `options.temperature` sobreescribe el default 0.7 del Modelfile (si no,
  quitarlo) y reconciliar `MAX_TOKENS` 64/128 con el presupuesto ≤32 de stack §8.
  (§2.1)
- **Diferido (no se decide hasta que lo anterior esté medido):** salto a
  `qwen3:8b`/`qwen3.5:9b` u otro modelo, con offload o roles separados (§9, §H2);
  y nube sustituta o híbrida (§10). Ambas exigen medir primero, no al revés.
- **Ramas emergentes (F): ¿feature nueva o reescritura de `arbol.py`?** Implica
  tocar `RAMAS`, `ARBOL`, `propuestas.py` y el KPI a la vez. Se decide al abrir
  `RAMAS-EMERGENTES`.

---

## 8. Cómo re-auditar

- Volver aquí tras cada ronda de cambios y releer §2 y §3.
- Marcar como resueltas las soluciones implementadas y citar la feature del
  backlog que las cerró.
- Re-ejecutar H1 para ver si la calidad del modelo subió con el cambio.
- Si se reescribe el árbol (F), re-auditar §2.16, §2.18 y el SQL de
  `objetivo.md §3.2`.

---

## 9. Catálogo de modelos candidatos (nov 2026)

> Datos a 2026-11-19, de fuentes públicas (Ollama library, MTEB/MMLU, guías de
> VRAM por tier). **El paisaje cambia rápido: re-verificar antes de decidir**
> (igual que pide `stack §2`). Los tamaños son Q4_K_M salvo que se indique otro.
> La columna "Español" es cualitativa y debe confirmarse con el plan de §H.

### 9.1 Criterios de selección para "lo nuestro"

1. **Local y Ollama** (HTTP + `format` JSON schema).
2. **RTX 2060 6 GB VRAM** + ~6.9 GB RAM libre (stack §2); offload VRAM→RAM
   aceptable para el nivel potente.
3. **Español de calidad** (narración y diálogo son en español).
4. **Salida estructurada** (el contrato "candidatas → elige → valida" depende
   del JSON schema).
5. **Modo "thinking"** para el nivel profundo (razonar, inventar, mito).
6. **Dos niveles** (visión multi-nivel, §G): pequeño/rápido para decidir y
   potente/creativo para narrar/inventar.

### 9.2 Nivel 1 — pequeño y rápido (decidir, temp 0.3)

| Modelo | Tag Ollama | VRAM (Q4) | Español | Thinking | Veredicto |
|---|---|---|---|---|---|
| **Qwen3.5 4B** | `qwen3.5:4b` | ~3.4 GB | Muy bueno | Sí | **Recomendado** |
| Qwen2.5 3B (actual) | `tribal-llm` | ~3.6 GB (Q8) | Bueno | No | Reemplazar |
| Qwen3 4B | `qwen3:4b` | ~3 GB | Muy bueno | Sí | Bueno, 1 gen atrás |
| Phi-4 mini | `phi4-mini` | ~2.5 GB | Bueno | No | KV cara (~1 GB/8K) |
| Granite 4.1 3B | `granite4.1:3b` | ~2.1 GB | Medio | No | KV barata, tool calling |
| Llama 3.2 3B | `llama3.2:3b` | ~2.0 GB | Medio | No | Solo si algo exige Llama |

### 9.3 Nivel 2 — potente y creativo (narrar, inventar, mito, temp 0.7–0.9)

| Modelo | Tag Ollama | VRAM (Q4) | Español | Thinking | Veredicto |
|---|---|---|---|---|---|
| **Qwen3 8B** | `qwen3:8b` | ~4.6 GB | Muy bueno | Sí | **Recomendado (cabe, o offload mínimo)** |
| Qwen3.5 9B | `qwen3.5:9b` | ~6.6 GB | Muy bueno | Sí | Offload obligado (excede 6 GB) |
| Gemma 3 4B | `gemma3:4b` | ~3.3 GB | Bueno | No | Creativo, 1 gen atrás |
| Gemma 4 E2B QAT | `gemma4:e2b-it-qat` | ~4.3 GB | Bueno | No | Lento; solo tag QAT |
| DeepSeek-R1 8B | `deepseek-r1:8b` | ~5.2 GB | Medio | Sí (CoT) | Razona, pero exige contexto (mal en 6 GB) |
| Ornith 9B | `ornith:9b` | ~5.6 GB | ? | Sí | Agentic; offload y lento |

### 9.4 Embeddings (en CPU)

| Modelo | Tag | Descarga | Dims | MTEB multilingüe | Veredicto |
|---|---|---|---|---|---|
| Qwen3-Embedding 0.6B (actual) | `qwen3-embedding:0.6b` | 639 MB | 1024 | 64.33 | **Mantener** |
| Qwen3-Embedding 4B | `qwen3-embedding:4b` | 2.5 GB | 2560 | 69.45 | Subir si la memoria crece |

### 9.5 Veredicto — el que mejor se adapta

**`qwen3.5:4b` (nivel 1) es el modelo que mejor se adapta a lo nuestro**, por:

1. **Continuidad**: misma familia Qwen que el actual `qwen2.5:3b` → el JSON
   schema y el español ya están probados en el proyecto (`viabilidad-modelo.md`).
2. **Piensa de verdad**: modo "thinking" nativo (la pieza que falta para el
   razonamiento por profundidad, §B).
3. **Cabe holgado**: ~3.4 GB deja ~2 GB de VRAM para KV cache y contexto, con
   margen para el freno térmico (§G4).
4. **Es el consenso 2026 para 6 GB**: MMLU-Pro 79.1, tool calling, visión y
   262K de contexto nativo.

Para el **nivel 2** (narrar, inventar, mito), el salto natural es **`qwen3:8b`
(Q4, ~4.6 GB)**: cabe en 6 GB con contexto corto o hace offload mínimo a RAM, y
es un salto de calidad real (Qwen3-4B ya rivaliza con Qwen2.5-72B en parte de
los benchmarks). Si se quiere más, `qwen3.5:9b` exige offload y es la opción de
compromiso.

> **No se instala nada sin medir.** Antes de sustituir `tribal-llm`, correr el
> plan de §H contra el 3B actual y contra `qwen3.5:4b`/`qwen3:8b` y decidir con
> números (acierto, latencia, coherencia del español), no con fe.

### 9.6 Notas técnicas que condicionan la elección

- **Salida estructurada + thinking**: históricamente incompatibles en Ollama
  (issue #10538); con Qwen3 ya funciona, pero es un punto de fricción conocido.
  Para el nivel 1 (decidir, temp 0.3) el thinking debe estar **apagado**; solo el
  nivel 2 lo necesita.
- **Cuenta de KV cache**: no todo es el tamaño del modelo. Phi-4 mini cuesta
  ~1 GB de KV por 8K de contexto; Granite es la más barata (~80 KiB/token). Con
  6 GB, el contexto y el KV importan tanto como los pesos.
- **Modelos de razonamiento (DeepSeek-R1)**: emiten trazas largas de thinking y
  necesitan el máximo de contexto libre, justo lo que menos tiene una 6 GB. Se
  descartan para este hardware.
- **Cuantización**: el actual usa `q8_0` (3B). Para 4B/8B en 6 GB la práctica es
  `q4_K_M`. Revisar si la pérdida de calidad en narración justifica subir a
  `q8_0` y pagar offload.
- **Co-residencia de modelos**: los dos LLMs no caben juntos en VRAM
  (3.4 + 4.6 ≈ 8 GB > 6 GB). Estrategia **A** —un solo modelo (`qwen3.5:4b`)
  con modos por rol (`thinking`/sampling)—, o **B** —4B residente + 8B bajo
  demanda con `keep_alive` corto (paga 2–4 s de recarga solo en narración e
  invención, que son raras). El embedding va siempre en CPU y no compite.

### 9.7 Técnicas y modelos especializados (prior art)

> Otros ya han resuelto estos problemas. El proyecto no está solo: hay dos
> referencias directas y una familia de modelos y técnicas especializadas.

#### 9.7.1 La arquitectura que resuelve exactamente esto — Generative Agents (Stanford, 2023)

"Generative Agents: Interactive Simulacra of Human Behavior" (Park et al.,
arxiv 2304.03442) es el antecedente canónico de un "sistema vivo que piensa,
recuerda y planifica". Su arquitectura de tres piezas es el blueprint del §B/§D:

| Pieza | Qué hace | En Tribal hoy |
|---|---|---|
| **Memory stream** | Registro de observaciones con timestamp de creación y último acceso | `recuerdos` (índice) — existe, pero sin contenido ni recencia |
| **Reflection** | Sintetiza memorias en abstracciones de nivel superior (árbol de reflexiones) | **No existe** — es la pieza que falta para "profundizar" |
| **Planning** | Plan amplio descompuesto recursivamente, revisable ante novedades | `intencion_llm` (1 paso) — no hay plan |
| **Retrieval** | recency × importance × relevance (decay 0.995) | `IndiceRecuerdos.buscar` (solo coseno, sin recencia ni importancia) |

Puntos clave (y un par de coincidencias con lo que ya haces):

- El **decay 0.995** de su retrieval es el mismo patrón que
  `saliencia.DECAIMIENTO = 0.999` — tu instinto ya iba por ahí.
- La **reflection** se dispara cuando la suma de importancias de los eventos
  recientes supera un umbral (150 en el paper): un "cuándo pensar" mucho más
  rico que tu `_hay_dilema` (dos condiciones AND).
- La **ablación** del paper demostró que quitar memoria, reflexión o
  planificación degrada la credibilidad: es evidencia de que el bucle cerrado
  (§D) no es opcional sino estructural.

#### 9.7.2 El antecedente directo de "civilización emergente" — Project Sid (Altera, 2024)

"Project Sid: Many-agent simulations toward AI civilization" (arxiv 2411.00114)
simula 10–1000+ agentes (en Minecraft) que desarrollan **roles especializados,
adaptan reglas colectivas y transmiten cultura**. Es la demostración de que la
visión de "las ramas y las eras emergen" (§F) es alcanzable y ya se ha hecho a
escala. Vale como referencia para no reinventar el mecanismo.

#### 9.7.3 Modelos especializados para estas tareas

El contrato "candidatas → elige → valida" es, en el fondo, **function/tool
calling** (elegir una de N acciones válidas). Hay modelos afinados exactamente
para eso, y modelos de rol/narración:

| Modelo | Base / tag | Especialidad | Relevancia para Tribal |
|---|---|---|---|
| `nemotron-mini` | 4B | Roleplay + RAG QA + function calling | Interesante para diálogo/NPC |
| `command-r7b` | 7B | Tool use, RAG | Candidato para decidir |
| `functiongemma` | Gemma 3 270M | Function calling | Diminuto; solo como curiosidad |
| `lfm2.5` | 8B-A1B | Tool calling en hardware de consumo | Candidato edge |
| `firefunction-v2` | Llama 3 70B | Function calling | Demasiado grande para 6 GB |
| Hermes 3 (Nous) | — | Ficción, roleplay, worldbuilding, diálogo | Para cronista/inventor (baja negativa) |
| Dolphin | — | Low-refusal | Para mito/narración sin auto-censura |

Benchmark de referencia: **BFCL** (Berkeley Function-Calling Leaderboard), que
mide "elige la acción correcta" — justo lo que evalúa el contrato del proyecto.

#### 9.7.4 Qué significa para la hoja de soluciones (§4)

1. **La reflection es lo que convierte "elige" en "piensa".** Añadirla a §D:
   cuando la importancia acumulada de los hitos supera un umbral, el individuo
   genera una reflexión que se guarda como recuerdo de nivel superior. Es el
   mecanismo de "profundizar" del que habla el objetivo.
2. **La retrieval debe ser recency × importance × relevance**, no solo coseno.
   Hoy `IndiceRecuerdos` es puro coseno; añadir recencia e importancia es barato
   y está validado por el paper.
3. **Hay modelos especializados** (function calling, roleplay, low-refusal) que
   pueden sustituir o complementar a Qwen por rol, en vez de un generalista para
   todo. Revisar §9.5 a la luz de §9.7.3 antes de fijar el veredicto.

### 9.8 Referencias (verificadas 2026-11-19)

- Ollama library (tags y tamaños de descarga).
- Guías de VRAM por tier 2026 (6 GB: `qwen3.5:4b` como ganador; Qwen3 8B ~4.6 GB Q4).
- MTEB multilingüe (Qwen3-Embedding 0.6B/4B/8B).
- MMLU-Pro de Qwen3.5-4B.
- Informe técnico Qwen3 (0.6B–32B densos; 30B-A3B y 235B-A22B MoE).
- Creative writing 2026 (Gemma 4 31B / Qwen3.8-27B son los mejores, fuera de
  rango para 6 GB).

---

## 10. Opción nube — LLM de pago (complementario, futuro)

> Estado: opción a futuro, para ejecutar Tribal en una máquina **sin GPU ni
> Ollama**. Complementa al local (§9), no lo sustituye por defecto. No se
> implementa ahora; se documenta para decidirlo y valorarlo cuando toque.

### 10.1 Objetivo

- Ejecutar Tribal en un PC aparte que **no puede correr un LLM local** (sin GPU,
  sin Ollama, o con RAM insuficiente).
- Opcionalmente, acceder a modelos **mejores** que el 3B local (los modelos de
  pago superan a `qwen3.5:4b` en español, razonamiento y narración).
- Mantener **intacto** todo lo que no sea "quién responde al prompt": reglas,
  grafo, saliencia, instinto, validación y el determinismo de la física.

### 10.2 La buena noticia: ya está casi preparado

La capa LLM ya separa lo que cambia de lo que no:

| Pieza | ¿Cambia con nube? |
|---|---|
| `esquema.py` (prompts + JSON schema) | **No** — reutilizable tal cual |
| `decision.py` (validar/corregir) | **No** |
| `candidatas.py` (filtro 2–4) | **No** |
| `cola.py` (async, ventana de validez) | **No** (quizá subir el timeout) |
| `http.py` (transporte) | **Sí** — protocolo y sobre distintos |
| `cliente.py` (construye cuerpo de Ollama) | **Sí** — cuerpo y sobre distintos |

`stack §12` ya lo anticipó: "enrutado local + nube con fallback al local, diferido".

### 10.3 Qué valorar cuando se haga (checklist)

1. **Protocolo.** El estándar de facto es OpenAI-compatible
   (`/v1/chat/completions`). Casi todos (OpenRouter, Groq, Together, Mistral,
   DeepSeek…) lo hablan.
2. **Salida estructurada.** El equivalente al `format` de Ollama es
   `response_format: {type: "json_schema", ...}` (o `json_object`). Verificar que
   el proveedor lo soporta **y** que el modelo respeta el schema.
3. **Latencia de red.** La local mide ~1 s; la nube 0.5–2 s+ y añade red. Subir
   el timeout de 3 s a ~15–30 s y revisar la ventana de validez (180 ticks): una
   decisión tardía ya se descarta y manda el instinto (eso ya funciona).
4. **Coste.** Muchas llamadas pequeñas (prompt corto + respuesta ~64 tokens). El
   salience gating y `max_en_vuelo=4` ya racionan, pero hay que **medir**
   tokens/petición y coste por partida antes de fiarse.
5. **Rate limits.** El presupuesto en vuelo ayuda; añadir backoff si el proveedor
   devuelve 429.
6. **Privacidad.** El estado de la tribu (números + textos) va a un tercero. No es
   sensible, pero hay que decidir qué se manda. `agents/redaction.py` ya tapa
   credenciales; aplicarlo a lo que salga.
7. **Autenticación.** La API key va en `.env` (nunca en git). Reusar el patrón de
   `.env.example` y el redactor.
8. **Determinismo.** La nube es no determinista (temp > 0). Los tests siguen con
   `--llm stub`/`backend_falso`; la nube es solo para partidas reales.
9. **Disponibilidad del modelo.** Español, JSON schema y razonamiento cambian por
   proveedor; verificar con §H antes de elegir.
10. **Flag de proyecto.** `project.yml` tiene `use_api: false`; habría que pasarlo
    a `true` y que los agentes lo lean (ya lo consultan).

### 10.4 Diseño propuesto (adapter de proveedor)

- Introducir un **adapter** que normalice a OpenAI-compatible, compartiendo
  `esquema/decision/cola`:
  - `OllamaProveedor` (actual, default local).
  - `NubeProveedor` (OpenAI-compatible, con `base_url` + API key).
  - `OpenCodeProveedor` (HTTP API de OpenCode, modelos `*-free`; ver §10.9).
- CLI: `run --llm {off, stub, http, nube, opencode}` o `--proveedor
  {ollama, openai, opencode}`.
- La nube puede ser **sustituta** (solo nube) o **híbrida** (router §G: local
  para decidir, nube para narrar/inventar). Ambas salen del mismo adapter.

### 10.5 Candidatos de proveedor (orden de preferencia sugerido)

| Proveedor | OpenAI-compatible | JSON schema | Español | Nota |
|---|---|---|---|---|
| **OpenRouter** | Sí | Sí | Según modelo | Un punto a muchos modelos; pago por uso |
| Groq | Sí | Sí | Bueno | Muy rápido, tier gratis |
| OpenAI | Sí | Sí | Bueno | Referencia de calidad |
| Anthropic | Parcial | Sí | Bueno | Protocolo propio |
| Google Gemini | Parcial | Sí | Bueno | Protocolo propio |
| Mistral / DeepSeek | Sí | Sí | Bueno | Más baratos |

> Default sugerido: **OpenRouter** (agnóstico, OpenAI-compatible, un solo
> contrato para probar varios modelos, pago por uso). La elección final se decide
> con §H (medir calidad, latencia y coste) cuando se active la opción.

### 10.6 Cómo se convertiría en features (ids N*)

- **N1 — Adapter de proveedor.** Un `Proveedor` con backends Ollama,
  OpenAI-compatible y OpenCode, compartiendo `esquema/decision/cola`. *Criterio:*
  la misma partida con `--llm stub` es idéntica con cualquiera de los backends;
  cada sobre (Ollama / OpenAI / OpenCode) se desenvuelve a la misma `Decision`.
- **N2 — Selección de proveedor y modelo.** `--proveedor` + `--modelo` + API key
  desde `.env`. *Criterio:* `llm selfcheck` reporta el proveedor, el modelo y si
  la clave está configurada (sin imprimirla).
- **N3 — Coste y latencia visibles.** Contar tokens/petición y latencia, y
  exponerlos en `resumen()` como ya se hace con la cola. *Criterio:* el resumen
  incluye coste estimado y latencia media por proveedor.

### 10.7 Decisión abierta

- ¿Sustituir (solo nube) o híbrido (router local+nube, §G)? Ambas salen del mismo
  adapter; la híbrida es más trabajo y es la que aprovecha el router de §G.

### 10.8 Fase de optimización de tokens (uso y prompts)

> Obligatoria antes de (o junto con) activar la nube de pago: cada token se paga.
> Beneficia también al local: menos tokens = más rápido y menos presión de VRAM.

**Primero medir (baseline).** Antes de optimizar, fijar tokens-in, tokens-out y
coste por partida (esto es N3). Sin baseline no se puede saber si una palanca
sirvió.

**Palancas (ids O*):**

- **O1 — Prompt comprimido y cache-friendly.** System prompt mínimo y estable;
  few-shot reducido a lo imprescindible (1 ejemplo o ninguno si el modelo es
  bueno). Un prefijo (system + few-shot) **byte-idéntico entre llamadas** habilita
  el *prefix caching* del proveedor (OpenAI/Anthropic) y abarata los tokens de
  entrada repetidos. *Criterio:* el prefijo es idéntico entre llamadas y su tamaño
  en tokens baja mediblemente.
- **O2 — Estado compacto.** `estado_para` serializa solo lo relevante para el
  dilema, en notación compacta (no un JSON verboso con claves largas). *Criterio:*
  el prompt de decisión baja de tamaño sin bajar el acierto (§H).
- **O3 — Tope de respuesta y de thinking.** `max_tokens` bajo (32 para decidir),
  `razon`/`dialogo` con tope de longitud (el motor ya valida textos; añadir
  `maxLength`), y **thinking apagado** en nivel 1 (solo nivel 2, con tope de
  tokens de thinking). Es la palanca más grande: los tokens de *thinking* de un
  modelo razonador se pagan y no se usan. *Criterio:* la respuesta de decisión
  nunca excede N tokens; el thinking solo aparece en narración/invención y está
  acotado.
- **O4 — Recuerdos acotados.** La memoria inyecta top-1 (o top-3 truncado a X
  palabras), no texto completo. *Criterio:* el contexto de memoria cabe en un
  presupuesto fijo de tokens.
- **O5 — Menos llamadas (coalescencia).** Reusar la decisión anterior si el estado
  no cambió; no llamar para lo que el instinto ya resuelve; narrar solo hitos de
  peso. *Criterio:* el nº de peticiones por partida baja sin cambiar los resultados
  clave.

**Validación:** re-medir con §H (acierto) y N3 (coste) para comprobar que el coste
baja sin bajar la calidad. Un test puede comparar "coste por partida antes y
después" con un backend falso que cuente tokens.

> **Nota de ejecución:** al hacer esta fase (y la de evaluación de modelos, §H),
> buscar primero **skills reutilizables** —optimización de prompts, reducción de
> coste de tokens, prompt-engineering— en lugar de partir de cero (`find-skills`
> o el catálogo de skills del arnés). Investigarlo **en el momento de ejecutar**,
> no ahora.

### 10.9 Vía OpenCode API — modelos free del asistente (tercera opción)

OpenCode expone un HTTP API desde su servicio de fondo (documentado en
`opencode.ai/docs/api`) que permite generación de texto con los modelos
configurados — incluidos los `*-free`. Es una tercera opción para la simulación,
además de Ollama local y API cloud de pago.

**Endpoints relevantes:**

- `POST /api/experimental/generate/text` — generación de una sola vez.
- `POST /api/session/{id}/prompt` — mensaje dentro de una sesión.
- `POST /api/experimental/generate/decisions` — decisiones con preguntas de
  opción (parecido al contrato "candidatas → elige").

**Matices (no es "clave y listo"):**

1. **Experimental**: los endpoints están marcados `experimental` y pueden
   cambiar entre versiones de OpenCode.
2. **No es OpenAI-compatible**: formato propio; necesita el adapter N1.
3. **Lo sirve el servicio de fondo de OpenCode**, con su autenticación (la del
   TUI). Requiere OpenCode corriendo y conectado; no es un endpoint público con
   clave.
4. **Pensado para integraciones**, no para inferencia a 60 fps de alto volumen.

**Qué verificar en la práctica (no asumir):**

- El request/response exacto de `/api/experimental/generate/text`.
- Que acepta los modelos `*-free` (p. ej. `opencode/deepseek-v4.1-flash-free`).
- Latencia y límites de uso (`/api/experimental/usage/limits`).
- Si soporta salida estructurada (equivalente al `format`/`response_format`).

**Cómo encaja:** es un tercer backend del adapter N1 (`OpenCodeProveedor`). Para
el PC aparte sin GPU sería la opción **gratis** (si el servicio de OpenCode corre
ahí), frente a la nube de pago.

**Distinción clave (no confundir):** los modelos free son el motor interno del
asistente. Acceder a ellos desde la simulación solo es posible **a través del
HTTP API de OpenCode**, no como una API cloud normal.

---

## 11. Apéndice: referencias de código (índice)

| Tema | Archivo | Símbolo |
|---|---|---|
| Modelo / endpoint / tokens | `tribal/llm/cliente.py` | `MODELO_POR_DEFECTO`, `ENDPOINT_POR_DEFECTO`, `TIMEOUT_POR_DEFECTO`, `TEMPERATURA`, `MAX_TOKENS` |
| Modelfile | `tribal.Modelfile` | `FROM`, `PARAMETER` |
| Transporte | `tribal/llm/http.py` | `transporte_http`, `Transporte` |
| Prompts / schemas | `tribal/llm/esquema.py` | `SISTEMA`, `SISTEMA_NARRACION`, `SISTEMA_PROPUESTA`, `EJEMPLOS`, `construir_prompt*` |
| Candidatas | `tribal/llm/candidatas.py` | `estado_para`, `candidatas`, `MAX_CANDIDATAS` |
| Validación | `tribal/llm/decision.py` | `decidir_con_candidatas`, `_violacion`, `_corregir` |
| Cola | `tribal/llm/cola.py` | `ColaLLM`, `VENTANA_POR_DEFECTO`, `MAX_EN_VUELO_POR_DEFECTO` |
| Embeddings | `tribal/llm/embeddings.py` | `EmbedderHashing`, `EmbedderOllama`, `IndiceRecuerdos` |
| Eval | `tribal/llm/eval.py` | `escenarios`, `evaluar`, `backend_competente` |
| Gatillo de pensamiento | `tribal/sim.py` | `_encolar_dilema`, `_hay_dilema`, `_recuperar_memoria`, `_drenar` |
| Saliencia | `tribal/agents/saliencia.py` | `subir`, `decaer`, `SUBIDA`, `DECAIMIENTO` |
| Instinto | `tribal/agents/instinto.py` | `elegir` |
| Diario | `tribal/culture/diario.py` | `Diario`, `registrar`, `narrar` |
| Inventor | `tribal/culture/propuestas.py` | `parsear`, `validar`, `_ramas_plausibles` |
| Árbol / ramas | `tribal/culture/arbol.py` | `RAMAS`, `ARBOL`, `ORIGENES`, `NIVEL_ORIGEN` |
| Combinaciones | `tribal/culture/combinaciones.py` | `COMBINACIONES` |
| Tradiciones | `tribal/culture/tradiciones.py` | `evaluar`, `_nueva_tradicion`, `RAMAS_TECNICAS` |
| KPI | `tribal/culture/grafo.py` | `pct_fuera_arbol`, `nodos_por_origen` |
| Config | `tribal/config.py` | `max_pensando`, `SimConfig` |
| Documento de viabilidad | `vault/01_PROYECTO/viabilidad-modelo.md` | — |
| Stack | `vault/01_PROYECTO/stack-tecnologico.md` | §2, §8 |
| Concepto | `vault/01_PROYECTO/concepto.md` | §7, §8b, §10, §10b |
