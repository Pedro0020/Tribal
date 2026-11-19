# Auditoría del LLM — estado y hoja de soluciones

> **Estado:** CERRADO el 2026-11-19. Documento de análisis, no de implementación.
> **Propósito:** dejar anotado el diagnóstico del uso del LLM y una hoja de
> soluciones completa, para que en el futuro se pueda volver aquí, auditar,
> decidir y añadir tareas al backlog **a mano**. No se toca el backlog desde
> aquí.
> **Método:** análisis estático del código y de los documentos de diseño. No es
> una prueba empírica contra el modelo real (eso queda pendiente, ver §H).
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

**El LLM está infrautilizado: se usa en una fracción pequeña (~5%) de la vida de
la simulación, y como un selector de candidatas, no como el "motor central" que
promete `concepto.md §2`.**

El modelo entra en exactamente **tres sitios** de `tribal/sim.py`, todos
estrechísimos:

| Canal | Dónde | Gatillo real | Magnitud por partida |
|---|---|---|---|
| **Decidir** | `_encolar_dilema()` | `_hay_dilema`: sed crítica **Y** energía baja a la vez, o salud crítica | Muy raro: en calma casi nadie lo cumple |
| **Narrar** | `_hito()` | Solo hitos (fuego, palabra, rito, caza, muerte de anciano) **y** solo si hay narrador con saliencia > 0 | ~6–15 frases |
| **Proponer** | `_solicitar_propuesta_llm()` | Solo en **crisis** + individuo **divergente** + **cada 200 ticks** | ~15, y la mayoría delega al catálogo |

Todo lo demás —beber, comer, huir, moverse, descansar, deambular, enseñar,
cuidar, practicar— lo cubre `instinto.elegir`, una política **determinista sin
LLM** (≈99% de los tick-individuo: 12 individuos × 3000 ticks ≈ 36.000 acciones
por partida, de las que el LLM decide decenas).

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
- Política determinista que cubre el 95%: sed→beber, hambre→comer, lobo→huir,
  ocio→enseñar/cuidar/practicar/deambular.
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

1. **La conclusión de viabilidad se volvió techo.** `viabilidad-modelo.md` dijo
   "el 3B no genera acciones desde cero, sí elige entre candidatas" y se optimizó
   todo para esa debilidad, abandonando la fortaleza (lenguaje, significado,
   rol, historia).
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
  (3B, temp 0.3) y otro más creativo para narrar/inventar (p. ej.
  `gemma-3-4b-it`, temp 0.7–0.9). *Criterio:* narrar y decidir usan modelos
  distintos; `llm selfcheck` lo reporta.
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

1. **H1/H2** — medir la calidad real del 3B (y de un candidato) para decidir con
   datos si hace falta el salto de modelo.
2. **D1 + D2** — cerrar el bucle de memoria (contenido + escritura). Barato y
   desbloquea casi todo lo demás.
3. **C1** — prompt por individuo (persona).
4. **A1 + A2** — habla y evolución del lenguaje.
5. **G1 + G2** — router y modelos por rol.
6. **E1 + E2 + E3** — despenalizar `origen=llm` y dar canal real a la innovación
   y al contenido simbólico.
7. **F1 + F2 + F3 + F4** — ramas/eras emergentes y KPI redefinido (el cambio de
   rumbo grande).
8. **G3 + G4** — offload y límites de hardware (cuando haya decisión de modelo).
9. **I1** — medición del uso real.

Dependencias clave: F depende de E (hay que tener canal de innovación antes de
que las categorías emerjan); G3 depende de H2 (la decisión de modelo).

---

## 7. Decisiones pendientes (cuando se retome)

- ¿Se confirma que `options.temperature` sobreescribe el default del alias, o hay
  que quitar `temperature 0.7` del Modelfile? (§2.1)
- ¿Se corrige `MAX_TOKENS` a 32 (stack §8) o se actualiza stack? (§2.1)
- ¿El KPI se redefine a "% fuera del seed" (F4) o se mantiene "% fuera del
  árbol" y solo se añade `origen=llm` (E1)? (§2.18, §4)
- ¿Salto a 7–8B con offload, o se queda el 3B y se separan roles? (§G3/H2)
- ¿Las ramas emergentes (F) son una feature nueva o una reescritura de
  `arbol.py`? Implica tocar `RAMAS`, `ARBOL`, `propuestas.py` y el KPI a la vez.

---

## 8. Cómo re-auditar

- Volver aquí tras cada ronda de cambios y releer §2 y §3.
- Marcar como resueltas las soluciones implementadas y citar la feature del
  backlog que las cerró.
- Re-ejecutar H1 para ver si la calidad del modelo subió con el cambio.
- Si se reescribe el árbol (F), re-auditar §2.16, §2.18 y el SQL de
  `objetivo.md §3.2`.

---

## 9. Apéndice: referencias de código (índice)

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
