# 🏹 Tribal

![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python&logoColor=white)
![Version](https://img.shields.io/badge/Version-0.1.13-green)
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
**ESC** o cerrar la ventana termina la partida.

Salida real de `uv run python -m tribal run --headless --ticks 600 --json`:

```json
{"seed": 42, "ticks": 600, "poblacion_inicial": 12, "poblacion_final": 15, "nacimientos": 3, "muertes": 0, "media_energia": 70.22, "media_sed": 37.91, "media_genes": {"velocidad": 1.002, "metabolismo": 1.031, "longevidad": 1.085, "fuerza": 1.045, "resistencia": 0.983, "inteligencia": 1.012, "salud": 1.02, "divergencia": 0.503}, "habilidades_distintas": 1, "habilidades": {"1": ["recolectar"], "2": ["recolectar"], "3": ["recolectar"], "4": ["recolectar"], "5": ["recolectar"], "6": ["recolectar"], "7": ["recolectar"], "8": ["recolectar"], "9": ["recolectar"], "10": ["recolectar"], "11": ["recolectar"], "12": ["recolectar"], "13": ["recolectar"], "14": ["recolectar"], "15": ["recolectar"]}, "individuos_movidos": 15, "depredador": {"activos": 1, "ataques": 1, "muertes": 0}, "agrupamiento_max": 4, "huidas": 313, "n_divergentes": 5, "n_conformistas": 5, "n_neutros": 5, "intentos_divergentes": 0, "combinaciones_logradas": 0, "tradiciones": 4, "imitaciones": 764, "beneficios": {"bayas": 1.0, "caza": 1.0, "dano_depredador": 1.0, "tasa_sed": 1.0}, "nodos": [{"id": "guijarro", "rama": "litica", "nivel": 0, "titulo": "Guijarro", "origen": "arbol", "autor": 6, "tick": 1}, {"id": "lasca", "rama": "litica", "nivel": 1, "titulo": "Lasca", "origen": "arbol", "autor": 6, "tick": 4}, {"id": "bifaz", "rama": "litica", "nivel": 2, "titulo": "Bifaz", "origen": "arbol", "autor": 6, "tick": 7}, {"id": "punta_de_lanza", "rama": "litica", "nivel": 3, "titulo": "Punta de lanza", "origen": "arbol", "autor": 6, "tick": 10}, {"id": "caza_cooperativa", "rama": "litica", "nivel": 4, "titulo": "Caza cooperativa", "origen": "arbol", "autor": 6, "tick": 13}, {"id": "observar_rayo", "rama": "fuego", "nivel": 0, "titulo": "Observar el rayo", "origen": "arbol", "autor": 6, "tick": 2}, {"id": "conservar_brasas", "rama": "fuego", "nivel": 1, "titulo": "Conservar brasas", "origen": "arbol", "autor": 6, "tick": 5}, {"id": "friccion", "rama": "fuego", "nivel": 2, "titulo": "Fricci\u00f3n", "origen": "arbol", "autor": 6, "tick": 8}, {"id": "cocinar", "rama": "fuego", "nivel": 3, "titulo": "Cocinar", "origen": "arbol", "autor": 6, "tick": 11}, {"id": "ahuyentar_depredadores", "rama": "fuego", "nivel": 4, "titulo": "Ahuyentar depredadores", "origen": "arbol", "autor": 6, "tick": 14}, {"id": "gestos", "rama": "lenguaje", "nivel": 0, "titulo": "Gestos y gru\u00f1idos", "origen": "arbol", "autor": 9, "tick": 9}, {"id": "proto_palabras", "rama": "lenguaje", "nivel": 1, "titulo": "Proto-palabras", "origen": "arbol", "autor": 9, "tick": 12}, {"id": "vocabulario", "rama": "lenguaje", "nivel": 2, "titulo": "Vocabulario", "origen": "arbol", "autor": 9, "tick": 16}, {"id": "transmision_eficaz", "rama": "lenguaje", "nivel": 3, "titulo": "Transmisi\u00f3n eficaz", "origen": "arbol", "autor": 9, "tick": 17}, {"id": "tradicion_ahuyentar_depredadores", "rama": "roles", "nivel": 5, "titulo": "Tradici\u00f3n de ahuyentar depredadores", "origen": "interaccion", "autor": 11, "tick": 219}, {"id": "tradicion_caza_cooperativa", "rama": "roles", "nivel": 5, "titulo": "Tradici\u00f3n de caza cooperativa", "origen": "interaccion", "autor": 11, "tick": 218}, {"id": "arte_rupestre", "rama": "simbolico", "nivel": 0, "titulo": "Arte rupestre", "origen": "arbol", "autor": 6, "tick": 3}, {"id": "ritual", "rama": "simbolico", "nivel": 1, "titulo": "Ritual", "origen": "arbol", "autor": 6, "tick": 6}, {"id": "mito", "rama": "simbolico", "nivel": 2, "titulo": "Mito", "origen": "arbol", "autor": 6, "tick": 15}, {"id": "identidad_grupo", "rama": "simbolico", "nivel": 3, "titulo": "Identidad del grupo", "origen": "arbol", "autor": 6, "tick": 18}, {"id": "tradicion_identidad_grupo", "rama": "simbolico", "nivel": 4, "titulo": "Tradici\u00f3n de identidad del grupo", "origen": "interaccion", "autor": 11, "tick": 220}, {"id": "tradicion_transmision_eficaz", "rama": "simbolico", "nivel": 4, "titulo": "Tradici\u00f3n de transmisi\u00f3n eficaz", "origen": "interaccion", "autor": 5, "tick": 49}], "aristas": [{"origen": "guijarro", "destino": "lasca"}, {"origen": "observar_rayo", "destino": "conservar_brasas"}, {"origen": "arte_rupestre", "destino": "ritual"}, {"origen": "lasca", "destino": "bifaz"}, {"origen": "conservar_brasas", "destino": "friccion"}, {"origen": "bifaz", "destino": "punta_de_lanza"}, {"origen": "friccion", "destino": "cocinar"}, {"origen": "gestos", "destino": "proto_palabras"}, {"origen": "punta_de_lanza", "destino": "caza_cooperativa"}, {"origen": "cocinar", "destino": "ahuyentar_depredadores"}, {"origen": "proto_palabras", "destino": "mito"}, {"origen": "ritual", "destino": "mito"}, {"origen": "proto_palabras", "destino": "vocabulario"}, {"origen": "vocabulario", "destino": "transmision_eficaz"}, {"origen": "mito", "destino": "identidad_grupo"}, {"origen": "transmision_eficaz", "destino": "tradicion_transmision_eficaz"}, {"origen": "caza_cooperativa", "destino": "tradicion_caza_cooperativa"}, {"origen": "ahuyentar_depredadores", "destino": "tradicion_ahuyentar_depredadores"}, {"origen": "identidad_grupo", "destino": "tradicion_identidad_grupo"}], "pct_fuera_arbol": 18.2, "nodos_por_origen": {"arbol": 18, "combinacion": 0, "interaccion": 4, "llm": 0}, "nivel_max": 2, "config": {"seed": 42, "individuos": 12, "ancho": 60, "alto": 34, "tasa_sed": 0.16, "tasa_energia": 0.15, "tasa_salud": 0.6, "cooldown_reproduccion": 600, "depredadores": 1, "depredador_activo": true, "crisis": false, "sequia_ticks": 0}}
```

`--seed 7 --benchmark --headless --ticks 600` (comprueba el presupuesto de
16,67 ms/tick; sale con código != 0 si no cabe):

```
seed 7  ticks 600  poblacion 12 -> 13
muertes 0  nacimientos 1  individuos movidos 13
depredadores 1  ataques 1  agrupamiento max 6  huidas 162
media energia 47.61  media sed 49.94
```

y en **stderr** (el `ms/tick` no entra en el resumen, que es determinista; su
valor varía unas centésimas entre ejecuciones):

```
benchmark: 0.31 ms/tick, cabe en 16.67 ms
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
nodos 22  aristas 19  pct_fuera_arbol 18.2  nivel_max 2
  litica    0  Guijarro             (arbol, autor 6, tick 1)
  litica    1  Lasca                (arbol, autor 6, tick 4)
  litica    2  Bifaz                (arbol, autor 6, tick 7)
  litica    3  Punta de lanza       (arbol, autor 6, tick 10)
  litica    4  Caza cooperativa     (arbol, autor 6, tick 13)
  fuego     0  Observar el rayo     (arbol, autor 6, tick 2)
  fuego     1  Conservar brasas     (arbol, autor 6, tick 5)
  fuego     2  Fricción             (arbol, autor 6, tick 8)
  fuego     3  Cocinar              (arbol, autor 6, tick 11)
  fuego     4  Ahuyentar depredadores (arbol, autor 6, tick 14)
  lenguaje  0  Gestos y gruñidos    (arbol, autor 9, tick 9)
  lenguaje  1  Proto-palabras       (arbol, autor 9, tick 12)
  lenguaje  2  Vocabulario          (arbol, autor 9, tick 16)
  lenguaje  3  Transmisión eficaz   (arbol, autor 9, tick 17)
  roles     5  Tradición de ahuyentar depredadores (interaccion, autor 11, tick 219)
  roles     5  Tradición de caza cooperativa (interaccion, autor 11, tick 218)
  simbolico 0  Arte rupestre        (arbol, autor 6, tick 3)
  simbolico 1  Ritual               (arbol, autor 6, tick 6)
  simbolico 2  Mito                 (arbol, autor 6, tick 15)
  simbolico 3  Identidad del grupo  (arbol, autor 6, tick 18)
  simbolico 4  Tradición de identidad del grupo (interaccion, autor 11, tick 220)
  simbolico 4  Tradición de transmisión eficaz (interaccion, autor 5, tick 49)
```

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
  "sequia_ticks": 0
}
```

```bash
uv run python -m tribal run --headless --config docs/config-ejemplo.json --json --ticks 600
```

Las claves que falten toman su default. Es **error** —código 2, mensaje con la
clave y el valor, sin traza— una clave desconocida, `individuos` fuera de
8–15, un mapa menor que 9×9 tiles, una tasa o un `cooldown_reproduccion` ≤ 0,
un `depredadores` negativo, un `depredador_activo` o `crisis` que no sean
booleanos, un `sequia_ticks` negativo o un valor de tipo equivocado
(`"ancho": 60.7`, `"seed": "hola"`, `"individuos": true`).

Precedencia: **CLI > fichero > defaults**. `--seed` y `--individuos` pasados a
mano mandan sobre el fichero (y el resumen refleja los valores efectivos):

```bash
uv run python -m tribal run --headless --config docs/config-ejemplo.json --seed 7 --individuos 9 --json --ticks 30
# ... "seed": 7, "poblacion_inicial": 9, "config": {"seed": 7, "individuos": 9, ...}
```

Una partida más larga enseña la puerta F0→F1 completa:
`uv run python -m tribal run --seed 2 --headless --json --ticks 3000` acaba
con `poblacion_final: 8`, `nacimientos: 8`, `muertes: 12` (1 de ellas por
mordiscos del depredador), 4 ataques, `huidas: 927` y un `agrupamiento_max: 8`:
ocho individuos a ≤2 tiles de un lago en el mismo tick (no necesariamente
bebiendo a la vez). Sin ningún recurso la tribu se extingue; ese caso lo
cubren los tests del motor.

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
en sequía (65 de energía) y la cría nace con 50 que paga la madre, así que un
nacimiento no inyecta energía neta en la población.

Las combinaciones activas aportan un efecto determinista, publicado en
`beneficios`:

| Combinación | Habilidad | Efecto |
|---|---|---|
| `raedera` | `fabricar` | +25 % de energía de las bayas |
| `cuchillo_al_fuego` | `fuego` | +25 % de energía de la caza |
| `caceria_dirigida` | `cazar` | +50 % de energía de la caza |
| `turnos_de_vigilia` | `cazar` | −50 % de daño del depredador |
| `canto_ritual` | `ensenar` | −10 % de tasa de sed |

Además, cuando una práctica se imita lo suficiente —tres imitadores distintos o
cinco imitaciones en 600 ticks— nace una **tradición** de nivel 2
(`tradicion_<nodo>`, `origen: "interaccion"`, rama `roles` si es técnica y
`simbolico` si no). La tradición es de la tribu: sigue activa aunque muera el
último que la imitó. `nivel_max` y `nodos_por_origen` resumen hasta dónde llegó
la emergencia (`arbol` = 0, `combinacion` = 1, `interaccion` = 2).

```bash
uv run python -m tribal run --headless --json --ticks 5000 --crisis
# ... "intentos_divergentes": 15, "combinaciones_logradas": 5, "tradiciones": 5,
#     "beneficios": {"bayas": 1.25, "caza": 1.875, "dano_depredador": 0.5, ...},
#     "nodos_por_origen": {"arbol": 23, "combinacion": 5, "interaccion": 5, "llm": 0}
#     ... los cinco cruces, incluido "canto_ritual" (proto_palabras + ritual)
uv run python -m tribal run --headless --json --ticks 5000
# ... "intentos_divergentes": 0, "combinaciones_logradas": 0,
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
`proto_palabras` (lenguaje) y `ritual` (símbolo)—. Lo que sigue sin medirse es
la puerta F1→F2 completa: que la proporción de divergentes reaccione a la
crisis. Eso es de DIVERGENCIA-002, no de este material.

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
