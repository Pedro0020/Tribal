# 🧰 Stack tecnológico — La Tribu

> Documento técnico de referencia. Estado: **consensuado, pendiente de implementar**.
> Última revisión: 2026-11-17.

---

## 1. Resumen del stack

| Área | Elección |
|---|---|
| Lenguaje | **Python** |
| Visualización 2D | **Pygame**, mapa top-down, **pixel art** |
| Datos | **SQLite** (con columnas JSON) + grafo en dos tablas + export a Markdown |
| LLM local (Fase 2) | **Ollama** (`tribal-llm`, base qwen2.5-3B Q8_0, ctx 8192) + JSON schema · API local `127.0.0.1:11434` |
| Embeddings (Fase 2–3) | **Qwen3-Embedding-0.6B** (o embeddinggemma-2) |
| Grafo de cultura en vivo (Fase 3) | Pantalla web con **D3.js** (opcional) |
| Desarrollo | **MeshHarmes** como esqueleto (AGENTS.md, backlog por fases) |

---

## 2. Hardware y viabilidad

| Recurso | Dato | Implicación |
|---|---|---|
| CPU | i7-9750H (6 núcleos / 12 hilos) | Sobra para simulación + lógica |
| RAM | 15.85 GB total, **~6.9 GB disponibles** | El modelo debe caber en VRAM; poco margen para procesos extra |
| GPU | RTX 2060 **6 GB** VRAM (~5.8 libres) | Modelos **3B–4B** cómodos; 9B cuantizado "justito" |

**El cuello de botella real es la inferencia del LLM, no la CPU ni la memoria de la simulación.** Todo el diseño se apoya en esto.

### Modelos recomendados (pequeños, en VRAM)
| Modelo | Cuantización | VRAM aprox. | Uso |
|---|---|---|---|
| Qwen2.5-3B-Instruct | Q8_0 | ~4.3 GB | Todoterreno, buen español |
| Llama-3.2-3B-Instruct | Q8_0 | ~4.4 GB | Muy rápido |
| gemma-3-4b-it | Q6_K | ~5.0 GB | Más creativo (narraciones) |
| Qwen2.5-1.5B / Qwen3.5-2B | Q8_0 | ~2.5–3 GB | Máxima velocidad |
| **Qwen3-Embedding-0.6B** | Q8_0 / AWQ | ~2 / 1.7 GB | Embeddings para memoria |
| **embeddinggemma-2** | Q8_0 | ~1.7 GB | Alternativa de embeddings |

> Los `estimated_tps` de las herramientas suelen ser optimistas; resta 30–50% en carga real.

### ⚠️ Co-residencia LLM + embeddings (validar antes de Fase 2)

El diseño asume tener **LLM + modelo de embeddings a la vez**. Con 6 GB no cabe todo: Qwen 3B Q8 (~4.3 GB) + embedding 0.6B (~1.7 GB) + KV cache + sobrecarga CUDA ≈ **por encima de los 6 GB**.

**Mitigación pragmática (decisión por defecto):**
- **Embeddings en CPU.** El modelo 0.6B en CPU basta para recuperar memoria de forma ocasional (unos cientos de embeddings), y deja la VRAM entera para el LLM. Se paga latencia solo en la recuperación, no en la simulación.
- Si hiciera falta embeddings en GPU: bajar el LLM a **1.5B Q8** durante la recuperación, o cargar/descargar el embedding por lotes.

> Se valida con una prueba real **antes de Fase 2** (medir VRAM con LLM + embeddings cargados).

### Verificación pendiente
Confirmar la **disponibilidad real** de los modelos nombrados (p. ej. "Qwen3.5-2B") antes de Fase 2; los nombres de la tabla son orientativos.

### Motor LLM en Windows (Fase 2)

**A. Ollama (camino oficial).** Es un llama.cpp empaquetado: mismo GGUF, misma GPU, sin compilar nada y sin gestionar binarios a mano.

```powershell
ollama pull qwen2.5:3b-instruct-q8_0   # ~3.4 GB → C:\Users\pedro\.ollama\models
ollama ps                              # con el modelo cargado debe decir 100% GPU
```

Modelo propio con la configuración del proyecto (creado y verificado):

```
FROM qwen2.5:3b-instruct-q8_0
PARAMETER num_ctx 8192
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
```

```powershell
ollama create tribal-llm -f tribal.Modelfile
```

- Identificador del modelo en el código: **`tribal-llm`**.
- Medido en la RTX 2060 (6 GB): **66 tok/s** de generación, GPU al **95 %**, **3,6 GB** de VRAM con contexto 8192 (quedan ~2,3 GB libres).
- `keep_alive` por defecto 5 min: entre peticiones la GPU está al 0 % pero la VRAM sigue ocupada. Si molesta, `"keep_alive": "60s"` en la petición.
- API local: `http://127.0.0.1:11434` (`/api/chat`, `/v1/chat/completions`).
- Salida estructurada: campo **`format`** con un JSON schema (equivale a las gramáticas GBNF para este uso).
- El modelo vive en el almacén de Ollama, **no** en el repo. `models/` del proyecto queda para pruebas manuales y está ignorado por git.
- Si el servicio no está levantado: `ollama serve` (en Windows suele estar como app de bandeja).

**B. Binarios de `llama-server` (alternativa, control total).**
1. GitHub `ggml-org/llama.cpp`: los binarios van en el tag diario `b####`, no en `latest`.
   - `llama-b####-bin-win-cuda-12.4-x64.zip` (RTX 2060 = CUDA 12.x)
   - `cudart-llama-bin-win-cuda-12.4-x64.zip` (runtime CUDA, si no hay CUDA Toolkit)
2. Extraer a `C:\Users\pedro\llama.cpp\` y descargar el GGUF a `models/` (ignorado por git).
3. `llama-server.exe -m models\...q8_0.gguf -ngl 99 -c 8192 --port 8080`
4. La salida estructurada se pide con `response_format: {"type":"json_schema", ...}`.

**C. `llama-cpp-python` en proceso (último recurso).** Solo con wheels precompiladas (`--index https://abetlen.github.io/llama-cpp-python/whl/cu124`); si no hay, intenta compilar y requiere CMake + VS Build Tools. Evitarlo: es justo la fragilidad que A y B eliminan.

> **Decisión:** **A (Ollama)**. Misma interfaz HTTP que B, pero sin gestión de binarios ni versiones. El diseño de la simulación no cambia: el LLM nunca se llama desde el hilo de render (§8).

---

## 3. Decisión de datos: SQLite + JSON + grafo (por qué NO Mongo)

### Qué es flexible y qué es fijo
| Dato | ¿Emergente? | Modelo |
|---|---|---|
| Estado del mundo (posición, energía, salud, vínculos) | No | **Estructurado** (columnas) |
| Genoma / habilidades / personalidad | Parcialmente | **JSON** (columnas flexibles) |
| Cultura / conocimiento | **Sí** | **Grafo** (nodos + aristas) |
| Memoria episódica | Sí | **Documento flexible** (JSON/texto) |

SQLite cubre las cuatro casillas: relacional (tablas), flexible (JSON), grafo (dos tablas) y texto libre.

### Por qué no Mongo ahora
- Mongo es un **servidor aparte**; SQLite es **embebido** (un archivo, cero daemon).
- La parte verdaderamente emergente es la **cultura**, y eso es un **grafo**, no documentos.
- El **libre albedrío** de los agentes es divergencia de *contenido y decisiones*, no de *tipos de datos*; el LLM necesita una **interfaz JSON conocida** para operar con coherencia.

### Cuándo sí Mongo
Equipo/servidor, alta concurrencia de escritura, documentos heterogéneos a gran escala, escalado horizontal. **Nada de eso aplica** a un proyecto local de una máquina.

### Puerta abierta sin pagar ahora
Se usa una **capa de acceso a datos fina** (interfaz): si algún día se necesitara Mongo/Neo4j, se cambia solo esa capa. Migrar es trivial.

---

## 4. Decisión de lenguaje: Python (por qué NO Rust)

### Rust es bueno, pero no para *este* cuello de botella
- La parte lenta es el **LLM**, que ya es **C++/CUDA** (llama.cpp). Rust no acelera ni un token.
- La simulación (8–15 agentes por turno) es **trivial** para Python (miles de FPS). Optimizarla es optimizar lo que no está lento.
- **Memoria**: Rust es más eficiente, pero ahorra ~100 MB de intérprete frente a los **5 GB del LLM** (idénticos en ambos). Irrelevante.
- El ecosistema **LLM local es Python-first** (llama-cpp-python, gramáticas, embeddings, structured output). En Rust se va contracorriente.
- Nuestro propio stack (dskit/MeshHarmes) es **Python**, con `uv` ya montado.

### Cuándo sí Rust
Miles/millones de agentes en tiempo real, binario único distribuible, o aprender Rust por gusto. Si el motor de reglas llegara a ser el límite, se reescribe **ese módulo** en Rust (PyO3/WASM).

### Python vs JS
- **Python** gana: ecosistema LLM + iteración rápida.
- **JS** ganaría: grafo de cultura en vivo (D3).
- Decisión: **Python como núcleo**; el grafo bonito se hace con una pantalla web encima cuando toque (Fase 3).

### Por qué no Docker ahora
Docker resuelve *empaquetado*, no *modelo de datos*. En Windows corre un Linux en WSL2 (2–4 GB de RAM) + CUDA passthrough doloroso. Se añadirá **cuando toque distribuir**, no antes.

---

## 5. Modelo de datos concreto (SQLite)

```sql
-- Estado del mundo y los individuos
individuos(id, nombre, edad, sexo, energia, salud, sed,
           genoma JSON, habilidades JSON, personalidad JSON,
           divergencia REAL, saliencia REAL, estado)
relaciones(id_a, id_b, tipo, intensidad)
recursos(id, tipo, x, y, cantidad)
mundo(tick, estacion, clima JSON)

-- Cultura como grafo
nodos(id, tipo, titulo, contenido, popularidad, estado)
aristas(id_origen, id_destino, tipo_relacion, peso)

-- Memoria
recuerdos(id_individuo, tipo, texto, embedding BLOB, tick, saliencia)

-- Narración y observación
diario(tick, tipo_evento, narracion)
telemetria(tick, poblacion, n_divergentes, n_conformistas, n_nodos, n_aristas)
```

- **`tick`** = nº de frame desde el inicio; el tiempo continuo se deriva (`seg_simulado = tick / fps * velocidad_reloj`). La `telemetria` muestrea por **intervalo**, no por frame.
- **Flexible donde importa**: `genoma`, `habilidades`, `personalidad`, `contenido` y `texto` son JSON/texto libre.
- **Export a Obsidian**: `nodos` + `aristas` se vuelcan a `.md` con `[[wikilinks]]` para ver la cultura en la vista de grafo de Obsidian.

---

## 6. Memoria y conocimiento como grafo (vault de Obsidian + graphify)

Dos usos separados:

1. **Runtime**: grafo en memoria (nodos + aristas) que el LLM **recorre** para cargar solo lo relevante (GraphRAG ligero). La cultura crece/muta como el grafo.
2. **Observación**: export del grafo a **Markdown con `[[wikilinks]]`** y se abre en un **vault de Obsidian** para verlo con **graphify** (la vista de grafo). Patrón tomado de MeshHarmes: un `vault/` con carpeta de visualizaciones (`04_VISUALIZACIONES/`).

> Hay **dos vaults distintos** (no confundir):
> - **Vault de desarrollo** (MeshHarmes): el conocimiento del *proyecto* — visión, decisiones, roadmap. Es donde viven estos `.md`.
> - **Vault de la tribu** (runtime): la *cultura simulada* exportada como notas. Ahí ves "la mente de la tribu" crecer con graphify.
>
> Y un tercer modo de verlo: el **grafo vivo** (D3) dentro de la propia app, en tiempo real.

> Feature estrella (Fase 3): ver la cultura de la tribu nacer, conectarse y a veces apagarse, como una constelación que se enciende sola.

> **Ver vs. consultar la cultura.** La vista de grafo (Obsidian/D3) deja **ver** la constelación; lo que completa la herramienta es **consultarla**: preguntar al grafo ("¿qué ruta llevó al fuego?", "¿qué nodos murieron con el anciano?"). Eso se hace con una **capa de consulta** (camino/explicación sobre `nodos`+`aristas`, Fase 3), y es lo que convierte el grafo de *bonito* a *útil para entender la emergencia*. **graphify sirve a los dos vaults**: el **de desarrollo** (consultar los `.md` del propio proyecto) y el **de la tribu** (ver + consultar la cultura simulada).

---

## 7. ¿Necesitamos data science?

No un *proyecto* de DS; solo **2–3 técnicas ligeras**:

| Técnica | Para qué | Cuándo |
|---|---|---|
| **Embeddings + similitud** | Recuperar recuerdos/cultura relevantes para el prompt | Fase 2–3 |
| **Clustering** | Agrupar individuos en roles/especies | Fase 1–2 (opcional) |
| **Estadística descriptiva** | Panel de observación / telemetría | Fase 0+ (opcional) |

Todo con los modelos de embedding ya disponibles (Qwen3-Embedding-0.6B, embeddinggemma-2).

---

## 8. Herramientas por capas

### Runtime (corazón)
| Herramienta | Veredicto |
|---|---|
| llama.cpp / llama-cpp-python + gramáticas GBNF | **Imprescindible** |
| Gramáticas / JSON schema (salida válida) | **Imprescindible** |
| SQLite | **Muy recomendable** |
| Pydantic (modelos de datos) | **Muy recomendable** |
| NetworkX (o dict de nodos/aristas) | **Recomendable** |
| Qwen3-Embedding-0.6B / embeddinggemma-2 | **Recomendable** (Fase 2+) |
| LightRAG | Opcional (o a mano, que es simple) |
| mem0 | Opcional (quizá más de lo necesario) |

**Evitar (overkill)**: Neo4j, vLLM, GraphRAG completo de Microsoft, Pinecone/Weaviate/Qdrant.

**Gramática y espontaneidad (concepto §8c):** la gramática fija el **esqueleto** (schema JSON + nombres de acción del vocabulario finito de acciones, concepto §7) y deja **libres los campos de texto** (`razon`, `dialogo`, contenido de un descubrimiento propuesto). Así el LLM no se sale del formato, pero sí sorprende en *qué* propone. Constriñe coherencia, no dirección.

### Concurrencia del LLM (60 fps sin bloqueo)

Con Ollama (§2), el LLM vive en un **proceso aparte**: la simulación nunca lo bloquea y, si el modelo se cae, el mundo sigue. El patrón es siempre el mismo:

1. **Un hilo de cliente dedicado** que consume una cola (`queue.Queue`) y habla HTTP con Ollama (`127.0.0.1:11434`). El bucle de Pygame **encola** la petición y, en frames posteriores, **pregunta** por el resultado sin esperar. Timeout corto: si no llega, el agente sigue por instinto y la decisión se descarta.
2. **Un hilo aparte para embeddings en CPU** (§2), independiente del hilo del LLM en GPU.
3. Si algún día se usa `llama-cpp-python` en proceso (ruta C), ese objeto **no es thread-safe**: solo un hilo de inferencia, jamás dos a la vez.

> Regla: **el LLM nunca se llama desde el hilo de render.** Se encola, y el resultado se aplica cuando llega — o no se aplica.

### Presupuesto de GPU en runtime (no saturar la gráfica)

Objetivo: la GPU trabaja en **ráfagas cortas**, con un ciclo de trabajo (duty cycle) ≤ 30 % y temperatura holgada. Medido en esta RTX 2060: una decisión de 62 tokens ocupa la GPU **1,5 s**; con 32 tokens, ~0,7 s.

| Regla | Valor | Por qué |
|---|---|---|
| `num_predict` por decisión | **≤ 32 tokens** | Una acción + razón cabe de sobra; 62 → 32 reduce la carga a la mitad |
| Inferencias simultáneas | **1** (semáforo) | Ollama ya serializa; el cliente no debe encolar 6 a la vez |
| Enfriamiento por agente | **≥ 8 s** entre consultas del mismo individuo | El resto del tiempo va por instinto (§10b) |
| Tope global | **≤ 15 decisiones/minuto** (token bucket) | 15 × 0,7 s ≈ 10,5 s/min → **~18 % de ciclo de trabajo** |
| `keep_alive` | **15 min** en sesión; `ollama stop tribal-llm` al cerrar | Sin recargas de 2–4 s; VRAM libre al terminar |
| Freno térmico | si `temp ≥ 78 °C` o `util ≥ 95 %` durante >60 s → parar de encolar | Protección de salud, no de rendimiento |

`nvidia-smi --query-gpu=utilization.gpu,temperature.gpu,power.draw --format=csv,noheader` es la fuente para el freno.

> Resultado esperado: ráfagas de ~0,7 s separadas por varios segundos, ~20 % de uso medio, 50–55 °C. La simulación sigue a 60 fps porque el render es CPU/Pygame, no el LLM.

### Observación
| Herramienta | Veredicto |
|---|---|
| D3.js / vis.js / Cytoscape.js (grafo vivo) | **Muy recomendable** (Fase 3) |
| Obsidian + Graph view (espejo) | **Recomendable** (Fase 3) |
| Streamlit / Gradio (telemetría) | Opcional |
| Loguru / structlog | **Recomendable** |

> **Puente Python → D3 (grafo vivo):** D3 vive en el navegador; Python no le empuja datos por sí solo. Fase 3 añade un **mini-servidor local (FastAPI + WebSocket)** que sirve el JSON del grafo en cada cambio. Es la única pieza nueva real de Fase 3.

### Desarrollo
| Herramienta | Veredicto |
|---|---|
| MeshHarmes (arnés) | **Usar como esqueleto** |
| uv | **Imprescindible** |
| ruff + mypy + pytest + pre-commit | **Recomendable** (MeshHarmes los trae) |
| vault/ de Obsidian (los .md de diseño) | Ya lo hacemos |

---

## 9. Repos de referencia

| Repo | Qué es | Uso |
|---|---|---|
| `cacelass/MeshHarmes` (también `aiagents`) | Arnés de agentes: AGENTS.md, puerta `init.sh`, backlog, **vault Obsidian con graphify** (`04_VISUALIZACIONES/`), 24 agentes deterministas | **Esqueleto de construcción** |
| `cacelass/dskit` | Plantilla copier para Data Science (uv + Sphinx) | **Descartable** (es para notebooks/ML, no para simulación) |

> Ojo con los dos significados de "agente": los **agentes de build** (escriben código, MeshHarmes) vs. los **agentes de la tribu** (individuos simulados, el runtime).

> **Estado real de MeshHarmes (verificado 2026-11-17):** es **Python 3.12+** (no Java), con `app/` vacío, `agents/` (24 agentes de build), `harness/` (backlog + progress), `vault/` y `AGENTS.md` + `init.sh`. Hoy está **citado pero no aplicado** — `Pecera/` aún no lo tiene scaffolded. Scaffoldearlo es el **primer paso de Fase 0**. (El `demo/` local es un arnés **Java** aparte, no MeshHarmes.)

---

## 10. Stack por fases

| Fase | Qué se añade |
|---|---|
| **Fase 0** | Python + Pygame + Pydantic + config/semilla (reproducibilidad) + scaffold MeshHarmes + (opcional) SQLite |
| **Fase 1** | Genoma + árbol de conocimiento + clustering |
| **Fase 2** | Ollama + JSON schema + embeddings en CPU + grafo en memoria |
| **Fase 3** | Memoria colectiva + export a Obsidian + grafo vivo (D3) + telemetría |

> **Reproducibilidad:** una semilla (`seed`) + un archivo de configuración (parámetros de la simulación) permiten re-ver una run interesante y comparar variantes. Barato y esencial para "observar" en serio.

---

## 11. Principios de diseño

1. **Complejidad cuando la ganes**, no "por si acaso" (evitamos Mongo, Docker, Rust y Neo4j hasta que aporten algo concreto).
2. **Capas desacopladas**: motor de reglas / genética / memoria / LLM son piezas intercambiables.
3. **No cerrar puertas**: capa de datos abstracta + módulos aislados → migrar o reescribir es barato.
4. **El cuello de botella manda**: se optimiza para la inferencia del LLM, no para la CPU.
5. **La magia es la sorpresa de la dinámica, no el contenido** (concepto §8c): el LLM hace *legible* la emergencia, no la fabrica. Se constriñe la coherencia, nunca la dirección.

---

## 12. Ideas diferidas (futuras versiones)

- **Enrutado de modelos (local + nube gratuita)**: usar un modelo de nube gratis (Groq / Google Gemini / OpenRouter) para las decisiones importantes (narrar hitos, inventar, nombrar), con **fallback al modelo local**. Diferido; por ahora, todo local.
- **Intervención del usuario**: por ahora solo observar; poder intervenir (alimentar, proteger, sembrar) queda para otra ocasión.
- **Docker**: empaquetar/distribuir el proyecto cuando haga falta (no antes).
- **Límite de potencia de la GPU** (`nvidia-smi -pl 130`, requiere admin): baja de 160 W a 130 W con ~5–8 % menos de velocidad y más margen térmico. Sugerido, no aplicado. El presupuesto de §8 ya mantiene el ciclo de trabajo en ~18 %, así que no es necesario por ahora.
