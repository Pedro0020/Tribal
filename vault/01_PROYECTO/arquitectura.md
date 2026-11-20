# 🏗️ Arquitectura — Tribal

> Documento de diseño técnico. Destila `concepto.md` (§4, §10/10b, §11, §8b) y
> `stack-tecnologico.md` (§2, §3, §5, §8) sin introducir decisiones nuevas: si
> algo aquí contradice al concepto, gana el concepto.
> Estado: **Fase 1 cerrada; Fase 2 (LLM) pendiente**. Última revisión: 2026-11-19.

---

## 1. Qué tiene que sostener esta arquitectura

El producto se juzga con una consulta a la base de datos de una partida
(`objetivo.md` §3.2): el **porcentaje de nodos de cultura cuyo `origen` no es
`arbol`** debe llegar al 50 %. Todo lo que sigue existe para que ese número
pueda subir sin que la ventana se congele: un motor rápido y determinista que
sostiene 60 fps, unos individuos que actúan solos, un LLM que decide **poco y
en segundo plano**, y una memoria colectiva que sobrevive a quien la creó.

De ahí salen las tres invariantes que ninguna otra decisión puede romper:

1. **El LLM nunca se llama desde el hilo de render.** Se encola; el resultado
   se aplica cuando llega, y si no llega, no se aplica.
2. **El motor de reglas es determinista dado (semilla, configuración, orden de
   ticks).** Sin esto, una partida interesante no se puede reproducir ni
   comparar, y el KPI deja de ser una medida.
3. **La cultura es un grafo persistido, no estado en RAM.** Si la cultura vive
   solo en memoria, no se puede demostrar la emergencia: no hay consulta.

---

## 2. Las piezas

| Pieza | Responsabilidad | Dónde vive | Fase |
|---|---|---|---|
| **Motor de reglas** | Mundo, reloj, estaciones, clima, recursos, resolución de acciones, necesidades, nacimiento/muerte | `tribal/core/` | 0 |
| **Individuos** | Genoma, habilidades, necesidades, personalidad (divergencia/conformidad), saliencia, intención actual | `tribal/agents/` | 0–1 |
| **Capa LLM** | Cola asíncrona, cliente HTTP de Ollama, JSON schema (`format`), selección por saliencia, aplicación diferida | `tribal/llm/` | 2 |
| **Memoria colectiva** | Grafo de nodos/aristas, `origen` de cada nodo, transmisión (enseñar/imitar), decaimiento | `tribal/culture/` | 1–3 |
| **Persistencia** | Esquema SQLite de stack §5, repositorios, export a Markdown con `[[wikilinks]]` | `tribal/store/` | 0 (opcional) / 3 |
| **Observación** | Render Pygame top-down pixel art y panel de telemetría (muestreo por intervalo) | `tribal/ui/` | 0 / 3 |

### 2.1 Motor de reglas — `tribal/core/`

`mundo.py` guarda el estado plano del mundo (tick, estación, clima, rejilla de
recursos). `recursos.py` regenera y agota recursos. `acciones.py` implementa el
vocabulario finito de concepto §7 como funciones puras
`(individuo, mundo, azar) -> resultado`: cazar, recolectar, beber, descansar,
fabricar, encender fuego, conversar, enseñar, explorar, ritual… El motor
**valida y aplica**, no decide: la decisión viene del instinto o del LLM.

Determinismo: un único generador `random.Random(seed)` propiedad del mundo, y
un orden de iteración estable (lista de individuos ordenada por `id`). Nada de
`set` en bucles que muten estado.

### 2.2 Individuos — `tribal/agents/`

`individuo.py` (datos + estado), `necesidades.py` (urgencias y umbrales),
`instinto.py` (política por defecto, sin LLM, concepto §10b nivel 1),
`saliencia.py` (acumulación y decaimiento del peso narrativo).

**Implementado en F2-004.** `saliencia.py` es la única fuente del peso
narrativo: `SUBIDA` fija cuánto vale cada hito (primer nodo de una rama,
combinación, tradición, enseñanza, rescate y crisis sobrevivida), `DECAIMIENTO`
= 0.999 por tick y `SALIENCIA_MAX` = 10. `Individuo.saliencia` nace a 0, no se
hereda y no se calcula desde el genoma: sube cuando el motor llama
`saliencia.subir(individuo, motivo)` en el punto del hito y baja un tick de
olvido por paso. Es, por tanto, independiente de `divergencia` (§9b): un
conformista y un divergente con la misma historia acaban con el mismo peso.

Un individuo tiene siempre una **intención** (`Instinto | DecisionLLM`). La
intención LLM, si llega, tiene prioridad durante N ticks; si caduca, se vuelve
al instinto. Esto es lo que impide que un agente se congele esperando a un
modelo que puede tardar un segundo.

### 2.3 Capa LLM — `tribal/llm/`

- `cola.py`: dos `queue.Queue` (peticiones y resultados) + contador de en vuelo.
- `cliente.py`: el hilo de cliente. Consume peticiones, hace
  `POST http://127.0.0.1:11434/api/chat` contra Ollama con `model: tribal-llm`
  (el alias del `tribal.Modelfile`, que está en la raíz del repo y arranca con
  `num_ctx 8192`), el campo `format` (JSON schema) y timeout corto, y deposita
  el resultado.
- `esquema.py`: el JSON schema de la respuesta. Fija el esqueleto (`accion`
  dentro del vocabulario de §7, `objetivo`, `razon`, `dialogo`) y deja libres
  los campos de texto, según stack §8 («constriñe coherencia, no dirección»).
- `candidatas.py`: el filtro duro. Devuelve **2–4 acciones** viables para el
  estado (`beber` solo con agua al alcance, `comer` solo con comida, `huir` solo
  con depredador encima) y `estado_para()` con los hechos que viajan al prompt y
  que usa la validación. Si el filtro deja una sola, añade `moverse` a un tile
  pisable y, si no lo hay, esa única candidata: el borde está documentado y
  `_hay_dilema` no encola decisión cuando no hay dos acciones viables.
- `decision.py`: construye el cuerpo de `/api/chat` con el `enum` restringido a
  las candidatas, el prompt few-shot de `esquema.py` y temperatura 0.3; después
  **valida y solo corrige lo inválido** (fuera de candidatas o restricción
  dura), sustituyéndolo por la mejor candidata por reglas. Un transporte caído
  no es una elección: se devuelve sin decisión y manda el instinto.
- `eval.py`: `llm eval` corre 20 escenarios simples con una acción claramente
  correcta. En CI usa un backend simulado competente (prueba el contrato y el
  filtrado, no la calidad del modelo); `--backend http` mide el modelo real y
  no revienta si el servicio no está.
- `embeddings.py`: `Embedder` (dim, `usa_gpu`, `emb`) con dos backends.
  `EmbedderHashing` es el determinista: bag-of-words con blake2b por token (no
  `hash()`, que cambia entre procesos), 256 dimensiones y L2 normalizado.
  `EmbedderOllama` es el real opcional (`POST /api/embed`, urllib, transporte
  inyectable); se declara en CPU (`usa_gpu=False`) porque la VRAM es del LLM y
  un fallo de servicio devuelve vector nulo sin lanzar. `IndiceRecuerdos`
  guarda vectores y `buscar(consulta, k)` devuelve top-k por coseno con orden
  estable (score y luego id); una guarda impide llamarlo desde `ui.render` o
  desde el hilo `tribal-llm`. `Simulacion` indexa los hitos de cultura —nodos
  del árbol, combinaciones y tradiciones de `origen=interaccion`— y añade los
  relevantes al contexto de cada petición; `resumen()` publica
  `memoria: {recuerdos, recuperaciones}`.
- `seleccion.py`: quién piensa este tick. Solo se encola si hay **dilema real**
  (conflicto de necesidades, evento propio relevante, oportunidad de innovar) y
  hay hueco en la cola; a igualdad de dilema, gana más saliencia.
- `aplicar.py`: convierte el JSON validado en una `DecisionLLM` aplicable y
  descarta lo que el motor considere implausible.

**Selección por saliencia implementada en F2-004.** No hay módulo aparte: la
selección vive en `Simulacion._encolar_dilema`. Cada tick reúne a los
individuos con dilema, los ordena por `(-saliencia, id)` y encola hasta
`SimConfig.max_pensando` (4 por defecto) y hasta `max_en_vuelo` de la cola; el
resto sigue por instinto y se reevalúa al tick siguiente. `resumen()` publica
`saliencia: {top, pensamientos, max_pensando, max_en_vuelo}` —el top 3 de los
vivos, las peticiones aceptadas por individuo y los máximos observados del
presupuesto—; sin capa LLM el bloque sale igual con `pensamientos` vacío.

**Contrato implementado en F2-001.** El cliente no pregunta «qué hacer»: recibe
un estado serializable y **2–4 acciones candidatas**, y el modelo elige una y la
justifica (`accion`, `objetivo`, `razon`, `dialogo`). `format` lleva
`esquema.ESQUEMA_RESPUESTA` con el `enum` del vocabulario de `core.acciones`,
temperatura 0.3 y `num_predict` acotado. `ClienteLLM.decidir()` devuelve
`ok | degradado | error` y **nunca lanza**: un timeout (3 s), una conexión
rechazada o un JSON inválido se convierten en `degradado`/`error`, de modo que
el bucle sigue por instinto. `disponible()` consulta `/api/tags` para
`llm selfcheck` y publica `modelo_presente` (`true` si `tribal-llm` está
instalado, `false` si el servicio responde sin él, `null` si no responde); un
servicio caído no rompe el comando. La suite inyecta `backend_falso` y bloquea
`urllib.request.urlopen`, así que `pytest` no abre red.

**Contrato completo en F2-CONTRATO.** `candidatas.py` filtra las opciones
viables y `decision.py` restringe el `enum` a ellas, elige con few-shot y
temperatura 0.3, y valida la respuesta: solo corrige si la acción no está entre
las candidatas o viola una restricción dura, y el `resumen()` cuenta esas
correcciones en `llm.corregidas`. `llm eval` mide el acierto del contrato en 20
escenarios simples con un backend simulado competente (CI) y deja
`--backend http` para medir el modelo real.

**Narración implementada en F2-005.** El cronista de concepto §10 no elige
nada: `ClienteLLM.narrar(hito, contexto)` manda un prompt propio
(`esquema.construir_prompt_narracion`) con `ESQUEMA_NARRACION`
(`{texto}`) y devuelve `ResultadoNarracion`, degradando a texto vacío sin
lanzar. La petición viaja por la misma cola que las decisiones como
`PeticionNarracion`, comparte el presupuesto en vuelo y el worker la resuelve
contra el mismo cliente; la frase vuelve como `TextoNarrado` y
`Simulacion._drenar` la aplica a la entrada del diario que la pidió. Sin hueco
en la cola, sin servicio o con JSON inválido el hito se queda sin frase, pero
se registró igual en el tick en que ocurrió. `backend_stub` detecta el `format`
de narración y responde por hash del prompt, así que `--llm stub
--llm-sincrono` produce el mismo diario en cada corrida.

### 2.4 Memoria colectiva — `tribal/culture/`

`grafo.py` mantiene `nodos` + `aristas` en RAM; el espejo en SQLite lo escribe
`store` (§2.5), que es el único que importa `sqlite3`.
`origen.py` asigna el nivel de emergencia de concepto §8b
(`arbol | combinacion | interaccion | llm`) en el momento de crear el nodo —es
un dato de nacimiento, no una etiqueta posterior—. `transmision.py` implementa
las dos rutas por las que un nodo se propaga: **enseñar** (anciano → joven,
coste de tiempo, depende de lenguaje) e **imitar** (conformistas copian lo que
ven funcionar). Un nodo que nadie transmite y cuyo portador muere queda
`apagado`, no borrado: las técnicas perdidas son parte del experimento.

**Implementación (F3-002).** Enseñar exige proximidad (≤2 tiles) y que
`proto_palabras` esté activo: `core.acciones.ensenar(..., lenguaje=...)`, y
`hablar` usa el mismo canal. Sin lenguaje no se transfiere ninguna habilidad;
la imitación pasiva de quien ve usar una técnica sí ocurre y no mira el
temperamento, así que los conformistas también copian. El portador de un nodo
es un vivo que sabe la habilidad que el nodo exige (`HABILIDAD_POR_NODO`):
las combinaciones piden la de `HABILIDAD_POR_COMBINACION` y el resto del árbol
son prácticas situacionales que puede ejercer cualquier vivo. `Simulacion`
llama a `transmision.sostener` en cada tick tras enterrar a los muertos; cuando
un nodo lleva `TICKS_SIN_PORTADOR` (120) ticks sin portadores, `Grafo.apagar`
lo marca `apagado` con tick y motivo, sin tocar `origen`, `autor` ni `tick`, y
sin sacarlo de `nodos`. `Grafo.contar` y `report culture --json` publican
`activos`, `apagados` y `nodos_por_estado`; `_nodo_a_json` añade `estado`,
`tick_apagado` y `motivo_apagado`. La tabla `nodos` guarda también
`tick_apagado` y `motivo_apagado` (con `ALTER TABLE` al abrir una base anterior
a F3-002), así que cerrar y reabrir la partida conserva la defunción del nodo.

**Consulta (F3-005).** `consulta.py` responde preguntas sobre el grafo
guardado: `consultar(grafo, texto)` reconoce la intención por palabras clave
—`ruta`/`camino`/`lleva`/`llega`/`llegar`/`conecta`/`hasta` para un camino,
`apag*`/`perdid*`/`murieron`/`fallecieron`/`desaparecieron` para las técnicas
perdidas— y devuelve datos del grafo, nunca texto
inventado. Para una ruta busca el destino por título o id (coincidencia entera
primero, parecido después) o, si la pregunta nombra una rama, su nodo activo
más avanzado; el camino es un BFS no dirigido desde la raíz de esa rama (su
nivel 0, o el nodo más antiguo), con `origen`, `autor`, `tick` y la arista
usada en cada paso. Para los apagados devuelve `tick_apagado`, `motivo`, el
`autor` (portador original) y el último portador conocido si está en RAM; la
base no guarda ese último dato, así que al releer sale `desconocido`. Una
pregunta sin respuesta devuelve la lista vacía con `motivo` y no es un error
del comando (exit 0); solo una base inválida sale con 2. `culture ask --db
tribu.db --query "..."` publica la respuesta en texto o `--json`.

`diario.py` (F2-005) es la memoria narrativa de concepto §10: `Entrada(tick,
tipo, texto, individuo_id, narrada)` y `Diario.registrar/ultimas/a_json`. El
motor lo llena desde `Simulacion._hito` —nodos `observar_rayo` (primer fuego),
`proto_palabras` (primera palabra), `ritual` (primer rito) y `caza_cooperativa`
(primera caza en grupo), más la primera tradición y cada muerte de anciano— y
desde `_drenar` (diálogos), y la frase del LLM se escribe después, tal cual, con
`Diario.narrar`. La entrada existe aunque no haya frase: narrar es opcional y
nunca bloquea el tick. `ultimas(n)` ordena por `tick` —estable para empates— y
no por orden de llegada, porque una decisión asíncrona puede anotar un diálogo
anterior al último hito; `resumen()["diario"]` publica `{entradas, narradas,
dialogos, ultimas}` ya ordenado, y `report diary` usa la misma vista.

### 2.5 Persistencia — `tribal/store/`

SQLite embebido, tablas de stack §5 (`individuos`, `relaciones`, `recursos`,
`mundo`, `nodos`, `aristas`, `recuerdos`, `diario`, `telemetria`), con las
columnas flexibles en JSON. Es el **único** módulo que importa `sqlite3`: el
resto trabaja contra una interfaz fina (`Repositorio`), que es la puerta que
stack §3 deja abierta para cambiar a Mongo/Neo4j si algún día hiciera falta.
La escritura va en lote por intervalo, no por frame: 60 escrituras/s de SQLite
son posibles pero gratuitas de evitar. `export.py` es el **único** dueño de la
salida a Markdown: vuelca `nodos`+`aristas` a `.md` con `[[wikilinks]]` para el
vault de la tribu. Ni `culture` ni `ui` exportan por su cuenta.

**Implementación (F3-001).** `esquema.py` guarda el DDL como texto y no importa
`sqlite3`; `repositorio.py` abre la conexión, aplica `PRAGMA journal_mode=WAL`
y `foreign_keys=ON` y expone `guardar`, `cargar`, `instantanea` y `cerrar`. El
volcado es completo y transaccional —sustituye el estado anterior, no acumula
deltas— y ocurre cada `config.ticks_guardado` ticks (300 por defecto) y al
cerrar. `nodos` lleva `origen`, `autor` y `tick` en columnas propias porque son
datos de nacimiento (§8b) y el KPI se reconstruye desde ellos; `tipo` es la rama
y `popularidad` son las veces usado. `genoma`, `habilidades`, `personalidad`,
`contenido`, `requisitos`, `clima` y `config` son JSON. `run --db` conecta el
motor a la base y `report db` la lee sin simular ni ejecutar DDL (`crear=False`
valida las tablas), con código 2 si el fichero no es una partida válida.

Límite deliberado: **no se reanuda la partida**. `cargar()` reconstruye el
grafo y la población para leer y verificar; el mundo (tiles, recursos, azar) no
se rehidrata y seguir jugando es SAVE-001. `relaciones` y `recuerdos` existen
con su esquema, pero aún se escriben vacías: el motor no guarda vínculos y el
índice de recuerdos solo expone vectores, no los textos.

**Export (F3-003).** `export.py` lee nodos y aristas con `Repositorio` y
escribe `out/<slug>.md` + `index.md`: frontmatter con los datos de nacimiento,
cuerpo con el contenido y una sección de relaciones con un `[[wikilink]]` por
arista de entrada y de salida. El slug sale del id saneado a ASCII y una
colisión de saneado lleva sufijo `-2`; los títulos repetidos no colisionan
porque el título nunca nombra el fichero. El orden (ids, aristas) y la
codificación (UTF-8 sin BOM, LF) son fijos, así que el export es idempotente
byte a byte. No borra `.md` viejos —el vault puede tener notas humanas—;
`index.md` se reescribe siempre y resume nodos por origen y estado.

**Telemetría histórica (F3-004).** El motor añade a `telemetria` una fila cada
`config.ticks_telemetria` ticks (60 por defecto), no por frame: 100 filas para
6000 ticks. Cada fila guarda `tick`, `poblacion`, `n_divergentes`,
`n_conformistas`, `n_neutros`, `n_nodos`, `n_aristas`, `media_energia` y
`media_sed`. Las filas se acumulan en el motor y viajan con cada volcado
completo; si la partida termina fuera de intervalo, el estado final se añade al
cerrar. `Repositorio.telemetria()` las lee ordenadas y `report telemetry --db`
publica tabla, lista JSON o CSV (UTF-8, LF, cabecera), sin resimular. Abrir una
base anterior a F3-004 —también en lectura— añade las columnas nuevas con
`ALTER TABLE` sin borrar filas, así que las muestras heredadas leen sus tres
campos nuevos a cero. Sobre una base existente `run --db` se niega a continuar
(exit 2) para no sustituir el histórico; `--fresh` es la única vía que borra y
empieza de cero.

### 2.6 Observación — `tribal/ui/`

`render.py` dibuja el mapa top-down con sprites; `telemetria.py` muestrea por
intervalo (población, divergentes/conformistas, nodos, aristas) y la escribe en
`telemetria`. La UI **lee** el mundo; nunca lo muta (si muta, deja de ser un
observador y el determinismo se pierde) y no exporta: el export es de `store`
(§2.5).

---

## 3. El flujo de un frame

```
cada frame (dt = 1/60 s, reloj acelerable):

1. RELOJ      mundo.tick += 1; estación/clima si toca; recursos regeneran
2. PERCIBIR   cada individuo actualiza su vista local del mundo
3. DECIDIR    intención vigente = DecisionLLM si no ha caducado
                             | instinto.elegir(individuo, mundo, azar)
4. ENCOLAR    si hay dilema y hueco: llm.encolar(Peticion(tick, individuo_id,
                                                        contexto_serializable))
              -> no bloquea: es un put_nowait con cola acotada
5. RESOLVER   acciones.aplicar(...) -> energía, salud, inventario, vínculos
6. EVENTOS    descubrimiento / muerte / primer fuego -> nodos de cultura
              (con su origen) + línea en diario
7. DRENAR     llm.recoger(): get_nowait hasta vaciar; cada resultado se valida
              y se aplica como intención futura, o se descarta si caducó
8. DIBUJAR    ui.render.dibujar(mundo)   <-- aquí no hay ninguna llamada LLM
```

Detalle de la parte que importa (pasos 4 y 7):

- **La petición no lleva objetos vivos.** Lleva un diccionario plano (id,
  necesidades, saliencia, últimos recuerdos, subgrafo de cultura relevante,
  acciones disponibles). Así el hilo del LLM no toca estructuras del mundo y no
  hay carreras que depurar.
- **Ventana de validez.** Una `DecisionLLM` emitida en el tick *T* se aplica
  solo si llega antes de *T + ventana* (p. ej. 180 ticks = 3 s reales a 60 fps).
  Pasada la ventana se descarta en silencio: el mundo ya cambió y decidir con
  información de hace tres segundos es peor que no decidir.
- **Presupuesto.** Máximo *N* peticiones en vuelo (p. ej. 4). Si la cola está
  llena, el individuo sigue por instinto y el dilema se reevalúa más tarde. Es
  la traducción operativa de «solo ~3–6 individuos piensan a la vez».
- **Implementación (F2-002).** `llm/cola.py`: un hilo daemon consume una
  `queue.Queue` acotada a `max_en_vuelo` y deposita en otra cola acotada; el
  bucle solo hace `put_nowait`/`get_nowait`, así que ninguna espera del modelo
  entra en el tick. `drenar(tick_actual)` ordena por `(tick, id)` —el orden no
  depende de la carrera— y descarta lo que llegó fuera de la ventana. `cerrar()`
  deja de aceptar, vacía las peticiones que no habían empezado (cuentan como
  descartadas), pone el centinela al final y no vuelve hasta que el worker sale
  —como mucho `en_vuelo * (timeout + 1)`—: `en_vuelo` queda a 0 y no hay hilo
  huérfano; si el transporte se pasara de ese plazo devuelve `False` para que el
  llamante avise. `--llm-sincrono` sustituye el hilo por una resolución en el
  mismo tick: es el único modo reproducible tick a tick, y solo vale con
  `--llm stub` (con `http` congelaría el tick hasta el timeout). En asíncrono la
  corrida es reproducible en el modelo pero no en los contadores `llm` ni en el
  tick de llegada, que dependen del reloj real.
- **Si el LLM no responde** (Ollama no está levantado, timeout, JSON inválido):
  no hay excepción que suba al bucle. El cliente devuelve `degradado`/`error`, la
  cola lo cuenta en `fallos` y sigue encolando con el mismo presupuesto —**no hay
  backoff**—: la simulación sigue por instinto indefinidamente. Fase 0 y Fase 1
  corren así *por diseño*, sin LLM: la puerta de Fase 1 exige que la tribu ya viva
  sin él. `report telemetry --llm` publica por muestra `peticiones`, `aplicadas`,
  `descartadas`, `fallos` y `latencia_ms_media` (media real de las inferencias;
  con `stub` es el tiempo del backend falso, ≈0). El modo reproducible es
  `--llm stub --llm-sincrono`: mismo backend falso por hash del prompt y sin
  hilo; la suite además cierra la cola y comprueba que no queda `tribal-llm`.
- **Embeddings** van en CPU (stack §2) y solo se consultan al construir el
  contexto de una petición. La recuperación es síncrona en el hilo del bucle
  —unas decenas de productos escalares sobre 256 floats—, pero **nunca** en el
  hilo de render ni en el del LLM: una guarda en `IndiceRecuerdos.buscar` lo
  comprueba por pila de llamadas y por nombre de hilo. El backend determinista
  (hashing) no abre red; el de Ollama, si se usa, pide `usa_gpu=false` y
  degrada a vector nulo cuando el servicio no está.

---

## 4. Fronteras entre módulos

La regla es de dependencias, no de carpetas: **las flechas no vuelven**.

```
ui ──► llm ──► core ◄── agents
 │       │        ▲        │
 └───────┴──► culture ◄────┘
              ▲
            store  (el único que habla sqlite3)
```

| Quién | Puede importar | No puede importar |
|---|---|---|
| `core` | stdlib (`core.modelos` son sus propios modelos de datos) | `llm`, `ui`, `store`, `culture`, `agents` |
| `agents` | `core`, `culture` (lectura) | `llm` (pide, no llama), `ui`, `store` |
| `llm` | stdlib, `core.modelos` (para validar) | `ui`, `store` |
| `culture` | `core` | `llm`, `ui`, `store` |
| `store` | `core`, `culture` (serializar) | `ui` |
| `ui` | todo (solo lee) | — |

Dos comprobaciones automatizables (a `tests/`, cuando existan los módulos):
`core` no importa `llm`, y el hilo que llama a `llm.encolar`/`llm.recoger` no
es el que dibuja. La primera es un test de imports; la segunda, una aserción
sobre `threading.current_thread()` en los métodos públicos de la cola.

### 4.1 Estructura de directorios propuesta

```
tribal/
  __init__.py        versión del paquete (existe)
  __main__.py        python -m tribal (existe)
  cli.py             punto de entrada, subcomandos (existe)
  paths.py           rutas del repo, resueltas una vez (existe)
  config.py          parámetros de la partida + seed (Fase 0)
  core/
    mundo.py  recursos.py  acciones.py  modelos.py
  agents/
    individuo.py  necesidades.py  instinto.py  saliencia.py
  llm/
    cola.py  cliente.py  esquema.py  seleccion.py  aplicar.py
  culture/
    grafo.py  origen.py  transmision.py
  store/
    esquema.py  repositorio.py  export.py
  ui/
    render.py  telemetria.py  panel.py
```

Dos avisos de nombres, decididos aquí para no descubrirlos en CORE-001:

- `agents/` en la raíz es el **arnés de build**; `tribal/agents/` son los
  individuos simulados (stack §9, «ojo con los dos significados de agente»).
  Dentro de `tribal/` no hay ambigüedad porque el prefijo ya está.
- `models/` en la raíz son los `.gguf` (ignorados por git). Los modelos de
  datos Pydantic van en `tribal/core/modelos.py`, **no** en `tribal/models/`.

---

## 5. Alternativas consideradas y descartadas

Cada una se descarta **hoy**, con el disparador que la reabriría escrito al
lado. Sin disparador, una alternativa descartada es una opinión.

### 5.1 Turnos por tablero en vez de tiempo continuo

*Descartada.* Todo el mundo actúa a la vez, en continuo, con un reloj que
deriva `seg_simulado = tick / fps * velocidad_reloj`. Un tablero por turnos
sería más fácil de razonar y de testear, pero mata justo lo que se quiere
observar: el agolparse junto al agua, la huida en manada, la llegada tarde a un
cadáver. Con turnos, el orden de resolución *es* el diseño.

*Disparador para reabrir:* que la puerta F0→F1 no muestre ningún
comportamiento emergente con reglas locales y la causa demostrable sea el orden
de resolución.

### 5.2 Todos los individuos con LLM en cada turno

*Descartada.* Con 8–15 individuos y latencias de 0,2–1,5 s por decisión
(concepto §12), pedirle a todos una decisión por turno hace imposible el
objetivo de 60 fps y quema la GPU en diálogo trivial. Se adopta el **híbrido
por saliencia** de §10b: instinto para todos, LLM solo ante dilema, y más a
menudo para quien ha ganado peso narrativo.

*Disparador para reabrir:* que la puerta F2→F3 muestre que los personajes
emergentes lo son *porque* el instinto los hace interesantes y el LLM solo
narra — es decir, que el gradiente de saliencia no aporte nada medible.

### 5.3 Mongo o Neo4j en vez de SQLite + grafo en dos tablas

*Descartada.* La parte emergente es la cultura, y eso es un grafo: se modela
con dos tablas (`nodos`, `aristas`) y se recorre en memoria. Mongo añade un
daemon y no resuelve el grafo; Neo4j lo resuelve pero es un servidor más para
una máquina y un observador (stack §3). Una capa de repositorio fina deja la
puerta abierta.

*Disparador para reabrir:* consultas de camino/explicación sobre el grafo que
en SQL se vuelvan ilegibles o lentas con el tamaño real de una partida, o la
necesidad de servir el grafo a más de un consumidor.

*Implementado en F3-001:* `tribal/store/` escribe y relee la partida con el
esquema de stack §5; el resto del producto solo ve `Repositorio`. Si algún día
se reabre esta decisión, la interfaz es el único punto que cambia.

### 5.4 Rust en vez de Python

*Descartada.* El cuello de botella es la inferencia, que ya es C++/CUDA: Rust
no acelera ni un token. La simulación de 8–15 individuos es trivial para
Python. Se paga en velocidad de iteración (que es lo que Fase 0–1 necesita) por
un rendimiento que no se usa. El ecosistema LLM local es Python-first.

*Disparador para reabrir:* que el motor de reglas sea el límite medido (perfil
que muestre el tick por encima del presupuesto de 16 ms con la población
objetivo). Entonces se reescribe **ese módulo** (PyO3/WASM), no el proyecto.

### 5.5 LLM dentro del proceso (hilo + `queue`) en vez de proceso aparte

*Descartada como ruta por defecto.* Cargar el modelo dentro del proceso de
Pygame (`llama-cpp-python`) ata el ciclo de vida del modelo al de la
simulación —reiniciar el modelo es reiniciar la partida—, arrastra compilación
nativa en Windows y el objeto **no es thread-safe**: un solo hilo puede
inferir, y un fallo de CUDA se lleva por delante el render. La ruta oficial es
**Ollama** como proceso aparte (`127.0.0.1:11434`), que es llama.cpp
empaquetado: misma GPU, mismo GGUF, sin compilar ni gestionar binarios. La cola
y el hilo de cliente son iguales en ambos casos; lo que cambia es quién posee
el modelo.

*Disparador para reabrir:* que la serialización del contexto por HTTP o la
latencia del socket pasen a ser el límite, o que haga falta control fino de KV
cache que la API de Ollama no exponga. En ese caso, `llama-server` propio o
`llama-cpp-python` con **un único hilo de inferencia y jamás dos a la vez**
(stack §8).

### 5.6 Vista web (D3) como interfaz principal

*Descartada para el bucle principal.* D3 es la mejor herramienta para *ver el
grafo* y se usará en Fase 3, pero como vista del grafo servida por un
mini-servidor local, no como interfaz del mundo. Pygame da el mapa top-down a
60 fps sin protocolo de por medio; meter WebSocket en el camino crítico
traslada el presupuesto de frame a la red.

*Disparador para reabrir:* que el render 2D deje de ser suficiente para
entender la emergencia (p. ej. el grafo en vivo pasa a ser la vista primaria).

---

## 6. Riesgos conocidos y su mitigación

| # | Riesgo | Por qué duele aquí | Mitigación |
|---|---|---|---|
| 1 | **Incoherencia** (fuego el día 1) | El KPI mide nodos fuera del árbol; si el árbol se rompe, mide ruido | Árbol de plausibilidad como validador + `origen` por nodo + memoria estructurada |
| 2 | **Bucle sin progresión** | La tribu caza y recolecta para siempre y no hay nada que medir | Presión ambiental creciente (estaciones, sequía) + disparadores de evento |
| 3 | **Memoria sin límite** | RAM y contexto del LLM crecen hasta romper ambos | Resumen periódico: episodios → conocimiento → tradición; `recuerdos` con `saliencia` y poda |
| 4 | **Extinción de la tribu** | Una partida se acaba antes de demostrar nada | Reposición mínima + persistencia de la cultura: los nodos no mueren con la última persona |
| 5 | **Coste de tokens / latencia** | Un LLM lento convierte el dilema en un tirón visible | Heurística para lo trivial, JSON de 5–15 tokens, ventana de validez, presupuesto de cola |
| 6 | **Español pobre del modelo** | El diálogo es la mitad del producto | Qwen/Gemma (buenos en español) + gramática que no exige prosa larga |
| 7 | **`llama-cpp-python` no es thread-safe** | Dos hilos inferiendo = corrupción o cuelgue | Ruta oficial Ollama (proceso aparte); si alguna vez se usa en proceso, un único hilo de inferencia y candado |
| 8 | **VRAM de 6 GB** | El LLM (3B Q8) + embeddings no caben juntos | Embeddings en CPU (stack §2); medir VRAM real antes de Fase 2 (`ollama ps` debe decir 100 % GPU) |
| 9 | **Frame budget** | 60 fps con 15 individuos y UI | Motor determinista y barato; LLM fuera del hilo de render; telemetría por intervalo, no por frame |
| 10 | **RAG ciego tras el renombrado** | `agents/tools/rag_tool.py` tiene `app` fijo en su tabla de fuentes | Feature aparte ya identificada: hasta arreglarlo, el código de `tribal/` no entra en el índice; no rompe la puerta ni los tests |
| 11 | **Export que ensucia el vault** | Un orden distinto, un BOM o nombres que colisionan rompen los wikilinks entre exports | Slug = id saneado con sufijo `-2` en colisión, orden determinista y UTF-8/LF: dos exports son byte a byte iguales; los `.md` viejos no se borran |
| 12 | **Respuesta inventada al consultar** | Una capa de consulta con LLM podría narrar un camino que no existe y volver el grafo inútil para entender la emergencia | `culture ask` es determinista y solo cita `nodos` + `aristas`: BFS sobre el grafo guardado y, en cada paso, `origen`, `autor`, `tick` y la arista usada; sin LLM en el camino |

Riesgos 1–6 vienen de concepto §14; 7–12 son técnicos de esta arquitectura.

---

## 7. Decisiones que se dejan para más adelante

No son olvidos: están en concepto §16 y `objetivo.md` §4, y no bloquean nada de
Fase 0–1.

| Decisión | Por qué se aplaza | Cuándo se decide |
|---|---|---|
| **Persistencia entre sesiones** (¿cargar la tribu donde se quedó?) | Fase 0 mide una partida; guardar/reanudar añade versionado del esquema | Al cerrar Fase 1, con el esquema ya estable |
| **Nombre definitivo** del producto | `Tribal` es el nombre de trabajo y ya está en `project.yml`, el paquete y el repositorio | Cuando haya algo que enseñar; cambiarlo es un renombrado mecánico (DESIGN-001 ya dejó el paquete coherente) |
| **Escala temporal** (¿cuánto real es un día o una estación?) | Es un parámetro de juego, no de arquitectura; se calibra mirando | Al ajustar la puerta F0→F1 |
| **D3 / FastAPI** para el grafo en vivo | Es la única pieza nueva real de Fase 3 y no toca el bucle | Fase 3 |
| **Enrutado a modelos en nube** (Groq/Gemini/OpenRouter con fallback local) | Rompe la reproducibilidad y la privacidad local; el local aún no se ha agotado | Después de Fase 2, si el local no basta |
| **Intervención del usuario** | Fuera de alcance (`objetivo.md` §4): en cuanto el humano empuja, la emergencia no es demostrable | No decidido |
| **Docker / distribución** | Resuelve empaquetado, no el experimento | Cuando toque distribuir |

---

## 8. Cómo esta arquitectura hace medible el KPI

`objetivo.md` §3.2 pide, al cerrar una partida, que **≥50 % de los nodos
activos** tengan `origen` distinto de `arbol`. La arquitectura lo hace
comprobable en tres puntos concretos:

1. **`origen` se escribe al nacer el nodo** (`tribal/culture/origen.py`), no se
   deduce después. Un nodo creado por el motor desde el árbol nunca puede
   reetiquetarse como emergente.
2. **Todo nodo va a `nodos` en SQLite**, con `estado` (`activo`/`apagado`). La
   consulta del KPI —`SUM(origen IN ('combinacion','interaccion')) / COUNT(*)`
   sobre `estado='activo'`— no depende de nada que viva solo en RAM.
3. **La partida es reproducible** (semilla + `config`), así que un porcentaje
   inesperado se puede volver a inspeccionar en vez de solo anotarse. El KPI se
   convierte en test del repositorio al cerrar Fase 3 (`objetivo.md` §3.2).

Lo que la arquitectura **no** puede hacer por sí sola: decidir si el número es
bueno. Eso son las puertas de concepto §15 y el líder de la fase.

---

## 9. Estado de implementación

**Existe hoy (Fase 1 cerrada, sin LLM):**

- Paquete `tribal/` con `__init__.py` (versión), `__main__.py`, `paths.py`,
  `config.py` (`SimConfig` inmutable y serializable a JSON) y `cli.py` con
  `hello`, `run`, `report culture`, `report telemetry` y `report gate-f1`.
- `tribal/core/`: mundo, recursos y parches, acciones, modelos, genoma con
  mutación, habilidades y depredador.
- `tribal/agents/`: necesidades e instinto (política sin LLM; la percepción
  cambia con el temperamento, la decisión no).
- `tribal/culture/`: árbol de plausibilidad con cinco ramas, grafo de nodos y
  aristas con `origen`, combinaciones, utilidad situacional y tradiciones.
- `tribal/sim.py`: `Simulacion` (motor de una partida), `run` (corrida
  headless o con ventana), `run_muestreado` (telemetría por intervalo) y el
  `resumen()` determinista que publica `run --json`.
- `tribal/ui/`: bucle Pygame a 60 fps y render top-down; la UI lee el mundo y
  no lo muta.
- `tribal/llm/`: `esquema.py` (JSON schema, validación y few-shot) y
  `cliente.py` (HTTP a Ollama con transporte inyectable y degradación sin
  excepciones). `uv run python -m tribal llm selfcheck --json` informa del
  servicio; la cola y la selección por saliencia son F2-002.
- `tribal/gate_f1.py`: barrido calma/crisis por semilla y veredicto de la
  puerta F1→F2.
- Puerta del arnés en verde (`harness gate` → `ENTORNO LISTO`) y `pytest -q`
  cubriendo motor, puertas F0/F1, genoma, habilidades, divergencia, utilidad,
  ambiente, tradiciones, configuración y reproducibilidad por semilla.

Comandos de la fase:

```bash
uv run python -m tribal run --headless --json --ticks 600 --seed 7
uv run python -m tribal run --headless --config docs/config-ejemplo.json --json --ticks 600
uv run python -m tribal report culture --json
uv run python -m tribal report telemetry --json --ticks 600 --intervalo 60
uv run python -m tribal report gate-f1 --seeds 1-10 --ticks 8000
```

**No existe todavía (y este documento no implementa):**

- Capa LLM (`tribal/llm/`): cola asíncrona, selección por saliencia y
  aplicación diferida. Empieza en Fase 2 (`F2-002`); `cliente.py` y
  `esquema.py` ya existen. El id del modelo es `tribal-llm` (`tribal.Modelfile`
  en la raíz del repo: `FROM qwen2.5:3b-instruct-q8_0` con `num_ctx 8192`).
- Persistencia SQLite (`tribal/store/`), export a Obsidian y telemetría leída
  de una partida guardada. Fase 3 (`F3-001`, `F3-003`, `F3-004`).
- Diario narrado, memoria colectiva persistida y consulta del grafo. Fase 2–3.

### 9.1 Qué ramas avanza F1 y con qué prácticas

La puerta F1→F2 de `concepto.md` §15 pide descubrir sin LLM algo más allá del
primer paso forzado y que la proporción divergente reaccione a la crisis. Esta
sección describe el material: cada rama avanza porque la tribu **hace** algo,
no porque el motor premie un rasgo. La medida de la puerta está en §9.3.

| Rama | Práctica (verbo) | Condición | Efecto |
|---|---|---|---|
| `litica` | comer | bayas o caza al alcance | energía (exige `recolectar`) |
| `litica` | tallar | junto a bosque | −0,5 de energía |
| `fuego` | frotar_madera | junto a bosque | −1,0 de energía |
| `lenguaje` | hablar | otro individuo a ≤2 tiles | puede transmitir una habilidad |
| `roles` | enseñar | aprendiz a ≤2 tiles | transmite una habilidad |
| `roles` | cuidar | herido a ≤2 tiles (salud < 100) | +0,5 de salud al atendido |
| `simbolico` | pintar | junto a bosque o agua | consume el tick, −0,2 de energía |

`PRACTICAS` (`tribal/sim.py`) mapea verbo → `(rama, habilidad opcional)`; las
condiciones las valida el verbo en `tribal/core/acciones.py` y el instinto las
elige solo en el tramo ocioso, con una rotación determinista por individuo y
tick. El árbol sigue mandando en el nivel: una práctica solo descubre el
siguiente escalón si sus prerrequisitos están activos, y como mucho nace un nodo
por tick. En calma avanzan las cinco ramas: lítica, fuego, lenguaje y símbolo en
los primeros ticks; roles cuando aparece una cría o un herido. Con eso,
`canto_ritual` (lenguaje + símbolo) y los demás cruces de
`tribal/culture/combinaciones.py` dejan de ser inalcanzables cuando un divergente
experimenta en crisis.

La puerta completa se mide en §9.3 (F1-006); el `pct_fuera_arbol` de
`objetivo.md` §3.2 (por encima del 50 %) sigue siendo de Fase 3.

### 9.2 La divergencia como conducta (DIVERGENCIA-002)

`divergencia` no es aptitud: no toca el bocado, la sed, la cría ni el genoma.
El contrato está en `tests/test_divergencia_calma.py` y tiene dos mitades: una
**lista blanca** de los únicos sitios que pueden leer el rasgo
(`genoma.temperamento`, `genoma.heredar`, el paseo de `instinto` y la
probabilidad de experimentar en `sim`) —cualquier otro acceso falla el test,
sea comparación, umbral o `+=`— y tests de conducta para el bocado (`comer`), la
sed al beber, el umbral de cría (`UMBRAL±1` con 0.1 y 0.9) y el genoma congelado
en una partida de 500 ticks. Lo que cambia el rasgo es **qué hace** el
individuo:

| Tramo | Radio del paseo | Sesgo de cohesión |
|---|---|---|
| conformista (`div < 0.4`) | 3 tiles | hacia el vecino más cercano |
| neutro | 5 tiles | ninguno |
| divergente (`div > 0.6`) | 10 tiles | se aparta del vecino |

El sesgo es firmado (`SESGO_COHESION * (1 - 2 * divergencia)`) y el destino se
recuerda hasta llegar, así que el radio es un rumbo y no difusión. La urgencia
manda por encima del rasgo: sed crítica y depredador dan la misma acción a los
dos temperamentos. Todo sale de `Mundo.azar`: misma semilla, misma trayectoria.

Para que la selección sea medible y no una opinión, `Simulacion.resumen()`
publica `descubridores` (ids que descubrieron una combinación),
`supervivencia_descubridores`, `supervivencia_no_descubridores` y
`diferencial_seleccion` (la resta). La ventaja, cuando aparece, es de la
habilidad que el autor aprende al descubrir; el informe de 10 semillas de
DIVERGENCIA-002 está en el README.

### 9.3 La puerta F1→F2, medida (F1-006)

La puerta de concepto §15 no se decide con una corrida afortunada: se mide con
`python -m tribal report gate-f1 --seeds 1-10 --ticks 8000` (`--json` para el
informe). La herramienta corre **dos brazos por semilla**, calma y crisis, con
la misma `SimConfig` salvo `crisis`, y publica:

| Columna | Qué es |
|---|---|
| `nac_div` | media de `divergencia` de **todos los nacidos** acumulados (medida primaria) |
| `S_fec` | reproductores (una vez por individuo) − población inicial del brazo (fecundidad) |
| `S_via` | vivos al terminar − población inicial (viabilidad; 0 si no hay vivos) |
| `desc/d`, `desc/c` | combinaciones descubiertas por divergente / conformista registrado |
| `imit/desc` | imitaciones totales / combinaciones descubiertas (0 si no hay) |
| `long_d`, `long_c` | edad media al morir de descubridores / conformistas |
| `div%` | divergentes vivos / vivos al terminar (secundaria) |
| media / σ | distribución de `divergencia` entre los vivos al terminar |
| nacidos / nodos | crías y `combinacion` + `interaccion` |
| población / extinciones | vivos al terminar y corridas que acaban en cero |

El porcentaje de vivos es binomial con 12 fundadores; por eso la medida
primaria es la respuesta en la descendencia. `S_fec` usa como base la población
inicial del brazo (tick 0, común a calma y crisis; la sequía se aplica desde el
primer tick) y se publica `mean_divergencia_inicial`. Sin reproductores no hay S
y esa fila no cuenta.

**Criterio corregido (ronda 6):** `senal` (alias `primaria`) es el **veredicto
de la puerta**: `S_fec > 0` en crisis en ≥6/10 y **`S_fec < 0` en calma en
≥6/10**. En estabilidad manda la tradición (concepto §15); la neutralidad
(|S| ≤ 0.01) era un **error de criterio**, no una propiedad del mundo. La clave
antigua `pasa` se llama ahora `secundaria` (cuatro criterios de `div%`) y **no
decide**; se publica solo como información.

El mecanismo que se mide es **percepción → conducta → aptitud**:

- El temperamento decide el radio en el que se ve la comida: 4 / 8 / 14 tiles
  para conformista / neutro / divergente (`instinto.RADIO_PERCEPCION_*`). El
  agua es terreno y se ve desde lejos; lo que se busca a ciegas es el parche.
- **La memoria social es condicional a la migración**: si el parche recordado
  no ha migrado desde que se formó/copió, la copia es precisa aunque el consumo
  lo deje temporalmente vacío; si migró, está obsoleta y el conformista copia
  la memoria —también vieja— del vecino con más energía. Es una propiedad
  física de la memoria (adaptativa en estabilidad, maladaptativa en cambio), no
  una bonificación. Tests:
  `test_la_informacion_del_conformista_es_precisa_si_el_parche_no_migra` y
  `test_la_migracion_se_acelera_con_la_escasez`.
- El divergente, sin comida en su radio, va al parche migrado más reciente o al
  menos visitado. Explorar solo se activa cuando no hay comida en el radio y
  cuesta `COSTE_EXPLORAR` por tick, pagado por el motor.
- **La migración solo ocurre en crisis**: en calma un parche agotado se
  regenera en el sitio (la memoria del conformista sigue siendo válida); en
  crisis el agotamiento dispara la migración, con espera proporcional a la
  escasez (`ticks_migracion` = 3000 con parche lleno, 1/5 = 600 agotado) y una
  reubicación de **≥11 tiles** (`DISTANCIA_MINIMA_MIGRACION`): fuera del
  horizonte del conformista (4) y dentro del divergente (14). Si no hay casilla
  válida, ese parche no migra. `migracion=false` apaga la migración en ambos
  regímenes. Tests:
  `test_en_calma_el_parche_se_regenera_en_el_sitio_y_en_crisis_migra` y
  `test_la_migracion_en_crisis_deja_el_parche_fuera_del_horizonte_conformista`.
- Umbrales 0.55 / 0.45 (media 0.5, σ≈0.04; el 0.6 dejaba la cola a ~3σ). La
  utilidad situacional de las combinaciones sigue pagando solo a quien tiene el
  nodo y su recurso escasea.

No hay canal que lea el rasgo para dar comida, sed, crías ni para editar el
genoma: lo vigilan `tests/test_divergencia_calma.py` y, con snapshots alrededor
de `_intentar_combinacion`, `_practicar` y `_punto_errante` y una lista blanca
de llamadas a `temperamento()`, `tests/test_puerta_f1.py`.

**Resultado del barrido (10 × 8000, 12 individuos):** la tabla completa está en
el README. Con el horizonte de 11 tiles, **la puerta cumple la medida primaria
a N=12**: `S_fec > 0` en crisis en 7/10, `S_fec < 0` en calma en 7/10, crisis ≤
calma y extinciones crisis ≤ calma. El `div%` secundario sigue sin pasar (4/10)
y no decide. La confirmación con N=50 refuerza la señal S (crisis 9/10, calma
6/10) pero **no replica crisis ≤ calma** (4/10) ni la igualdad de extinciones:
la condición de régimen favorable es dependiente de escala. El default del
juego sigue en 12 (concepto §1b); la salvedad queda documentada. `desc/c` = 0
por construcción (los conformistas no experimentan) y `long_d` = 0 porque
ningún descubridor murió dentro de la ventana. El diagnóstico completo está en
`harness/progress/implementer-F1-006.md`.

### 9.4 La puerta F2→F3, medida (F2-006)

La puerta de concepto §15 pide dos cosas observables: que el LLM proponga nodos
**fuera del árbol** (nivel 1 de §8b) que pasen la validación a un ritmo no
trivial, y que la saliencia concentre la narración en pocos individuos (§10b).
`python -m tribal report gate-f2` las mide con un **backend guionizado**
determinista, sin red y sin tocar el catálogo:

```bash
uv run python -m tribal report gate-f2 --seeds 1-5 --ticks 3000 --crisis \
  --llm script --llm-sincrono --json
```

**Canal de propuestas.** `tribal/culture/propuestas.py` es la frontera entre el
modelo y el grafo. El LLM devuelve `{id, rama, requisitos, titulo, contenido}` y
el motor decide:

- id del catálogo (`combinaciones.py`): se comprueba que los requisitos no se
  hayan cambiado y se delega en `Grafo.descubrir`, que vuelve a validar los
  prerrequisitos y escribe `origen="combinacion"`;
- id nuevo: los dos requisitos tienen que estar **activos** y ser de la misma
  rama o de ramas adyacentes en `RAMAS`; la rama del nodo es una de las dos. El
  nodo nace con `autor`, `tick`, `nivel = max(niveles) + 1`, contenido anclado a
  los dos requisitos y un efecto de sed derivado de los dos ids. Un `comb_*`
  nace como `combinacion` (regla de plausibilidad) y **no puede encadenarse**:
  sus requisitos no pueden ser otro `comb_*` ni un `llm_*`. El resto de cruces
  nuevos nace como `llm` (nivel 1 de §8b);
- cualquier otra cosa se rechaza con un motivo (`prerrequisito`, `rama`,
  `duplicado`, `cadena`, `formato`, `catalogo`) y se cuenta en `propuestas_llm`.

La petición se dispara cuando un divergente experimenta en crisis y, además,
hay un **turno de invención por reloj** cada `PROPUESTA_CADA_TICKS = 100`: una
tribu pequeña no pide menos propuestas solo por tener menos divergentes. Una
partida de 3000 ticks pide 30 propuestas y acepta 19, sin inundar el grafo. Sin
LLM (o fuera de la crisis) no hay peticiones: la dinámica de F1 no cambia. El
canal usa la misma cola y el mismo presupuesto en vuelo que las decisiones y la
narración (`PeticionNodo`), y la propuesta se valida contra el grafo del tick
en que se aplica, no contra el que había cuando se pidió.

**K = 5.** Son las cinco combinaciones del catálogo, el nivel 1 completo de
§8b. No es trivial porque exige que cuajen **todos** los cruces posibles en cada
semilla, no un acierto aislado; además el veredicto pide ≥ 1 propuesta nueva del
canal que no esté en el catálogo, para que el modelo se haya ejercitado. El
nodo nace como `llm` (o `comb_*` como `combinacion`); el canal se cuenta en
`propuestas_llm`. El backend intercala propuestas imposibles para que el test
demuestre también el rechazo.

**Narración concentrada.** El cronista ya no se reparte por el censo: en
`_hito`, `_narrador` elige al sujeto del hito si está en el top-3 de **peso
narrativo acumulado** y, si no, al individuo con más peso; sin nadie con peso
positivo no se pide frase. El peso es el **área acumulada** de saliencia (la
suma de lo ganado en toda la partida), mientras que la saliencia instantánea
sí decae (`DECAIMIENTO = 0.999` por tick). Así el techo `SALIENCIA_MAX = 10`
no convierte el top-3 en un empate de ids y el protagonismo temprano no se
pierde por un pico tardío. La entrada guarda `narrador_id` además de `individuo_id`; la
concentración de la puerta es `líneas de los tres con más peso / líneas
narradas` y exige ≥ 50 %.

**Resultado del barrido (5 × 3000, 12 individuos, crisis):** la tabla completa
está en el README. `SUCCESS True` en 5/5: 19 nodos `llm` por semilla (cruces
nuevos del canal), 2-5 `combinacion` del catálogo activos y 0-5 tradiciones
activas; 19 propuestas aceptadas y 11 rechazadas con motivo; concentración
top-3 entre 0.7 y 1.0. El KPI `pct_fuera_arbol` (combinación + interacción +
`llm`, `objetivo.md` §3.2) queda en 50.0-55.8 % y pasa en las cinco. `llm` ya
no es un origen residual: es nivel 1 y cuenta. El límite conocido es el tamaño
de la muestra: la concentración se mide sobre 12-17 líneas narradas por partida;
el test fija las semillas 1 y 3 y la tabla publica las cinco.

### 9.5 El criterio de hecho, medido: `report kpi` (F3-006)

`objetivo.md` §3 pedía que el cierre de Fase 3 fuese una consulta, no una
sensación. `tribal/culture/kpi.py` reúne esa comprobación en `evaluar(db) -> KPI`
y `report kpi` la publica sin simular ni escribir:

```bash
uv run python -m tribal report kpi --db tribu.db [--json]
```

**Hitos (§3.1).** Se miran nodos `activo`: `fuego` (rama `fuego`),
`herramienta_compuesta` (rama `litica` con ≥ 2 aristas entrantes),
`proto_lenguaje` (rama `lenguaje`, `nivel > 0`) y `mito`. El esquema no guarda un
`tipo` distinto de la rama, así que el mito es el nodo `mito` del árbol
(`simbolico`), el que exige `proto_palabras` + `ritual`.

**KPI (§3.2).** Es el SQL literal de `objetivo.md`, sin reinterpretarlo:

```sql
SELECT ROUND(100.0 * SUM(CASE WHEN origen IN ('combinacion','interaccion','llm')
                         THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_fuera_arbol
FROM nodos
WHERE estado = 'activo';
```

`llm` **es nivel 1** de §8b («el LLM une 2+ nodos en un paso no previsto,
validado»). Su exclusión del SQL anterior fue un error de transcripción, no de
diseño: la prosa de `objetivo.md` ya pedía «origen distinto de `arbol`» y la
solución E1 de `auditoria-llm.md` §4 ya lo decía. El denominador incluye todos
los activos, también los de nivel 0. `tests/test_kpi.py` ejecuta la consulta
literal, comprueba que `evaluar` cuenta `llm`, que excluirlo daría otro número,
que ninguna tradición copia un nodo `llm` y que hay como mucho una tradición
activa por rama.

**Veredicto.** `4 hitos && pct >= 50.0`. El comando sale con 0 aunque sea
`False`: es un informe, no una puerta; la puerta de Fase 3 es su test.

**Evidencia real (no la del script).** Semilla 1, 3000 ticks, `--crisis`,
`--llm http` contra `tribal-llm` en 127.0.0.1:11434. `llm selfcheck --json`
responde `disponible: true`, 90.6 ms. El bucle headless sin throttle corre a
~2 ms/tick y no da ventana al modelo; la misma cola HTTP a 60 fps tarda 60.37 s
y el modelo **no llega al 50 %**:

```
pct_fuera_arbol  14.8 % (4/27, umbral 50.0 %)
veredicto        False
```

Resumen LLM: 17 peticiones, **0 aplicadas**, 16 descartadas, 1 fallo; 3
propuestas de nodo, 0 aceptadas y 1 rechazada por `transporte`. La corrida
literal `run --headless --llm http` sin throttle da el mismo 14.8 % (7.04 s, 1
petición, 0 aplicadas). El veredicto real es False y se publica tal cual; no se
sustituye por el número del backend falso.

**Test determinista del mecanismo (no es la evidencia del criterio).** Con el
backend guionizado, el e2e de `test_kpi` (semilla 1, 3000 ticks) da **50.0 %
(21/42), 4/4 hitos y `veredicto True`**. El barrido de 5 semillas:

| seed | activos | arbol | comb | inter | llm | nuevos | fuera | %fuera | ok |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 42 | 21 | 2 | 0 | 19 | 21 | 21 | 50.0 | True |
| 2 | 46 | 23 | 4 | 0 | 19 | 23 | 23 | 50.0 | True |
| 3 | 46 | 23 | 4 | 0 | 19 | 23 | 23 | 50.0 | True |
| 4 | 49 | 23 | 3 | 4 | 19 | 22 | 26 | 53.1 | True |
| 5 | 52 | 23 | 5 | 5 | 19 | 24 | 29 | 55.8 | True |

`nuevos` = `comb` + `llm` (K de la puerta F2); `fuera` = `comb` + `inter` +
`llm` (KPI); todo sobre activos, una sola cabecera.

**Qué se corrigió.** El intento anterior encadenaba `comb` de `comb`: el 50 %
era inflación y el reviewer lo rechazó. Ahora:

1. **Nivel 1 real, sin cadena.** Un `comb_*` nace como `combinacion` y sus
   requisitos no pueden ser otro `comb_*` ni un `llm_*`; `propuestas.validar`
   lo rechaza con `cadena` y el backend solo propone parejas del árbol/catálogo.
   El cruce del modelo nace como `llm` (nivel 1). Su efecto es un −1 %/−2 % de
   sed derivado de los dos ids; `beneficios._agrupar` evita apilar variantes.
   Hay un turno de invención por reloj (`PROPUESTA_CADA_TICKS = 100`) además
   del experimento del divergente: 30 propuestas, 19 aceptadas, 11 rechazadas.
2. **Tradiciones genuinas y acotadas.** `tradicion_<rama>_1`, una por rama,
   con título/contenido propios, nunca de un nodo `llm`. Su efecto es cultural:
   +0.25 de saliencia al descubrir en su rama, no un multiplicador de comida.
   La imitación marca toda la rama, pero el tope impide crear una por nodo.
3. **Persistencia social.** `tradiciones.sostener` apaga con `Grafo.apagar` la
   tradición que pasa 1200 ticks sin una imitación. A partir de ~6000 ticks la
   tribu se extingue y no queda KPI que medir; la ventana viva es 3000–4000.

La narración de F2 se estabilizó midiendo el **área acumulada** de saliencia
(sin descuento): las cinco semillas dan `SUCCESS True` con concentración
0.7-1.0. `tests/test_kpi.py` ejecuta el SQL literal y exige `>= 50.0` sin
`xfail`; `tests/test_tradiciones.py` fija el tope, el apagado y la exclusión de
`llm`.

---

## 10. Referencias

- `vault/01_PROYECTO/objetivo.md` — problema, criterio de hecho, KPI (§3.2).
- `vault/01_PROYECTO/concepto.md` — §4 bucle, §8b emergencia, §10/10b LLM,
  §11 arquitectura, §14 riesgos, §16 decisiones abiertas.
- `vault/01_PROYECTO/stack-tecnologico.md` — §2 hardware, §3 datos, §5 esquema,
  §8 herramientas y concurrencia del LLM.
- `README.md` — comandos de Fase 1 y 2 (`run`, `report culture`,
  `report telemetry`, `report gate-f1`, `report gate-f2`), config de ejemplo y
  barridos de las puertas F1→F2 y F2→F3.
- `harness/progress/implementer-F1-006.md` — diagnóstico, mutaciones y salida
  literal que respaldan la puerta F1.
- `harness/progress/implementer-F2-006.md` — tabla, backend guionizado y salida
  literal que respaldan la puerta F2.
