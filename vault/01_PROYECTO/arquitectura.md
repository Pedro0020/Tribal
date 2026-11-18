# 🏗️ Arquitectura — Tribal

> Documento de diseño técnico. Destila `concepto.md` (§4, §10/10b, §11, §8b) y
> `stack-tecnologico.md` (§2, §3, §5, §8) sin introducir decisiones nuevas: si
> algo aquí contradice al concepto, gana el concepto.
> Estado: **Fase 0 en curso**. Última revisión: 2026-11-18.

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

Un individuo tiene siempre una **intención** (`Instinto | DecisionLLM`). La
intención LLM, si llega, tiene prioridad durante N ticks; si caduca, se vuelve
al instinto. Esto es lo que impide que un agente se congele esperando a un
modelo que puede tardar un segundo.

### 2.3 Capa LLM — `tribal/llm/`

- `cola.py`: dos `queue.Queue` (peticiones y resultados) + contador de en vuelo.
- `cliente.py`: el hilo de cliente. Consume peticiones, hace
  `POST http://127.0.0.1:11434/api/chat` contra Ollama con `model: tribal-llm`
  (el alias del Modelfile, que es el que arranca con `num_ctx 8192`), el campo
  `format` (JSON schema) y timeout corto, y deposita el resultado.
- `esquema.py`: el JSON schema de la respuesta. Fija el esqueleto (`accion`
  dentro del vocabulario de §7, `objetivo`, `razon`, `dialogo`) y deja libres
  los campos de texto, según stack §8 («constriñe coherencia, no dirección»).
- `seleccion.py`: quién piensa este tick. Solo se encola si hay **dilema real**
  (conflicto de necesidades, evento propio relevante, oportunidad de innovar) y
  hay hueco en la cola; a igualdad de dilema, gana más saliencia.
- `aplicar.py`: convierte el JSON validado en una `DecisionLLM` aplicable y
  descarta lo que el motor considere implausible.

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
- **Si el LLM no responde** (Ollama no está levantado, timeout, JSON inválido):
  no hay excepción que suba al bucle. El cliente cuenta fallos, marca la capa
  como `degradada` y deja de encolar durante un backoff; la simulación sigue
  por instinto indefinidamente. Fase 0 y Fase 1 corren así *por diseño*, sin
  LLM: la puerta de Fase 1 exige que la tribu ya viva sin él.
- **Embeddings** van en su propio hilo, en CPU (stack §2), y solo se consultan
  al construir el contexto de una petición. Nunca en el hilo de render ni en el
  del LLM.

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

Riesgos 1–6 vienen de concepto §14; 7–10 son técnicos de esta arquitectura.

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

**Existe hoy (Fase 0 en curso):**

- Paquete `tribal/` con `__init__.py` (versión), `__main__.py`, `cli.py`
  (subcomando `hello`) y `paths.py` (raíz y directorios derivados).
- Entry point de consola `tribal`, hatch `packages = ["tribal"]` y coverage
  `source = ["tribal"]` coherentes; `project_slug: tribal` en `project.yml`.
- Tests de humo: CLI, rutas e importación del paquete (7 tests).
- Puerta del arnés en verde (`harness gate` → `ENTORNO LISTO`).

**No existe todavía (y este documento no implementa):**

- Motor de reglas, individuos, instinto, saliencia (`tribal/core/`,
  `tribal/agents/`): CORE-001 y siguientes.
- Persistencia SQLite y esquema de stack §5 (`tribal/store/`).
- Capa LLM: cola, cliente HTTP de Ollama, esquema JSON, selección por saliencia
  (`tribal/llm/`). Nada de esto se usa hasta Fase 2; el diseño existe para que
  Fase 0–1 no lo necesite. El id que usa el código es `tribal-llm` (Modelfile
  `FROM qwen2.5:3b-instruct-q8_0` con `num_ctx 8192`; el base es solo el
  `FROM`, no el id del cliente); el propio `tribal-llm` vive en el almacén de
  Ollama, fuera del repo.
- Render Pygame y telemetría (`tribal/ui/`). `pygame-ce` **no** está declarado
  en `pyproject.toml` todavía: se añade en CORE-001.
- Grafo de cultura (`tribal/culture/`) y export a Obsidian (`tribal/store/export.py`).
- Índice RAG del código de producto: `agents/tools/rag_tool.py` sigue apuntando
  a `app`; hasta que se corrija (feature aparte), `make index-rag` no indexa
  `tribal/`.

### 9.1 Qué ramas avanza F1 y con qué prácticas

La puerta F1→F2 de `concepto.md` §15 pide descubrir sin LLM algo más allá del
primer paso forzado y que la proporción divergente reaccione a la crisis. Esta
fase cubre la primera mitad —el material—: cada rama avanza porque la tribu
**hace** algo, no porque el motor premie un rasgo.

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

Lo que esta fase **no** hace es medir la puerta completa: la proporción de
divergentes que reacciona a la crisis es de DIVERGENCIA-002/EMER-001, y el
`pct_fuera_arbol` de `objetivo.md` §3.2 (por encima del 50 %) es de Fase 3.

---

## 10. Referencias

- `vault/01_PROYECTO/objetivo.md` — problema, criterio de hecho, KPI (§3.2).
- `vault/01_PROYECTO/concepto.md` — §4 bucle, §8b emergencia, §10/10b LLM,
  §11 arquitectura, §14 riesgos, §16 decisiones abiertas.
- `vault/01_PROYECTO/stack-tecnologico.md` — §2 hardware, §3 datos, §5 esquema,
  §8 herramientas y concurrencia del LLM.
