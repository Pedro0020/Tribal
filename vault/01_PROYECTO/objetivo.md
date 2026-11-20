# 🎯 Objetivo — Tribal

> Documento de alcance. Destila `concepto.md` y `stack-tecnologico.md`; no
> introduce decisiones nuevas. Si algo aquí contradice al concepto, gana el
> concepto y este fichero se corrige.

---

## 1. Problema

Los simuladores de agentes que usan LLM suelen tener dos fallos: o el LLM es un
**guionista** que escribe la historia que el diseñador ya tenía en la cabeza, o
las reglas son tan cerradas que el resultado se puede predecir leyendo el
código. En ambos casos la "civilización" es una puesta en escena.

Tribal ataca ese problema con una pregunta concreta: **¿puede una cultura
aparecer sin que nadie la escriba?** Una banda de homínidos arranca sin fuego,
sin herramientas y sin lenguaje; el LLM solo decide cuando hay un dilema real,
y el motor de reglas valida lo que es físicamente plausible. Lo que se mide no
es la calidad del relato, sino si el grafo de cultura generado **se sale del
árbol de plausibilidad** que sirvió para arrancarlo (concepto §8b).

El enemigo explícito es el **guion disfrazado**: que al final la cultura sea
exactamente lo que el árbol de §8 ya preveía. Eso no es un fallo de
implementación, es el fallo del experimento.

---

## 2. Usuario / consumidor

- **Quien lo construye y lo observa:** una sola persona, en su máquina, con
  una GPU modesta. No hay usuarios concurrentes, ni cuentas, ni servicio.
- **Qué hace con Tribal:** lanza una partida, deja correr la tribu y **mira**
  (mapa 2D top-down + grafo de cultura exportado al vault). Interviene no;
  observa y consulta ("¿qué ruta llevó al fuego?", stack §6).
- **Qué obtiene:** un artefacto persistido (`tribu.db`) del que puede
  demostrar, con una consulta, si la cultura emergió o no.
- **Escala del consumidor:** 8–15 individuos por partida (concepto §1b). El
  "usuario" del sistema simulado es la tribu; el consumidor del producto es
  quien la observa.

Lo que **no** es el usuario: un jugador. No hay partida que ganar, ni
puntuación, ni objetivo que cumplir más allá de sobrevivir y transmitir.

---

## 3. Criterio de hecho

El proyecto está hecho cuando **una partida guardada demuestra cuatro hitos y
un KPI**. No es una sensación ni un vídeo bonito: es una consulta sobre la
base de datos de esa partida (concepto §15, puerta de Fase 3).

### 3.1 Los cuatro hitos

Al final de la partida, el grafo de cultura contiene **al menos un nodo activo
de cada uno de estos cuatro tipos**:

| Hito | Qué cuenta | Dónde se mira |
|---|---|---|
| **Fuego** | Una técnica de fuego adquirida por la tribu (no solo un rayo visto) | `nodos` rama `fuego`, `estado = 'activo'` |
| **Herramienta compuesta** | Un útil construido a partir de **dos o más** nodos previos | `nodos` rama `litica` con ≥2 aristas entrantes |
| **Proto-lenguaje** | Un paso de lenguaje **posterior** a gestos/grunidos | `nodos` rama `lenguaje`, nivel > 0 |
| **Mito** | Un relato compartido, no una observación suelta | `nodos` rama `simbolico`, tipo `mito` |

### 3.2 El KPI: porcentaje de nodos fuera del árbol

Cada nodo guarda su `origen` (`arbol` | `combinacion` | `interaccion` | `llm`),
según los niveles de emergencia de concepto §8b:

- **Nivel 0 — `arbol`:** el paso estaba previsto y el motor lo fuerza. No es
  emergencia.
- **Nivel 1 — `combinacion` / `llm`:** el LLM une dos o más nodos existentes
  en un paso no previsto, válido por plausibilidad. `llm` es el mismo nivel 1
  cuando el nodo lo propone el modelo y `combinacion` cuando lo inscribe la
  regla de plausibilidad del motor. Emergencia débil.
- **Nivel 2 — `interaccion`:** el nodo nace de la dinámica social y **persiste**
  porque el grupo lo copia. Emergencia real.

**Umbral:** al menos el **50 %** de los nodos de cultura activos deben tener
`origen` distinto de `'arbol'` — es decir, ser de nivel 1 o 2. El denominador
son **todos** los nodos activos de la partida, incluidos los de nivel 0: si se
excluyeran, el porcentaje sería 100 % por construcción y no mediría nada.

**Cómo se comprueba** — una consulta, no una opinión:

```sql
SELECT ROUND(100.0 * SUM(CASE WHEN origen IN ('combinacion','interaccion','llm')
                         THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_fuera_arbol
FROM nodos
WHERE estado = 'activo';
```

> **Nota (corrección de F3-006).** `llm` es nivel 1 por concepto §8b: «el LLM
> une 2+ nodos en un paso no previsto, validado». La versión anterior de este
> SQL lo omitía por un **error de transcripción**, no de diseño: la prosa de
> arriba ya pedía `origen` distinto de `'arbol'`. La solución E1 de
> `auditoria-llm.md` §4 ya lo decía. El numerador cuenta, por tanto,
> `combinacion`, `interaccion` y `llm`; el denominador sigue siendo todos los
> nodos activos.

La partida se cierra con el resultado en `tribu.db` y la comprobación pasa a
ser un test del repositorio (`tests/`) que ejecuta esa consulta y exige
`pct_fuera_arbol >= 50.0`. Un cierre de Fase 3 sin ese test en verde no cuenta
como hecho.

### 3.3 Lo que **no** cuenta como hecho

- "El LLM narró un mito precioso" → contenido, no emergencia (concepto §8c).
- "Los sprites se mueven y sobreviven" → eso es la puerta de Fase 0, no la de
  cierre (concepto §15).
- "Casi todos los nodos son nuevos" tras excluir los del árbol → trampa
  aritmética; el denominador está fijado arriba.

---

## 4. Fuera de alcance

Decidido no hacerlo **en este proyecto**, no "todavía no me ha dado tiempo":

1. **Intervención del usuario en la simulación.** Solo se observa; alimentar,
   proteger o sembrar queda para otra ocasión (concepto §1b, stack §12). En
   cuanto el humano empuja, la emergencia deja de ser demostrable.
2. **Multijugador, red o servidor compartido.** Un mundo, una máquina, un
   observador (stack §3). Sincronizar simulación y persistir sesiones remotas
   multiplica el coste sin tocar la pregunta del experimento.
3. **Entrenar o afinar modelos propios** (y usar modelos en la nube). Se
   consume un modelo pequeño ya entrenado, en local (stack §12); el enrutado a
   nube está diferido. El LLM es una pieza intercambiable, no el producto.
4. **Distribuible / Docker / instalador.** Docker resuelve empaquetado, no el
   modelo de datos, y en Windows arrastra WSL2 + CUDA passthrough (stack §4).
   Se aborda cuando toque distribuir, no antes.
5. **Render 3D o motor de juego serio.** La vista es 2D top-down pixel art,
   decidida en concepto §1b. La ventana al sistema es el grafo de cultura; el
   apartado gráfico no es el producto.
6. **Escala masiva** (miles de agentes, tiempo real a gran escala, migrar a
   Rust o Mongo por rendimiento). 8–15 individuos y un solo nodo (stack §3,
   §4). Optimizar aquí sería optimizar lo que no está lento.

**Preguntas abiertas que tampoco son criterio de hecho:** persistencia entre
sesiones, nombre definitivo y escala temporal (concepto §16). Se deciden
cuando se implementen, no definen "hecho".
