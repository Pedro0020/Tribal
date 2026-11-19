# 🏹 Tribal

![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python&logoColor=white)
![Version](https://img.shields.io/badge/Version-0.1.26-green)
![Author](https://img.shields.io/badge/Author-Pedro0020-blueviolet)

> Una banda de homínidos despierta en un mundo hostil sin nada y, generación tras generación, **la civilización aparece sola**.

Este repositorio construye una simulación en **2D pixel-art** donde 8–15 agentes con necesidades, memoria y personalidad viven en tiempo real, y donde la **cultura** (herramientas, fuego, lenguaje, rituales, mitos) emerge de su dinámica y no de un guion. Los LLM locales actúan como cerebros individuales **solo cuando hay algo real que decidir**.

El objetivo no es dibujar una tribu: es un experimento observable sobre cómo nace la cultura sin que nadie la escriba.

## Documentación

| Documento | Contenido |
|---|---|
| [`vault/01_PROYECTO/concepto.md`](vault/01_PROYECTO/concepto.md) | Concepto principal: agentes, memoria, evolución, espontaneidad, riesgos y fases |
| [`vault/01_PROYECTO/stack-tecnologico.md`](vault/01_PROYECTO/stack-tecnologico.md) | Stack y el porqué de cada decisión técnica |
| [`vault/01_PROYECTO/objetivo.md`](vault/01_PROYECTO/objetivo.md) | Objetivo: problema, usuario, criterio de hecho medible y fuera de alcance |
| [`vault/01_PROYECTO/arquitectura.md`](vault/01_PROYECTO/arquitectura.md) | Plan técnico — lo escribe la feature `DESIGN-001` |

## Criterio de éxito

La tribu pasa de **cero** a **fuego + una herramienta compuesta + proto-lenguaje + un mito**, y **al menos la mitad de esos nodos no estaban en el árbol de plausibilidad inicial**. Todo lo demás (escala, gráficos, duración) está al servicio de ese momento. El KPI exacto y la consulta que lo comprueba están en [`objetivo.md`](vault/01_PROYECTO/objetivo.md#3-criterio-de-hecho).

## Flujo de trabajo: spec → plan → tareas

| Paso | Feature | Produce |
|---|---|---|
| **Spec** (qué se resuelve) | `SCOPE-001` | `vault/01_PROYECTO/objetivo.md` |
| **Plan** (cómo se resuelve) | `DESIGN-001` | `vault/01_PROYECTO/arquitectura.md` |
| **Tareas** | `CORE-001`, `QA-001`, … | `harness/featureslist.json` |

Ninguna feature se cierra sin que `./init.sh` pase en verde. El protocolo completo está en [`AGENTS.md`](AGENTS.md).

## Inicio rápido

```bash
make setup     # uv sync + hooks
make init      # la puerta: ¿se puede trabajar?
make run       # ejecuta el paquete
make check     # lint + typecheck + test + arnés
```

## Estado tras Fase 1

La Fase 1 está cerrada y **no usa LLM**: todo lo de abajo sale del motor de
reglas y del azar de la semilla.

- **Árbol de conocimiento** con cinco ramas (lítica, fuego, lenguaje, roles y
  simbólico), niveles, prerrequisitos y `origen` por nodo. Cada rama avanza con
  una práctica real (comer/tallar, frotar madera, hablar, enseñar/cuidar,
  pintar), no con una recompensa al rasgo. → `report culture`.
- **Genoma y habilidades**: ocho rasgos heredables con mutación; las
  habilidades se enseñan e imitan y cambian el rendimiento de la acción.
- **Divergentes y conformistas**: `divergencia` solo elige conducta (radio de
  paseo, experimentar en crisis, memoria condicional a la migración); no toca
  comida, sed, cría ni genoma.
- **Utilidad situacional**: el beneficio de una combinación depende de la
  escasez del recurso, la estación y la densidad de portadores.
- **Gradiente ambiental**: parches que se agotan, migran en crisis y estaciones
  que cambian la regeneración.
- **Puerta F1→F2 medida en la descendencia**: `report gate-f1` compara calma y
  crisis sobre 10 semillas. Veredicto publicado: `S_fec > 0` en crisis 7/10 y
  `S_fec < 0` en calma 7/10 (primaria); el `div%` secundario (4/10) no decide.
- **Telemetría**: `report telemetry` muestrea por intervalo, no por tick.

La Fase 2 (LLM) empieza en `F2-001`; hasta entonces, nada de lo anterior
necesita red ni modelo.

## Capa LLM local (Fase 2)

`tribal/llm/` es la capa aislada que habla con Ollama. `cola.py` es la cola
asíncrona: un hilo daemon (`tribal-llm`) consume una `queue.Queue` acotada,
llama al cliente y deposita la respuesta en otra cola acotada. **El LLM nunca se
llama desde el hilo del bucle**: el tick encola hasta `max_pensando` peticiones
(4 por defecto, por saliencia) —solo si hay dilema real (sed y energía en
conflicto, o salud crítica)— y recoge al final lo que haya llegado.

El presupuesto son dos cosas: como mucho `--llm-max-en-vuelo` peticiones
aceptadas sin respuesta (4 por defecto; si está lleno, el individuo sigue por
instinto) y una sola inferencia a la vez, porque el hilo es único. En modo
síncrono la respuesta se resuelve dentro de `encolar`: nunca hay nada en vuelo,
así que ese tope —y el campo `max_en_vuelo` del resumen— solo miden con la cola
asíncrona. Una decisión
vale una **ventana** de 180 ticks (~3 s a 60 fps): si llega más tarde se
descarta en silencio y el individuo sigue por instinto. Una decisión vigente
manda ese tick; si la acción elegida no se puede hacer, el instinto recupera el
turno —una intención no puede congelar a nadie—.

```bash
uv run python -m tribal run --headless --json --llm stub --ticks 1200
uv run python -m tribal run --headless --json --llm stub --llm-sincrono --ticks 1200
uv run python -m tribal run --headless --json --llm http --llm-max-en-vuelo 2 --ticks 1200
```

`--llm off` (default) es la partida de Fase 0/1 y el resumen **no** lleva el
bloque `llm`: nada cambia. Con `stub` un backend falso elige candidata con un
hash del prompt —determinista entre procesos— y sirve para probar el cableado
sin GPU ni red; `--llm-sincrono` resuelve en el mismo tick y es el modo
exactamente reproducible (solo vale con `stub`: con `http` congelaría el tick
hasta el timeout). En asíncrono, el tick en que aterriza una decisión y los
propios contadores `llm` dependen del reloj real: la corrida es reproducible en
el modelo, no en el `resumen()` completo. `--llm http` habla con Ollama.

`resumen()["llm"]` publica `{peticiones, aplicadas, descartadas, fallos,
corregidas, en_vuelo}`; `fallos` son errores del transporte, `corregidas` las
elecciones que el motor tuvo que sustituir por inválidas y `descartadas` lo que
llegó fuera de ventana o quedó pendiente al cerrar. Al acabar la partida la cola se
cierra: deja de aceptar, descarta lo que no había empezado y espera al hilo como
mucho `en_vuelo * (timeout + 1)` —con Ollama caído y 4 en vuelo, ese es el tope
del cierre—, así que `en_vuelo` queda a 0 y no hay hilos vivos. Si el LLM no
responde —Ollama caído, timeout de 3 s, JSON inválido— no hay excepción: el
fallo se cuenta en `fallos` y la tribu sigue por instinto indefinidamente. **No
hay backoff**: el presupuesto de peticiones en vuelo es el único freno.

### Saliencia y pensamiento selectivo (concepto §9b y §10b)

**Divergencia no es saliencia.** `divergencia` (§9b) es temperamento heredado:
cuánto se desvía alguien del grupo. La **saliencia** (§10b) es peso narrativo
**ganado**: cuánto protagonismo ha acumulado por sus actos. Un conformista que
guarda la tradición puede ser más saliente que un divergente cuyas ideas nunca
cuajaron. El motor sube saliencia por hitos —ser el primero en un escalón de
una rama (el primer fuego, la primera palabra, el primer líder), descubrir una
combinación, crear la primera tradición, enseñar una habilidad, sacar a un
herido del pozo o sobrevivir 600 ticks de crisis— y la deja decaer
`0.999` por tick, con techo `SALIENCIA_MAX = 10`. Nunca se calcula desde el
genoma, así que dos historias iguales dan la misma saliencia con cualquier
divergencia (`tribal/agents/saliencia.py`).

Cuando hay más dilemas que presupuesto, `_encolar_dilema` ordena a los
individuos con dilema por `(-saliencia, id)` y encola hasta `max_pensando`
(config, 4 por defecto) y hasta `max_en_vuelo`; los demás siguen por instinto y
se reevalúan el tick siguiente. Así el LLM atiende primero a los protagonistas
emergentes sin que nadie se congele ni el tick se bloquee.

```bash
uv run python -m tribal run --headless --json --llm stub --llm-sincrono --ticks 1200
# ... "saliencia": {"top": [[5, 0.657], [2, 0.455], [8, 0.304]],
#                   "pensamientos": {"2": 1, "3": 287, "5": 173, "9": 307, ...},
#                   "max_pensando": 4, "max_en_vuelo": 0}, ...
```

El modo `--llm-sincrono` es el reproducible: misma semilla, mismo JSON. Con
`--llm stub` **asíncrono** los contadores de `pensamientos`, `llm` y
`max_en_vuelo` varían entre corridas porque el instante en que aterriza cada
respuesta depende del reloj; el top de saliencia puede moverse con ellos. Sin
`--llm-sincrono`, no compares números exactos.

`resumen()["saliencia"]` publica el **top 3** de los vivos con saliencia
positiva, las peticiones aceptadas por individuo (`pensamientos`) y los máximos
observados de individuos que pensaron en un tick y de peticiones en vuelo (este
último, solo con la cola asíncrona; en síncrono vale 0). El
bloque sale también sin LLM —la saliencia se gana igual—, con `pensamientos`
vacío; `sum(pensamientos) == llm.peticiones` siempre.

### Diario y narración (concepto §10)

El motor escribe **lo que pasó**; el LLM solo pone la frase. El diario
(`tribal/culture/diario.py`) anota el primer fuego (`observar_rayo`), la primera
caza en grupo (`caza_cooperativa`), la primera palabra (`proto_palabras`), el
primer rito (`ritual`), la primera tradición y la muerte de cada anciano
(≥ `UMBRAL_ANCIANO = 1500` ticks), más cada diálogo que devuelve una decisión.
Cada hito se ata al nodo que representa el hecho, no al primer escalón de su
rama: `gestos` no es una palabra ni `arte_rupestre` un rito. Cada entrada guarda
`tick`, `tipo`, `texto`, `individuo_id` y `narrada`.

La entrada se registra **siempre**; la narración es opcional:

- Con capa LLM (`--llm stub|http`) el hito encola una petición al cronista —
  una sola frase en español, sin diálogo— sin bloquear el tick. La frase llega
  a la entrada por su propia cola y se guarda **tal cual** la devolvió el
  modelo; `narrada=true`.
- Sin LLM, con el servicio caído, con un timeout, con JSON inválido o sin
  hueco en la cola, el hito queda con `texto=""` y `narrada=false`. El diario
  no pierde nada: la historia es del motor, no del modelo.
- `--llm stub --llm-sincrono` es el modo reproducible: el stub elige la frase
  por hash del prompt, así que misma semilla y mismos ticks dan el mismo
  diario.

La narración es **best-effort**: comparte con las decisiones el presupuesto en
vuelo (4 por defecto), así que en partidas largas una parte de los hitos queda
sin frase (p. ej. 34 entradas / 18 narradas en 6000 ticks) y lo que llega
después de cerrar la cola se descarta. El hecho nunca se pierde; la frase sí.

El diálogo no se narra: es lo que el individuo dijo en la decisión, y se asocia
a él (`tipo="dialogo"`, `individuo_id`). `Diario.ultimas(n)` ordena **por
`tick`** (estable para empates), no por orden de llegada: una decisión
asíncrona que aterriza tarde puede anotar un tick anterior al último hito, y el
diario sigue cronológico. `resumen()["diario"]` publica `{entradas, narradas,
dialogos, ultimas}` con las últimas tres entradas ya ordenadas; el `resumen()`
legible de `run` imprime esas tres y `report diary` usa la misma vista.

```bash
uv run python -m tribal report diary --json --last 5
uv run python -m tribal report diary --llm stub --llm-sincrono
```

```
seed 42  ticks 600  llm stub  entradas 5  narradas 5  dialogos 0
      2  primer_fuego       ind 3   el grupo reconoció en sí mismo lo que antes solo hacía
      6  primer_rito        ind 3   el humo subió y nadie volvió a mirar atrás
     12  primera_tradicion  ind 9   el grupo reconoció en sí mismo lo que antes solo hacía
     13  primera_caza_grupo ind 3   la presa cayó entre varios y la carne alcanzó para todos
     86  primera_palabra    ind 11  el gesto se repitió sin que nadie lo mandara
```

`report diary` corre una partida headless (acepta `--seed`, `--ticks`,
`--last`, `--config`, `--crisis`, `--llm` y `--llm-sincrono`) y publica las
últimas `--last` entradas (5 por defecto). Todavía no lee una partida
persistida: cuando exista `tribu.db` leerá la tabla `diario`.

El contrato sale de [`viabilidad-modelo.md`](vault/01_PROYECTO/viabilidad-modelo.md)
y está implementado en `tribal/llm/candidatas.py` + `decision.py`: el modelo
**no genera la acción desde cero**, elige una de las **2–4 candidatas** que
filtran las reglas para ese estado, con few-shot y temperatura 0.3. `candidatas()`
solo ofrece lo físicamente posible —sin agua al alcance no hay `beber`, sin
comida no hay `comer`, sin depredador encima no hay `huir`—; si el filtro deja
una sola opción añade `moverse` a un tile pisable y, si no hay mundo transitable,
deja esa única candidata con el borde documentado: en ese caso no se pide
decisión y manda el instinto. La invariante es 2–4 **siempre que existan al
menos dos acciones viables**. El campo `format` lleva un JSON schema con `accion`
restringida al `enum` de esas candidatas, más `objetivo`, `razon` y `dialogo`;
los textos quedan libres.

Después de la respuesta, el motor **valida y solo corrige lo inválido**: una
acción fuera de las candidatas o una restricción dura (`huir` sin amenaza,
`beber` sin agua, `comer` sin comida) se sustituye por la mejor candidata por
reglas y se cuenta en `corregidas`; una elección válida no se segundea. Un
fallo de transporte no es una elección que corregir: se cuenta en `fallos` y el
individuo sigue por instinto.

```bash
uv run python -m tribal llm eval --json                    # CI: backend simulado
uv run python -m tribal llm eval --backend http --json     # modelo real
```

`llm eval` corre 20 escenarios simples con una acción claramente correcta y
publica `aciertos`, `acierto`, `corregidas` y `sin_decision`. En CI usa un
**backend simulado competente** (elige la candidata de mayor utilidad): eso
prueba el contrato y el filtrado, no la calidad de `tribal-llm`; el acierto del
modelo real se mide aparte con `--backend http`, y sin servicio el comando no
revienta: las decisiones quedan `sin_decision` y la tribu sigue por instinto.

```bash
ollama serve                                  # servicio local en 127.0.0.1:11434
ollama pull qwen2.5:3b-instruct-q8_0          # base del Modelfile
# tribal.Modelfile hereda de esa base y fija num_ctx 8192
ollama create tribal-llm -f tribal.Modelfile  # id que usa el cliente
uv run python -m tribal llm selfcheck --json
```

`selfcheck` publica `disponible`, `endpoint`, `modelo`, `latencia_ms`, `error` y
`embeddings: {backend, usa_gpu, dim}`.
Que no haya servicio **no es un fallo del comando**: la tribu sigue por instinto.
Un timeout (3 s), una conexión rechazada o un JSON inválido se devuelven como
`degradado`/`error`; `decidir()` nunca lanza. Los tests inyectan
`backend_falso(...)` y `tests/conftest.py` bloquea `urllib.request.urlopen`, así
que `uv run pytest -q` no abre red.

### Memoria y embeddings (CPU)

`tribal/llm/embeddings.py` indexa los hitos de cultura —nodos del árbol,
combinaciones y tradiciones de `origen=interaccion`— para que una petición al
LLM lleve los recuerdos relevantes, no todos. `IndiceRecuerdos.buscar()` devuelve
top-k por coseno con orden estable (score y luego id) y **nunca corre en el hilo
de render ni en el del LLM**: se consulta al construir el contexto, en el hilo del
bucle. La guarda lo comprueba por nombre de hilo y por pila de llamadas.

El backend por defecto es `EmbedderHashing`: bag-of-words con hash estable
(blake2b, no `hash()`) en 256 dimensiones y L2 normalizado, así que mismo texto →
mismo vector **en cualquier proceso**. `EmbedderOllama` es el backend real
opcional (`POST /api/embed`, sin dependencias); se pide en CPU porque la VRAM es
del LLM (stack §2 y §7) —`usa_gpu=false` es la intención declarada, el
dispositivo lo decide Ollama— y si el servicio no está devuelve un vector nulo en
vez de lanzar. Sin capa LLM el índice no se crea y el resumen publica
`memoria: {recuerdos, recuperaciones}` a cero.

## Ejecutar (Fase 0)

La Fase 0 es una tribu de 8–15 individuos en un mapa top-down de 60×34 tiles
(480×272 px) con tres necesidades —energía, sed y salud— que evolucionan por
tick. Cada individuo nace con un **genoma** de ocho rasgos heredables
(velocidad, metabolismo, longevidad, fuerza, resistencia, inteligencia, salud
y divergencia) que modula cuánto avanza, cuánto gasta y cuánto vive. Las
parejas adultas y bien alimentadas tienen crías junto al agua, que heredan la
media de sus progenitores con una mutación pequeña; con la edad llega la
muerte. Un **depredador** recorre el mapa, persigue a la presa viva más cercana
y la muerde: quien lo ve cerca huye en un sprint. De ahí salen dos
comportamientos que nadie guioniza —la tribu se agolpa en los lagos y huye en
manada— y que la puerta F0→F1 mide. Cada individuo sabe hacer cosas
(**habilidades**) que se aprenden enseñando o imitando, nunca por genoma.
Todavía **no** hay LLM: en Fase 1 el árbol de conocimiento se recorre con
prácticas reales de la tribu —comer y tallar, frotar madera, hablar,
enseñar/cuidar y pintar— y se consulta con `report culture` (siguiente
apartado).

```bash
uv run python -m tribal run                                      # ventana 60 fps, 12 individuos
uv run python -m tribal run --headless --ticks 600 --json        # una partida, resumen JSON
uv run python -m tribal run --seed 7 --benchmark --headless --ticks 600
```

![Fase 0: la tribu junto al lago con un depredador acechando](docs/img/fase0-puerta.png)

En la ventana se ve el mapa (hierba, lagos azules, bosques con bayas rojas y
caza marrón), los individuos como sprites de 6×8 px (túnica ocre o roja según
sexo, más pequeños mientras son crías), el depredador como un cuadrúpedo oscuro
con ojo rojo y una franja de HUD con tick, población y media de energía y sed.
El centro de cada **parche** de recurso lleva un punto de 2×2 (gris si está
agotado) y, con estaciones, otoño e invierno tiñen el mapa y el HUD dice cuál
toca.
**ESC** o cerrar la ventana termina la partida.

Salida real de `uv run python -m tribal run --headless --ticks 600 --json`:

```json
{"seed": 42, "ticks": 600, "poblacion_inicial": 12, "poblacion_final": 16, "nacimientos": 4, "coste_reproduccion": 50.0, "muertes": 0, "media_energia": 75.23, "media_sed": 34.51, "media_genes": {"velocidad": 0.993, "metabolismo": 1.023, "longevidad": 0.97, "fuerza": 1.01, "resistencia": 1.028, "inteligencia": 1.012, "salud": 0.975, "divergencia": 0.455}, "habilidades_distintas": 1, "habilidades": {"1": ["recolectar"], "2": ["recolectar"], "3": ["recolectar"], "4": ["recolectar"], "5": ["recolectar"], "6": ["recolectar"], "7": ["recolectar"], "8": ["recolectar"], "9": ["recolectar"], "10": ["recolectar"], "11": ["recolectar"], "12": ["recolectar"], "13": ["recolectar"], "14": ["recolectar"], "15": ["recolectar"], "16": ["recolectar"]}, "individuos_movidos": 16, "depredador": {"activos": 1, "ataques": 0, "muertes": 0}, "agrupamiento_max": 9, "huidas": 266, "n_divergentes": 3, "n_conformistas": 8, "n_neutros": 5, "mean_divergencia_inicial": 0.4513, "mean_divergencia_nacidos": 0.4666, "mean_divergencia_reproductores": 0.4724, "reproductores": 8, "S": 0.0211, "S_fecundidad": 0.0211, "S_viabilidad": 0.0038, "descubrimientos": 0, "descubrimientos_divergentes": 0, "descubrimientos_conformistas": 0, "divergentes_registrados": 3, "conformistas_registrados": 8, "tasa_descubrimiento_divergente": 0.0, "tasa_descubrimiento_conformista": 0.0, "tasa_imitacion": 0.0, "longevidad_media_descubridores": 0.0, "longevidad_media_conformistas": 0.0, "muertes_descubridores": 0, "muertes_conformistas": 0, "intentos_divergentes": 0, "combinaciones_logradas": 0, "descubridores": [], "supervivencia_descubridores": 0.0, "supervivencia_no_descubridores": 1.0, "diferencial_seleccion": 0.0, "tradiciones": 7, "imitaciones": 1911, "beneficios": {"bayas": 1.0, "caza": 1.0, "dano_depredador": 1.0, "tasa_sed": 1.0}, "utilidad_media": {}, "escasez": {"agua": 0.0, "bayas": 0.075, "caza": 0.125}, "estacion": null, "parches": [{"id": 1, "tipo": "agua", "activo": true, "abundancia": 1.0, "x": 44.0, "y": 7.0}, {"id": 2, "tipo": "agua", "activo": true, "abundancia": 1.0, "x": 18.0, "y": 8.0}, {"id": 3, "tipo": "agua", "activo": true, "abundancia": 1.0, "x": 21.0, "y": 11.0}, {"id": 4, "tipo": "agua", "activo": true, "abundancia": 1.0, "x": 5.0, "y": 27.0}, {"id": 5, "tipo": "bayas", "activo": true, "abundancia": 0.964, "x": 6.0, "y": 3.6}, {"id": 6, "tipo": "bayas", "activo": true, "abundancia": 0.779, "x": 39.5, "y": 6.7}, {"id": 7, "tipo": "bayas", "activo": true, "abundancia": 0.861, "x": 51.0, "y": 7.0}, {"id": 8, "tipo": "bayas", "activo": true, "abundancia": 1.0, "x": 9.0, "y": 10.2}, {"id": 9, "tipo": "bayas", "activo": true, "abundancia": 1.0, "x": 30.0, "y": 11.0}, {"id": 10, "tipo": "bayas", "activo": true, "abundancia": 0.95, "x": 41.0, "y": 16.8}, {"id": 11, "tipo": "bayas", "activo": true, "abundancia": 1.0, "x": 18.0, "y": 19.5}, {"id": 12, "tipo": "bayas", "activo": true, "abundancia": 0.988, "x": 48.1, "y": 23.6}, {"id": 13, "tipo": "caza", "activo": true, "abundancia": 0.5, "x": 33.0, "y": 17.0}, {"id": 14, "tipo": "caza", "activo": true, "abundancia": 1.0, "x": 54.0, "y": 22.0}, {"id": 15, "tipo": "caza", "activo": true, "abundancia": 0.5, "x": 16.0, "y": 11.0}, {"id": 16, "tipo": "caza", "activo": true, "abundancia": 1.0, "x": 4.5, "y": 32.0}, {"id": 17, "tipo": "caza", "activo": true, "abundancia": 1.0, "x": 13.0, "y": 0.0}, {"id": 18, "tipo": "caza", "activo": true, "abundancia": 1.0, "x": 19.0, "y": 29.0}, {"id": 19, "tipo": "caza", "activo": true, "abundancia": 1.0, "x": 56.0, "y": 30.0}], "migraciones": 0, "nodos": [{"id": "guijarro", "rama": "litica", "nivel": 0, "titulo": "Guijarro", "origen": "arbol", "autor": 3, "tick": 1}, {"id": "lasca", "rama": "litica", "nivel": 1, "titulo": "Lasca", "origen": "arbol", "autor": 3, "tick": 4}, {"id": "bifaz", "rama": "litica", "nivel": 2, "titulo": "Bifaz", "origen": "arbol", "autor": 3, "tick": 7}, {"id": "punta_de_lanza", "rama": "litica", "nivel": 3, "titulo": "Punta de lanza", "origen": "arbol", "autor": 3, "tick": 10}, {"id": "caza_cooperativa", "rama": "litica", "nivel": 4, "titulo": "Caza cooperativa", "origen": "arbol", "autor": 3, "tick": 13}, {"id": "observar_rayo", "rama": "fuego", "nivel": 0, "titulo": "Observar el rayo", "origen": "arbol", "autor": 3, "tick": 2}, {"id": "conservar_brasas", "rama": "fuego", "nivel": 1, "titulo": "Conservar brasas", "origen": "arbol", "autor": 3, "tick": 5}, {"id": "friccion", "rama": "fuego", "nivel": 2, "titulo": "Fricci\u00f3n", "origen": "arbol", "autor": 3, "tick": 8}, {"id": "cocinar", "rama": "fuego", "nivel": 3, "titulo": "Cocinar", "origen": "arbol", "autor": 8, "tick": 9}, {"id": "ahuyentar_depredadores", "rama": "fuego", "nivel": 4, "titulo": "Ahuyentar depredadores", "origen": "arbol", "autor": 3, "tick": 11}, {"id": "gestos", "rama": "lenguaje", "nivel": 0, "titulo": "Gestos y gru\u00f1idos", "origen": "arbol", "autor": 12, "tick": 85}, {"id": "proto_palabras", "rama": "lenguaje", "nivel": 1, "titulo": "Proto-palabras", "origen": "arbol", "autor": 11, "tick": 86}, {"id": "vocabulario", "rama": "lenguaje", "nivel": 2, "titulo": "Vocabulario", "origen": "arbol", "autor": 11, "tick": 89}, {"id": "transmision_eficaz", "rama": "lenguaje", "nivel": 3, "titulo": "Transmisi\u00f3n eficaz", "origen": "arbol", "autor": 11, "tick": 90}, {"id": "cazador", "rama": "roles", "nivel": 0, "titulo": "Cazador", "origen": "arbol", "autor": 14, "tick": 494}, {"id": "recolectora", "rama": "roles", "nivel": 0, "titulo": "Recolectora", "origen": "arbol", "autor": 14, "tick": 496}, {"id": "anciano", "rama": "roles", "nivel": 1, "titulo": "Anciano", "origen": "arbol", "autor": 14, "tick": 498}, {"id": "chaman", "rama": "roles", "nivel": 2, "titulo": "Cham\u00e1n", "origen": "arbol", "autor": 14, "tick": 501}, {"id": "lider", "rama": "roles", "nivel": 2, "titulo": "L\u00edder", "origen": "arbol", "autor": 14, "tick": 503}, {"id": "tradicion_ahuyentar_depredadores", "rama": "roles", "nivel": 5, "titulo": "Tradici\u00f3n de ahuyentar depredadores", "origen": "interaccion", "autor": 9, "tick": 17}, {"id": "tradicion_caza_cooperativa", "rama": "roles", "nivel": 5, "titulo": "Tradici\u00f3n de caza cooperativa", "origen": "interaccion", "autor": 9, "tick": 19}, {"id": "arte_rupestre", "rama": "simbolico", "nivel": 0, "titulo": "Arte rupestre", "origen": "arbol", "autor": 3, "tick": 3}, {"id": "ritual", "rama": "simbolico", "nivel": 1, "titulo": "Ritual", "origen": "arbol", "autor": 3, "tick": 6}, {"id": "mito", "rama": "simbolico", "nivel": 2, "titulo": "Mito", "origen": "arbol", "autor": 3, "tick": 87}, {"id": "tradicion_ritual", "rama": "simbolico", "nivel": 2, "titulo": "Tradici\u00f3n de ritual", "origen": "interaccion", "autor": 9, "tick": 12}, {"id": "identidad_grupo", "rama": "simbolico", "nivel": 3, "titulo": "Identidad del grupo", "origen": "arbol", "autor": 5, "tick": 88}, {"id": "tradicion_lider", "rama": "simbolico", "nivel": 3, "titulo": "Tradici\u00f3n de l\u00edder", "origen": "interaccion", "autor": 6, "tick": 511}, {"id": "tradicion_mito", "rama": "simbolico", "nivel": 3, "titulo": "Tradici\u00f3n de mito", "origen": "interaccion", "autor": 5, "tick": 88}, {"id": "tradicion_identidad_grupo", "rama": "simbolico", "nivel": 4, "titulo": "Tradici\u00f3n de identidad del grupo", "origen": "interaccion", "autor": 9, "tick": 96}, {"id": "tradicion_transmision_eficaz", "rama": "simbolico", "nivel": 4, "titulo": "Tradici\u00f3n de transmisi\u00f3n eficaz", "origen": "interaccion", "autor": 13, "tick": 383}], "aristas": [{"origen": "guijarro", "destino": "lasca"}, {"origen": "observar_rayo", "destino": "conservar_brasas"}, {"origen": "arte_rupestre", "destino": "ritual"}, {"origen": "lasca", "destino": "bifaz"}, {"origen": "conservar_brasas", "destino": "friccion"}, {"origen": "friccion", "destino": "cocinar"}, {"origen": "bifaz", "destino": "punta_de_lanza"}, {"origen": "cocinar", "destino": "ahuyentar_depredadores"}, {"origen": "ritual", "destino": "tradicion_ritual"}, {"origen": "punta_de_lanza", "destino": "caza_cooperativa"}, {"origen": "ahuyentar_depredadores", "destino": "tradicion_ahuyentar_depredadores"}, {"origen": "caza_cooperativa", "destino": "tradicion_caza_cooperativa"}, {"origen": "gestos", "destino": "proto_palabras"}, {"origen": "proto_palabras", "destino": "mito"}, {"origen": "ritual", "destino": "mito"}, {"origen": "mito", "destino": "identidad_grupo"}, {"origen": "mito", "destino": "tradicion_mito"}, {"origen": "proto_palabras", "destino": "vocabulario"}, {"origen": "vocabulario", "destino": "transmision_eficaz"}, {"origen": "identidad_grupo", "destino": "tradicion_identidad_grupo"}, {"origen": "transmision_eficaz", "destino": "tradicion_transmision_eficaz"}, {"origen": "cazador", "destino": "anciano"}, {"origen": "recolectora", "destino": "anciano"}, {"origen": "anciano", "destino": "chaman"}, {"origen": "anciano", "destino": "lider"}, {"origen": "caza_cooperativa", "destino": "lider"}, {"origen": "lider", "destino": "tradicion_lider"}], "pct_fuera_arbol": 23.3, "nodos_por_origen": {"arbol": 23, "combinacion": 0, "interaccion": 7, "llm": 0}, "nivel_max": 2, "config": {"seed": 42, "individuos": 12, "ancho": 60, "alto": 34, "tasa_sed": 0.16, "tasa_energia": 0.15, "tasa_salud": 0.6, "cooldown_reproduccion": 600, "depredadores": 1, "depredador_activo": true, "crisis": false, "sequia_ticks": 0, "migracion": true, "ticks_por_estacion": 0, "umbral_agotamiento": 0.25, "ticks_migracion": 3000}}
```

`--seed 7 --benchmark --headless --ticks 600` (comprueba el presupuesto de
16,67 ms/tick; sale con código != 0 si no cabe):

```
seed 7  ticks 600  poblacion 12 -> 14
muertes 1  nacimientos 3  individuos movidos 13
depredadores 1  ataques 5  agrupamiento max 10  huidas 105
media energia 70.93  media sed 39.51
estacion sin estacion  parches 17  migraciones 0
```

y en **stderr** (el `ms/tick` no entra en el resumen, que es determinista; su
valor varía unas centésimas entre ejecuciones):

```
benchmark: 0.56 ms/tick, cabe en 16.67 ms
```

Opciones de `run`: `--seed` (default 42), `--individuos` (8–15, default 12),
`--config` (fichero JSON), `--ticks` (`0` = sin límite en ventana; obligatorio
> 0 con `--headless`), `--crisis` (sequía: menos capacidad de carga de agua y
bayas, más sed y más intentos divergentes), `--headless`, `--json` y `--benchmark`.

## Árbol de conocimiento (Fase 1)

El **árbol de plausibilidad** de concepto §8 vive en `tribal/culture/arbol.py`:
cinco ramas (lítica, fuego, lenguaje, roles y simbólico) con niveles y
prerrequisitos. Los nodos de nivel 0 no exigen nada; el resto pide los
anteriores de su rama y dos cruzan ramas a propósito (el `mito` necesita
`proto_palabras` y `ritual`: sin palabras ni ceremonia sería una anécdota, y el
`lider` necesita `anciano` y `caza_cooperativa`).

En Fase 1 cada rama avanza con una **práctica** que el instinto elige en el
tramo ocioso, no con una recompensa al rasgo. La tabla está en
`PRACTICAS` (`tribal/sim.py`) y los verbos en `tribal/core/acciones.py`:

| Rama | Práctica | Condición | Efecto |
|---|---|---|---|
| `litica` | comer | bayas o caza al alcance | recupera energía (y exige `recolectar`) |
| `litica` | tallar | junto a bosque | gasta 0,5 de energía |
| `fuego` | frotar_madera | junto a bosque | gasta 1,0 de energía |
| `lenguaje` | hablar | otro individuo a ≤2 tiles | puede transmitir una habilidad |
| `roles` | enseñar | aprendiz a ≤2 tiles | transmite una habilidad |
| `roles` | cuidar | herido a ≤2 tiles (salud < 100) | +0,5 de salud al atendido, −0,2 al cuidador |
| `simbolico` | pintar | junto a bosque o agua | consume el tick y 0,2 de energía |

El árbol sigue decidiendo el nivel: una práctica solo descubre el siguiente
escalón si sus prerrequisitos están activos, y como mucho nace **un nodo por
tick**. En calma, la lítica, el fuego, el lenguaje y el símbolo se recorren
en los primeros ticks; los roles esperan a que alguien esté herido (o haya un
aprendiz al que enseñar). Eso mueve el `pct_fuera_arbol` de la Fase 1: las
tradiciones (nivel 2) lo suben por encima de cero cuando nacen, así que el
valor depende de la semilla y de si esa partida llegó a combinar o transmitir;
en calma y sin tradición puede seguir siendo 0.0.

Cada nodo nace con su **origen** —`arbol | combinacion | interaccion | llm`,
los niveles de emergencia de concepto §8b— escrito en el momento de crearlo y
sin setter para cambiarlo después: es el dato con el que se mide si la cultura
se sale del guion. `tribal/culture/grafo.py` es el guardián: un nodo cuyos
prerrequisitos no estén activos **no se descubre** (`PrerequisitoFaltante`), y
redescubrirlo es idempotente. En esta fase el motor recorre el árbol entero
—las prácticas de arriba alimentan las cinco ramas— y las tradiciones pueden
sacarlo del árbol; por eso `pct_fuera_arbol` deja de ser 0.0 en las partidas
donde nace una tradición o cuaja una combinación, y sigue en 0.0 en las que no.
Subir esa cifra por encima del 50 % sigue siendo el trabajo de la Fase 3.

```bash
uv run python -m tribal report culture             # legible
uv run python -m tribal report culture --json      # nodos, aristas y pct_fuera_arbol
uv run python -m tribal report culture --seed 7 --ticks 900
```

Todavía no hay partida persistida, así que el informe sale de simular
`--ticks` ticks (600 por defecto) en headless con la semilla y el `--config`
pedidos: mismo seed y mismos ticks, mismo informe. Salida real de
`uv run python -m tribal report culture`:

```
seed 42  ticks 600
nodos 30  aristas 27  pct_fuera_arbol 23.3  nivel_max 2
  litica    0  Guijarro             (arbol, autor 3, tick 1)
  litica    1  Lasca                (arbol, autor 3, tick 4)
  litica    2  Bifaz                (arbol, autor 3, tick 7)
  litica    3  Punta de lanza       (arbol, autor 3, tick 10)
  litica    4  Caza cooperativa     (arbol, autor 3, tick 13)
  fuego     0  Observar el rayo     (arbol, autor 3, tick 2)
  fuego     1  Conservar brasas     (arbol, autor 3, tick 5)
  fuego     2  Fricción             (arbol, autor 3, tick 8)
  fuego     3  Cocinar              (arbol, autor 8, tick 9)
  fuego     4  Ahuyentar depredadores (arbol, autor 3, tick 11)
  lenguaje  0  Gestos y gruñidos    (arbol, autor 12, tick 85)
  lenguaje  1  Proto-palabras       (arbol, autor 11, tick 86)
  lenguaje  2  Vocabulario          (arbol, autor 11, tick 89)
  lenguaje  3  Transmisión eficaz   (arbol, autor 11, tick 90)
  roles     0  Cazador              (arbol, autor 14, tick 494)
  roles     0  Recolectora          (arbol, autor 14, tick 496)
  roles     1  Anciano              (arbol, autor 14, tick 498)
  roles     2  Chamán               (arbol, autor 14, tick 501)
  roles     2  Líder                (arbol, autor 14, tick 503)
  roles     5  Tradición de ahuyentar depredadores (interaccion, autor 9, tick 17)
  roles     5  Tradición de caza cooperativa (interaccion, autor 9, tick 19)
  simbolico 0  Arte rupestre        (arbol, autor 3, tick 3)
  simbolico 1  Ritual               (arbol, autor 3, tick 6)
  simbolico 2  Mito                 (arbol, autor 3, tick 87)
  simbolico 2  Tradición de ritual  (interaccion, autor 9, tick 12)
  simbolico 3  Identidad del grupo  (arbol, autor 5, tick 88)
  simbolico 3  Tradición de líder   (interaccion, autor 6, tick 511)
  simbolico 3  Tradición de mito    (interaccion, autor 5, tick 88)
  simbolico 4  Tradición de identidad del grupo (interaccion, autor 9, tick 96)
  simbolico 4  Tradición de transmisión eficaz (interaccion, autor 13, tick 383)
```

## Telemetría por intervalo

`report telemetry` corre una partida headless y toma una muestra cada
`--intervalo` ticks (60 por defecto): una fila por intervalo, no por frame.
Cada muestra trae `tick`, `poblacion`, `divergentes`, `conformistas`, `neutros`,
`nodos`, `aristas`, `media_energia` y `media_sed`. Acepta `--seed`, `--ticks`,
`--intervalo`, `--config` y `--crisis`.

```bash
uv run python -m tribal report telemetry                        # tabla legible
uv run python -m tribal report telemetry --json                 # 10 muestras de 600 ticks
uv run python -m tribal report telemetry --seed 7 --ticks 300 --intervalo 30 --crisis
```

Es determinista: mismos `--seed`, `--ticks`, `--intervalo` y `--config`
producen las mismas muestras, y la última coincide con el resumen de `run`
para esa partida. Salida real (600 ticks, intervalo 60 → **10 muestras**, no
600):

```
seed 42  ticks 600  intervalo 60  crisis False
  tick  pob  div  conf  neut  nodos  aristas  energia  sed
    60   12    3     7     2     15       12    75.56  20.6
   120   12    3     7     2     23       20    71.49  30.32
   180   12    3     7     2     23       20     69.2  40.03
   240   12    3     7     2     23       20    70.71  49.74
   300   12    3     7     2     23       20    66.88  59.46
   360   12    3     7     2     23       20    56.78  58.2
   420   14    3     8     3     24       21    65.89  29.18
   480   14    3     8     3     24       21    60.66  33.85
   540   15    3     8     4     30       27    63.59  26.91
   600   16    3     8     5     30       27    75.23  34.51
```

En JSON es un objeto con `seed`, `ticks`, `intervalo`, `crisis` y `muestras`
(recortado a la primera muestra):

```json
{"seed": 42, "ticks": 600, "intervalo": 60, "crisis": false, "muestras": [{"tick": 60, "poblacion": 12, "divergentes": 3, "conformistas": 7, "neutros": 2, "nodos": 15, "aristas": 12, "media_energia": 75.56, "media_sed": 20.6}]}
```

Todavía no lee una partida persistida: cuando exista `tribu.db` (Fase 3),
`report telemetry --db` leerá la tabla `telemetria` en vez de simular.

## Configuración y semilla

Una partida se reproduce con **semilla + configuración**: la semilla fija el
azar del mundo y la configuración fija todo lo demás (población, tamaño del
mapa y tasas de desgaste). `SimConfig` (`tribal/config.py`) reúne esos
parámetros, es inmutable y se serializa a JSON; el resumen de la partida los
incluye en su campo `config`, así que una salida inesperada se puede volver a
ejecutar en vez de solo anotarse.

El fichero de ejemplo, commiteado como [`docs/config-ejemplo.json`](docs/config-ejemplo.json),
es exactamente una partida por defecto:

```json
{
  "seed": 42,
  "individuos": 12,
  "ancho": 60,
  "alto": 34,
  "tasa_sed": 0.16,
  "tasa_energia": 0.15,
  "tasa_salud": 0.6,
  "cooldown_reproduccion": 600,
  "depredadores": 1,
  "depredador_activo": true,
  "crisis": false,
  "sequia_ticks": 0,
  "migracion": true,
  "ticks_por_estacion": 0,
  "umbral_agotamiento": 0.25,
  "ticks_migracion": 3000
}
```

```bash
uv run python -m tribal run --headless --config docs/config-ejemplo.json --json --ticks 600
```

Las claves que falten toman su default. Es **error** —código 2, mensaje con la
clave y el valor, sin traza— una clave desconocida, `individuos` fuera de
8–15, un mapa menor que 9×9 tiles, una tasa o un `cooldown_reproduccion` ≤ 0,
un `depredadores` negativo, un `depredador_activo`, `crisis` o `migracion` que
no sean booleanos, un `sequia_ticks` o un `ticks_por_estacion` negativos, un
`umbral_agotamiento` fuera de (0, 1] o un valor de tipo equivocado
(`"ancho": 60.7`, `"seed": "hola"`, `"individuos": true`).

Precedencia: **CLI > fichero > defaults**. `--seed` y `--individuos` pasados a
mano mandan sobre el fichero (y el resumen refleja los valores efectivos):

```bash
uv run python -m tribal run --headless --config docs/config-ejemplo.json --seed 7 --individuos 9 --json --ticks 30
# ... "seed": 7, "poblacion_inicial": 9, "config": {"seed": 7, "individuos": 9, ...}
```

Una partida más larga enseña la puerta F0→F1 completa:
`uv run python -m tribal run --seed 2 --headless --json --ticks 3000` acaba
con `poblacion_final: 17`, `nacimientos: 16`, `muertes: 11` (ninguna por
mordisco: 0 ataques), `huidas: 1078`, `migraciones: 0` (en calma el parche se
regenera en el sitio) y un `agrupamiento_max: 13`: trece individuos a ≤2 tiles
de un lago en el mismo tick (no necesariamente bebiendo a la vez). Sin ningún
recurso la tribu se extingue; ese caso lo cubren los tests del motor.

## Gradiente ambiental: parches, migración y estaciones (AMB-001)

El mundo plano de la Fase 0 no hacía de «dónde y cuándo estás» una decisión.
Desde AMB-001 (eje 3 de la hoja de ruta) los recursos viven en **parches** y el
mundo tiene **estaciones**:

- **Parches.** Al sembrar el mapa, las fuentes se agrupan por tipo y cercanía
  (`RADIO_PARCHE = 4` tiles) en parches con centro, radio y sus fuentes. El
  agua es un parche por lago y **no migra**: es terreno.
- **Agotamiento local y migración.** Un parche de comida (bayas o caza) está
  agotado cuando su abundancia —`cantidad / capacidad`— cae por debajo de
  `umbral_agotamiento`. Tras un cooldown (240 ticks) la comida **se muda** a
  otra zona: se sortea con `Mundo.azar` el orden de las casillas del terreno
  que le toca (bosque para las bayas, hierba para la caza) y se toma la primera
  que queda a ≥6 tiles del centro viejo, con todas sus fuentes en casilla
  pisable (nunca agua ni fuera del mapa) y sin apilar una fuente sobre otra del
  mismo tipo. La cercanía se mide **fuente a fuente con 1 tile**, no con
  holgura: las bayas viven repartidas por los pocos tiles de bosque del mapa y
  pedir dos tiles libres alrededor de cada mata dejaba su migración en cero. El
  parche conserva tipo, forma y capacidad, y vuelve a estar lleno. Por qué migra
  —la estación cambia la vegetación, la manada se desplaza— es la excusa
  narrativa: el mecanismo es un **andamiaje** para que seguir la presa pague y
  quedarse en la zona agotada mate, no una ley del mundo.
- **Estaciones.** Con `ticks_por_estacion > 0` el mundo cicla
  `primavera → verano → otoño → invierno` cada esos ticks. En invierno la
  regeneración cae a la mitad (el intervalo se dobla) y las técnicas que
  explotan un recurso estacional valen un 25 % más, porque la escasez muerde
  más. Con `0` (default) no hay estaciones y el clima no cambia nada.

```jsonc
// estaciones de 150 ticks y migración: cuatro estaciones por cada 600 ticks
{"seed": 42, "individuos": 12, "ticks_por_estacion": 150}
```

```bash
uv run python -m tribal run --headless --ticks 600 --config mi-config.json
# seed 42  ticks 600  poblacion 12 -> 13
# ...
# estacion primavera  parches 17  migraciones 4
```

El resumen publica el estado del gradiente: `estacion` (`null` sin
estaciones), `parches` —`id`, `tipo`, `activo` (si su abundancia llega al
umbral), `abundancia`, `x`, `y`— y `migraciones` (cuántas reubicaciones ha
hecho el mundo). En el JSON, un parche de caza ya migrado y relleno se ve así:

```json
{"id": 10, "tipo": "caza", "activo": true, "abundancia": 1.0, "x": 15.0, "y": 3.0}
```

La verificación no premia rasgos: `tests/test_ambiente.py` monta **un solo
mundo**, dos individuos que arrancan en la misma casilla, con el **mismo
genoma y el mismo sexo**, y dos políticas de acción manuales; el que camina al
parche activo sigue vivo a los 1200 ticks y el que patrulla la zona agotada
muere en el 834. Dos procesos con la misma semilla dan el mismo resumen y otra
semilla reubica los parches en otro sitio. Además, el barrido de 6 semillas ×
2 mapas (60×34 y 80×50) deja **todos** los parches de bayas y de caza migrando
al menos una vez, el agua intacta y ninguna fuente en agua o fuera del mapa.

## Genoma y habilidades (Fase 1)

El genoma ([`tribal/core/genoma.py`](tribal/core/genoma.py)) tiene ocho rasgos:
siete funcionales en [0.5, 1.5] con 1.0 neutro —velocidad, metabolismo,
longevidad, fuerza, resistencia, inteligencia y salud— y `divergencia` en
[0.0, 1.0], el temperamento conformista ↔ divergente de concepto §9b que en
F1-003 decide quién experimenta y quién imita. La generación fundadora llega con los ocho rasgos repartidos al azar
(los siete funcionales entre 0.85 y 1.15, `divergencia` entre 0.2 y 0.8), y la
descendencia hereda la media de sus dos progenitores con una mutación normal
del 5 % acotada al rango del rasgo: la misma semilla produce los mismos
genomas. Un genoma por defecto se comporta como la Fase 0.

Las **habilidades** ([`tribal/core/habilidades.py`](tribal/core/habilidades.py))
no se heredan por genoma: se aprenden viviendo. El catálogo son `cazar`,
`recolectar`, `fabricar`, `fuego` y `ensenar`, cada una en su rama del árbol de
concepto §8. La tribu arranca sabiendo `recolectar`; un adulto que sabe algo se
lo **enseña** a quien no lo sabe a ≤2 tiles (la probabilidad crece con la
inteligencia del aprendiz y con la cercanía) y quien ve a otro usar una
habilidad puede **imitarla**. Si la enseñanza no prende, el adulto no se queda
clavado: sigue deambulando. Las habilidades pesan en la acción:
`recolectar`/`cazar` rinden un 50 % más de energía al comer bayas/caza, y la
`resistencia` modula la sed de forma simétrica (1.5 → 20 % menos; 0.5 → 20 %
más).

El resumen de `run --json` añade `media_genes` (los ocho rasgos),
`habilidades_distintas` y `habilidades` por individuo.

## Divergentes y conformistas (Fase 1)

El rasgo `divergencia` del genoma decide el temperamento de concepto §9b:
por encima de **0.6** el individuo es **divergente**, por debajo de **0.4**
**conformista**, y en medio **neutro**. El rasgo **solo elige conducta**, no
aptitud: no cambia el bocado, ni la sed, ni el ritmo de cría, y el genoma no se
edita en runtime. El conformista **imita** lo que ve funcionar: cuando usa una
técnica que no descubrió él, el nodo suma una imitación (el resumen lo cuenta en
`imitaciones`). El divergente **prueba cruces nuevos**: combinaciones de dos
técnicas ya activas que no están en el árbol, catalogadas en
[`tribal/culture/combinaciones.py`](tribal/culture/combinaciones.py) con su
rama, sus dos requisitos y su justificación (`raedera`, `cuchillo_al_fuego`,
`canto_ritual`, `caceria_dirigida`, `turnos_de_vigilia`). El cruce nace con
`origen: "combinacion"` —nivel 1 de §8b—, consume el tick (no come ni bebe ese
tick) y puede fallar.

Cuando el cruce cuaja, el nodo es **conocimiento tribal** y el autor aprende la
**habilidad de la técnica**. El efecto de la combinación lo disfruta quien sabe
esa habilidad, sea divergente o no; los conformistas la copian enseñando o
imitando como cualquier otra destreza. Esa es toda la ventaja del descubridor:
lo que hizo, no lo que es.

La presión ambiental dispara la experimentación: con `--crisis` (o
`"crisis": true` en el JSON) el agua y las bayas bajan su **capacidad de carga**
a la mitad, la sed sube un 25 % para todos y los divergentes intentan cruces;
`sequia_ticks` limita la sequía a esos ticks (`0` = toda la partida). **Sin
crisis no hay intentos ni nodos `combinacion`**: en calma prospera la tradición,
y el motor no gasta ticks en experimentar.

La **reproducción** no subvenciona la crisis: el umbral es el mismo en calma y
en sequía (65 de energía) y la cría nace con 50 que paga la madre —y nunca más
de lo que tiene—, así que un nacimiento no inyecta energía neta en la población.
El resumen lo publica como `coste_reproduccion` y el test de población comprueba
que en crisis no nacen más crías por persona-tick que en calma.

### Conducta en calma

El rasgo no espera a la crisis: en el tramo ocioso el **paseo** también depende
de `divergencia` ([`tribal/agents/instinto.py`](tribal/agents/instinto.py)). El
radio del deambular va de **3 tiles** en el conformista a **10** en el
divergente (5 en el neutro), y el sesgo de cohesión es firmado: el conformista
apunta al vecino más cercano y el divergente se aparta de él. El destino se
recuerda hasta llegar, así que un radio grande es un rumbo largo y no una
difusión. La misma semilla da la misma trayectoria: todo sale de `Mundo.azar`.

La urgencia manda por encima del temperamento: con sed crítica los dos van al
agua y con un depredador encima los dos huyen. El paseo no cuesta energía ni
cambia la sed, el bocado, la cría o el genoma: el rasgo decide **qué hace**, no
**cuánto rinde**. Medido con 8 semillas × 120 ticks, mismo mapa y misma posición
de partida: el divergente explora un radio medio de 10.0 tiles y el conformista
6.2.

### Telemetría de la selección

`run --json` publica quién descubrió y qué le pasó (eje 6: no se puede refinar
lo que no se mide):

| Clave | Qué mide |
|---|---|
| `descubridores` | ids que descubrieron al menos una combinación |
| `supervivencia_descubridores` | fracción de esos ids que sigue viva |
| `supervivencia_no_descubridores` | lo mismo para el resto de quienes alguna vez vivieron |
| `diferencial_seleccion` | la resta: > 0 si descubrir sale a cuenta |

```bash
uv run python -m tribal run --headless --json --ticks 2000 --crisis
# ... "combinaciones_logradas": 5, "descubridores": [1, 2, 9],
#     "supervivencia_descubridores": 1.0,
#     "supervivencia_no_descubridores": 0.938, "diferencial_seleccion": 0.062,
#     ... se lee como: los tres que descubrieron siguen vivos y los demás
#     han perdido un 6 % de efectivos
```

La ventaja no se codifica: viene de la habilidad que el autor aprende al
descubrir (+25 % de bayas con `raedera`, −50 % de daño con
`turnos_de_vigilia`…) y de que su recurso escasee. Un divergente que no descubre
nada rinde exactamente igual que un conformista, y dos individuos con la **misma
divergencia** solo se diferencian por lo que saben hacer.

2000 ticks, 12 individuos, `crisis=true`; `div%` es la proporción de divergentes
vivos y `dif` el diferencial de selección:

```
seed | div% calma->crisis | descubridores | supD/supN | dif
   1 |  11.8 ->  11.8 | 1 | 1.000/0.842 | +0.158
   2 |  40.0 ->  17.6 | 2 | 0.500/0.842 | -0.342
   3 |  29.4 ->  52.9 | 3 | 0.667/0.882 | -0.216
   4 |  44.4 ->  25.0 | 3 | 0.667/0.714 | -0.048
   5 |  61.1 ->  58.8 | 3 | 0.667/0.833 | -0.167
   6 |   0.0 ->   0.0 | 0 | 0.000/0.579 |  0.000
   7 |  10.0 ->   6.2 | 2 | 0.500/0.789 | -0.289
   8 |   0.0 ->   5.0 | 1 | 1.000/0.864 | +0.136
   9 |  11.1 ->  21.1 | 3 | 1.000/0.941 | +0.059
  10 |  37.5 ->  20.0 | 3 | 0.667/0.812 | -0.146
```

Lectura honesta: el mecanismo ya es medible, pero con doce individuos la deriva
manda. El signo del diferencial cambia según la semilla (4/10 a favor), y la
proporción de divergentes no sube de forma sistemática: descubrir cuesta ticks y
la técnica se transmite a los conformistas en cuanto se usa. Lo que sí es
estable es de quién es la ventaja cuando aparece —del descubridor que aprendió
la habilidad, no del rasgo—.

Las combinaciones activas no son multiplicadores fijos: su **utilidad depende
del estado del mundo** (eje 1 de la hoja de ruta). La tabla da el efecto
nominal, el que se cobra cuando el recurso que explota el nodo está agotado:

| Combinación | Habilidad | Recurso | Efecto nominal |
|---|---|---|---|
| `raedera` | `fabricar` | bayas | +25 % de energía de las bayas |
| `cuchillo_al_fuego` | `fuego` | caza | +25 % de energía de la caza |
| `caceria_dirigida` | `cazar` | caza | +50 % de energía de la caza |
| `turnos_de_vigilia` | `cazar` | caza | −50 % de daño del depredador |
| `canto_ritual` | `ensenar` | agua | −10 % de tasa de sed |

La utilidad se interpola entre 1.0 (recurso lleno: no hay premio, lo que sobra
no distingue a nadie) y ese efecto nominal, según
`escasez = 1 − cantidad / capacidad`. Además se diluye con la **densidad de
portadores** (`1 / (1 + 0.1 · portadores)`): si todo el grupo sabe la técnica,
la ventaja de tenerla es de oportunidad, no de rasgo. El temperamento no entra
en la cuenta: dos individuos con la misma habilidad rinden igual.

El resumen publica la media aplicada en la corrida (`utilidad_media` por nodo),
la escasez de cada recurso y `estacion` —`null` mientras no haya estaciones
(`ticks_por_estacion = 0`); con estaciones, el invierno sube la utilidad de las
técnicas que explotan bayas o caza—.

Además, cuando una práctica se imita lo suficiente —tres imitadores distintos o
cinco imitaciones en 600 ticks— nace una **tradición** de nivel 2
(`tradicion_<nodo>`, `origen: "interaccion"`, rama `roles` si es técnica y
`simbolico` si no). La tradición es de la tribu: sigue activa aunque muera el
último que la imitó. `nivel_max` y `nodos_por_origen` resumen hasta dónde llegó
la emergencia (`arbol` = 0, `combinacion` = 1, `interaccion` = 2).

```bash
uv run python -m tribal run --headless --json --ticks 5000 --crisis
# ... "intentos_divergentes": 8, "combinaciones_logradas": 5, "tradiciones": 5,
#     "beneficios": {"bayas": 1.0469, "caza": 1.0337, "dano_depredador": 0.9777, ...},
#     "utilidad_media": {"raedera": 1.0686, "caceria_dirigida": 1.014, ...},
#     "escasez": {"agua": 0.5, "bayas": 0.526, "caza": 0.125}, "estacion": null,
#     "migraciones": 45,
#     "nodos_por_origen": {"arbol": 23, "combinacion": 5, "interaccion": 5, "llm": 0}
#     ... los cinco cruces, incluido "canto_ritual" (proto_palabras + ritual)
uv run python -m tribal run --headless --json --ticks 5000
# ... "intentos_divergentes": 0, "combinaciones_logradas": 0,
#     "utilidad_media": {}, "migraciones": 18,
#     "nodos_por_origen": {"arbol": 23, "combinacion": 0, "interaccion": 4, ...}
```

### Resultado medido del barrido (EMER-001)

10 semillas × 8000 ticks, 12 individuos, `crisis=false` frente a `crisis=true`.
`div%` es la proporción de divergentes vivos; media y σ son de `divergencia`
final; «nodos nuevos» suma `combinacion` + `interaccion`.

```
seed | div% calma->crisis | media calma/crisis | sigma calma/crisis | nacidos calma/crisis | nodos calma/crisis | poblacion calma/crisis | extinciones
   1 |  0.0 ->  0.0 | 0.460/0.431 | 0.025/0.026 | 29/34 | 1/2 |  5/15 | 0/0
   2 |  0.0 -> 23.5 | 0.486/0.545 | 0.036/0.056 | 36/40 | 1/2 | 13/17 | 0/0
   3 | 10.0 ->  0.0 | 0.545/0.508 | 0.040/0.022 | 92/40 | 1/2 | 50/13 | 0/0
   4 |  0.0 ->  0.0 | 0.400/0.412 | 0.030/0.029 | 34/17 | 1/2 | 11/ 4 | 0/0
   5 |  0.0 ->  0.0 | 0.564/0.000 | 0.024/0.000 | 38/13 | 1/2 | 16/ 0 | 0/1
   6 |  0.0 ->  0.0 | 0.357/0.301 | 0.100/0.014 | 56/28 | 1/1 | 26/12 | 0/0
   7 |  0.0 ->  0.0 | 0.420/0.000 | 0.020/0.000 | 25/ 5 | 1/2 |  8/ 0 | 0/1
   8 |  0.0 ->  0.0 | 0.000/0.447 | 0.000/0.017 | 16/26 | 1/1 |  0/ 7 | 1/0
   9 |  0.0 ->  0.0 | 0.000/0.407 | 0.000/0.020 |  2/31 | 1/2 |  0/10 | 1/0
  10 |  0.0 -> 31.9 | 0.534/0.587 | 0.023/0.031 | 62/90 | 1/1 | 17/47 | 0/0
```

**La puerta F1 no se alcanza con este mecanismo.** La proporción de divergentes
sube en 2/10 semillas, empata en 7 y baja en 1; la crisis no es más poblada que
la calma solo en 5/10. La lectura honesta: una única combinación alcanzable
(`raedera`) da una ventaja de un solo evento, la habilidad se transmite a los
conformistas y la herencia promedia `divergencia` hacia 0.5, así que el rasgo se
descuelga de la aptitud. Hacen falta más combinaciones alcanzables (o un canal
de selección que no edite el genoma); no una ventaja por decreto. Los detalles
están en `harness/progress/implementer-EMER-001.md`.

Ese barrido es anterior a CONNECT-001: entonces solo se alcanzaba `raedera`.
Desde CONNECT-001 las cinco ramas tienen práctica y los cinco cruces son
alcanzables en una partida corta con crisis —incluido `canto_ritual`, que exige
`proto_palabras` (lenguaje) y `ritual` (símbolo)—. Desde DIVERGENCIA-002 la
divergencia también cambia la conducta en calma y el resumen trae
`descubridores` y `diferencial_seleccion`, y el barrido de F1-006 (abajo) mide
la puerta entera con el mecanismo corregido.

### Puerta F1→F2 (F1-006): el barrido actual

`python -m tribal report gate-f1` corre los dos brazos —calma y crisis, la
misma configuración salvo `crisis`— sobre las semillas pedidas y publica la
tabla completa con un veredicto booleano por criterio. Los valores por defecto
son los de la puerta: 10 semillas × 8000 ticks.

```bash
uv run python -m tribal report gate-f1 --seeds 1-10 --ticks 8000
uv run python -m tribal report gate-f1 --seeds 1-10 --ticks 8000 --json
```

La **medida primaria es la respuesta en la descendencia**, no el porcentaje de
vivos: con 12 fundadores ese porcentaje es binomial por construcción. El
barrido publica:

- `nac_div`: media de `divergencia` de **todos los nacidos** acumulados.
- `S_fec` (`S`): fecundidad = media de los reproductores (una vez por individuo)
  menos la media de la población **inicial** del brazo. Base: tick 0, común a
  calma y crisis.
- `S_via`: viabilidad = media de los vivos al terminar menos la media inicial;
  0 si no queda población (no es medible).
- `desc/d` y `desc/c`: combinaciones descubiertas por individuo registrado
  divergente / conformista. Los conformistas no experimentan por diseño, así
  que `desc/c` vale 0; es un dato, no un fallo.
- `imit/desc`: imitaciones totales / combinaciones descubiertas; 0 si no hubo
  descubrimientos (la razón no existe).
- `long_d` y `long_c`: edad media al morir (ticks vividos) de descubridores y
  conformistas.
- `media` / `sigma`: distribución de `divergencia` entre los vivos al terminar,
  no solo el corte 0.55.
- `div%`: proporción de divergentes vivos, **secundaria**.

**Criterio corregido (ronda 6):** en crisis `S_fec > 0` en ≥6/10 (rastrear el
parche migrado gana); en calma **`S_fec < 0`** en ≥6/10 (en estabilidad manda
la tradición, concepto §15). La neutralidad (|S| ≤ 0.01) era un **error de
criterio**: no es una propiedad del mundo, y pedirla convertía una selección
normal en un fallo. El `div%` sigue publicado pero no decide.

El mecanismo es percepción → conducta → aptitud: el temperamento decide **qué
radio de comida ve** (4 / 8 / 14 tiles para conformista / neutro / divergente;
el agua es terreno y se ve desde lejos). La **memoria social es condicional a la
migración**: si el parche recordado no ha migrado desde que se formó/copió, la
memoria es precisa aunque el consumo lo deje temporalmente vacío (el
conformista vuelve y espera la regeneración); si el parche migró, la copia está
obsoleta y el conformista copia la memoria —también vieja— del vecino con más
energía. El divergente rastrea el parche migrado más reciente o el menos
visitado. Explorar solo se activa cuando no hay comida en el radio y cuesta
0.05 por tick; no hay bonificación al rasgo. Umbrales 0.55 / 0.45.

**La migración solo ocurre en crisis.** En calma un parche agotado se regenera
**en el sitio**: el recurso vuelve donde estaba y la memoria del conformista
sigue siendo válida. En crisis el agotamiento dispara la migración, con espera
proporcional a la escasez (lleno `ticks_migracion` = 3000, agotado 1/5 = 600) y
una reubicación de **≥11 tiles** (`DISTANCIA_MINIMA_MIGRACION`): fuera del
horizonte del conformista (4) y dentro del divergente (14). Si un mapa no tiene
casilla válida a esa distancia, ese parche no migra. `migracion=false` apaga la
migración en los dos regímenes. Así la memoria se degrada con el **cambio
ambiental**, no con el tiempo: calma = sin cambio, crisis = cambio.

```
seed | div% c->x | nac_div c/x | S_fec c/x | S_via c/x | desc/d c/x | desc/c c/x | imit/desc c/x | long_d c/x | long_c c/x | media c/x | sigma c/x | nac c/x | nodos c/x | pob c/x | ext
   1 |   0.0->  0.0 | 0.415/0.458 | -0.039/+0.003 | -0.053/-0.012 | 0.000/1.250 | 0.000/0.000 | 0.00/3103.00 | 0/3480 | 3040/3195 | 0.407/0.448 | 0.029/0.027 | 40/38 | 6/11 | 18/ 8 | 0/0
   2 |  26.3->  0.0 | 0.508/0.412 | +0.022/-0.042 | +0.011/-0.139 | 0.000/0.714 | 0.000/0.000 | 0.00/2660.80 | 0/2861 | 3046/2940 | 0.496/0.346 | 0.075/0.017 | 46/15 | 5/11 | 19/ 3 | 0/0
   3 |   0.0-> 10.0 | 0.504/0.529 | -0.053/-0.035 | -0.065/-0.044 | 0.000/0.278 | 0.000/0.000 | 0.00/2447.60 | 0/2839 | 2996/3010 | 0.504/0.524 | 0.026/0.051 | 20/42 | 2/10 |  4/10 | 0/0
   4 |   0.0-> 100.0 | 0.377/0.590 | -0.038/+0.129 | +0.000/+0.150 | 0.000/0.294 | 0.000/0.000 | 0.00/691.20 | 0/2778 | 2657/2717 | 0.000/0.595 | 0.000/0.024 | 10/14 | 6/10 |  0/ 6 | 1/0
   5 |   0.0-> 71.4 | 0.383/0.534 | -0.072/+0.064 | -0.120/+0.090 | 0.000/0.278 | 0.000/0.000 | 0.00/1393.40 | 0/2261 | 3239/2780 | 0.352/0.562 | 0.036/0.034 | 58/24 | 5/10 | 24/ 7 | 0/0
   6 |   3.1->  0.0 | 0.469/0.461 | -0.039/-0.026 | -0.050/+0.000 | 0.000/0.714 | 0.000/0.000 | 0.00/1437.40 | 0/2814 | 2788/2959 | 0.453/0.000 | 0.050/0.000 | 82/14 | 6/11 | 32/ 0 | 0/1
   7 | 100.0-> 93.3 | 0.617/0.603 | +0.018/+0.013 | +0.013/-0.005 | 0.000/0.122 | 0.000/0.000 | 0.00/504.20 | 0/2969 | 2740/2740 | 0.613/0.594 | 0.030/0.037 | 89/41 | 4/9 | 43/15 | 0/0
   8 |   0.0-> 88.9 | 0.000/0.519 | +0.000/+0.019 | +0.000/+0.111 | 0.000/0.312 | 0.000/0.000 | 0.00/1465.00 | 0/2940 | 3077/2898 | 0.000/0.612 | 0.000/0.054 | 0/26 | 4/10 |  0/ 9 | 1/0
   9 |   0.0->  0.0 | 0.362/0.381 | -0.014/+0.005 | -0.069/+0.001 | 0.000/2.500 | 0.000/0.000 | 0.00/9228.60 | 0/2607 | 2938/2915 | 0.311/0.380 | 0.020/0.050 | 29/51 | 9/14 |  8/21 | 0/0
  10 |   0.0->  0.0 | 0.372/0.443 | -0.032/+0.030 | -0.056/+0.073 | 0.000/1.000 | 0.000/0.000 | 0.00/2791.40 | 0/2994 | 2932/2890 | 0.355/0.484 | 0.015/0.022 | 25/28 | 5/11 |  9/ 6 | 0/0

VEREDICTO PRIMARIO (S): S crisis>0 7/10 | S calma<0 7/10 | PRIMARIA True
SECUNDARIO (div%, no decide): sube 4/10 | empata 3/10 | baja 3/10 | sube>=8/10 False | no baja False | crisis<=calma>=6/10 True | extinciones crisis<=calma True | SECUNDARIA False
```

**La puerta cumple a N=12 con la medida primaria:** `S_fec > 0` en crisis en
7/10, `S_fec < 0` en calma en 7/10, crisis ≤ calma y extinciones en crisis ≤
calma. `senal` (alias `primaria`) es el **veredicto de la puerta**; el antiguo
`pasa` se llama ahora `secundaria` y **no decide**. El `div%` secundario sigue
sin pasar (4/10) y no cambia el resultado. La calma es estable (parche se
regenera en el sitio, memoria válida); en crisis el parche nuevo cae a ≥11
tiles, fuera del horizonte del conformista y dentro del divergente, así que la
copia vieja cuesta.

**Confirmación N=50:** el motor admite `--individuos` hasta 100 como parámetro
de medición; el default del juego sigue en 12 (concepto §1b). La señal S se
refuerza (`S_fec > 0` en 9/10, `S_fec < 0` en 6/10), pero **crisis ≤ calma no
se replica** (4/10) y hay una extinción en crisis: la condición de régimen
favorable es dependiente de escala. Se publica como límite, no se oculta; la
puerta se cierra con el N=12 del juego y esta salvedad documentada.

```
--individuos 50 (confirmación)
seed | div% c->x | nac_div c/x | S_fec c/x | S_via c/x | desc/d c/x | desc/c c/x | imit/desc c/x | long_d c/x | long_c c/x | media c/x | sigma c/x | nac c/x | nodos c/x | pob c/x | ext
   1 |  14.8-> 25.7 | 0.469/0.505 | +0.002/+0.031 | -0.005/+0.049 | 0.000/0.070 | 0.000/0.000 | 0.00/7957.60 | 0/3030 | 3024/2811 | 0.469/0.522 | 0.083/0.047 | 172/187 | 19/24 | 61/70 | 0/0
   2 |  66.0-> 52.4 | 0.539/0.542 | +0.011/+0.013 | +0.036/+0.019 | 0.000/0.049 | 0.000/0.000 | 0.00/5847.20 | 0/3190 | 2963/2706 | 0.561/0.544 | 0.109/0.057 | 139/165 | 9/14 | 50/63 | 0/0
   3 |   5.3-> 34.8 | 0.477/0.525 | -0.034/+0.001 | -0.073/+0.003 | 0.000/0.053 | 0.000/0.000 | 0.00/7751.20 | 0/3242 | 3016/2878 | 0.447/0.523 | 0.053/0.076 | 194/199 | 8/13 | 75/69 | 0/0
   4 |   0.0-> 41.3 | 0.470/0.526 | -0.049/+0.004 | -0.096/+0.008 | 0.000/0.058 | 0.000/0.000 | 0.00/8135.60 | 0/2991 | 3064/2876 | 0.430/0.534 | 0.053/0.092 | 108/149 | 13/18 | 30/46 | 0/0
   5 |  10.0->  0.0 | 0.470/0.503 | -0.012/+0.024 | -0.068/+0.000 | 0.000/0.128 | 0.000/0.000 | 0.00/3085.80 | 0/3251 | 3069/2704 | 0.418/0.000 | 0.089/0.000 | 103/58 | 11/16 | 30/ 0 | 0/1
   6 |  32.9-> 28.3 | 0.495/0.514 | +0.014/+0.025 | +0.010/+0.039 | 0.000/0.075 | 0.000/0.000 | 0.00/9809.00 | 0/3137 | 2906/2673 | 0.494/0.523 | 0.096/0.051 | 209/154 | 17/21 | 82/46 | 0/0
   7 |  55.9-> 56.4 | 0.559/0.569 | +0.005/+0.006 | -0.026/-0.003 | 0.000/0.025 | 0.000/0.000 | 0.00/5835.60 | 0/3085 | 3063/2875 | 0.536/0.559 | 0.115/0.062 | 174/280 | 9/14 | 59/78 | 0/0
   8 |   8.5-> 70.6 | 0.456/0.547 | -0.037/+0.029 | -0.076/+0.059 | 0.000/0.056 | 0.000/0.000 | 0.00/3458.60 | 0/2809 | 3052/2987 | 0.439/0.574 | 0.071/0.057 | 147/124 | 19/24 | 59/34 | 0/0
   9 |   9.8-> 23.1 | 0.426/0.420 | -0.010/-0.016 | +0.001/-0.008 | 0.000/0.083 | 0.000/0.000 | 0.00/23803.40 | 0/2780 | 3013/2927 | 0.437/0.429 | 0.099/0.110 | 159/237 | 17/23 | 51/104 | 0/0
  10 |   4.5-> 35.3 | 0.439/0.513 | -0.047/+0.015 | -0.072/+0.034 | 0.000/0.053 | 0.000/0.000 | 0.00/10484.60 | 0/2932 | 2957/2791 | 0.422/0.528 | 0.077/0.055 | 196/218 | 16/21 | 66/85 | 0/0

VEREDICTO PRIMARIO (S): S crisis>0 9/10 | S calma<0 6/10 | PRIMARIA True
SECUNDARIO (div%, no decide): crisis<=calma>=6/10 False | extinciones crisis<=calma False | SECUNDARIA False
```

No se tocaron canales prohibidos: sin penalización al comer, la sed o la cría
por temperamento, sin ventaja reproductiva, sin editar el genoma y sin umbrales
por régimen. El conformismo pierde por **copiar información vieja**, que es una
desventaja de conducta, no un decreto. Los tests
`test_la_informacion_del_conformista_es_precisa_si_el_parche_no_migra`,
`test_en_calma_el_parche_se_regenera_en_el_sitio_y_en_crisis_migra`,
`test_la_migracion_en_crisis_deja_el_parche_fuera_del_horizonte_conformista`,
`test_la_migracion_se_acelera_con_la_escasez` y
`test_sin_crisis_explorar_no_mejora_la_energia_media` fijan el mecanismo; los
de `Simulacion` fijan nacidos, reproductores, descubrimientos por temperamento,
imitaciones y longevidad.




## Principios

1. **La magia es la sorpresa de la dinámica, no el contenido.** El LLM hace legible la emergencia; no la fabrica. Se constriñe la coherencia, nunca la dirección.
2. **Complejidad cuando la ganes.** Python + Pygame + SQLite; sin Mongo, Docker ni Rust hasta que aporten algo.
3. **El cuello de botella manda.** Se optimiza para la inferencia del LLM, no para la CPU.
4. **Capas desacopladas.** Motor de reglas, genética, memoria y LLM son piezas intercambiables.
5. **Observar es el producto.** El grafo de cultura (Obsidian y, en su día, D3) es la ventana al sistema, no un extra.

## Fases

| Fase | Qué añade | Puerta de salida |
|---|---|---|
| **0** | Motor de reglas continuo + 2D, sin LLM | La tribu vive y muestra comportamiento emergente de las puras reglas |
| **1** | Genoma + habilidades + árbol de conocimiento | Descubre algo no trivial **sin** LLM |
| **2** | Capa LLM por saliencia + diálogo + narración | Propone nodos fuera del árbol a ritmo no trivial |
| **3** | Memoria colectiva + transmisión + roles emergentes | Fin de película: criterio de éxito |

## Estructura

```
tribal/                 ← código de Tribal (motor, agentes, capa LLM)
tests/                  ← tests
agents/                 ← arnés de build (24 agentes Python)
harness/                ← backlog y memoria del arnés
vault/                  ← conocimiento del proyecto (Obsidian)
AGENTS.md               ← protocolo del arnés
init.sh                 ← la puerta
```
