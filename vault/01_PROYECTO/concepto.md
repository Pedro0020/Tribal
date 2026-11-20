# 🏹 La Tribu — Civilización emergente con agentes LLM

> Documento de concepto y diseño. Estado: **perfilado y consensuado, listo para Fase 0**.
> Última revisión: 2026-11-17.
> Nota: la "pecera" queda como variante hermana (evolución genética pura). Este documento profundiza el giro hacia una **tribu paleolítica**.

---

## 1. Visión

Una banda de homínidos prehistóricos despierta en un mundo hostil **sin nada**: sin fuego, sin herramientas avanzadas, sin lenguaje estructurado. A través de la supervivencia, la cooperación y el paso de las generaciones, **la cultura emerge por sí sola**: herramientas, fuego, roles, lenguaje, rituales, mitos.

Todo observado en **2D**, con **agentes LLM locales** como cerebros individuales y una **memoria colectiva** que se transmite entre generaciones.

> No se trata de *dibujar* una tribu. Se trata de ver cómo la civilización aparece sola.

---

## 1b. Decisiones tomadas (2026-11-17)

| Decisión | Elección |
|---|---|
| Motor principal | **Cultura + sociedad** (herramientas, fuego, roles, lenguaje, rituales, mitos) |
| Papel del LLM | **Híbrido por saliencia**: todos tienen agencia, pero solo algunos "piensan" cada turno (ver §10b) |
| Horizonte evolutivo | **Abierto con fin de película** (crece sin techo, pero con criterio de éxito observable en §15) |
| Tiempo | **Continuo** (60 fps) + decisiones LLM **asíncronas** |
| Individuos | **Divergentes y conformistas** como motor cultural (ver §9b) |
| Vista 2D | **Mapa top-down** (llanura/bosque vistos desde arriba) |
| Interacción | **Observar** (la intervención queda para otra ocasión) |
| Escala | **Pequeña: 8–15 individuos** |
| Estética | **Pixel art** (mapa top-down con sprites) |

---

## 2. Por qué "tribu" encaja mejor con LLM que "pecera"

| | Pecera | Tribu paleolítica |
|---|---|---|
| Lo que evoluciona | Genética (genes, nadar) | **Cultura** (herramientas, lenguaje, mitos) |
| Velocidad de evolución | Muy lenta (imperceptible) | Rápida (se ve emerger) |
| Papel del LLM | Guionista esporádico | **Motor central** (decisiones, memoria, cultura) |
| Lo que el LLM hace bien | Poco (no "nada" bien) | **Mucho**: lenguaje, significado, roles, historia |
| Ritmo | Continuo, 60 fps | **Continuo, 60 fps** (con decisiones LLM asíncronas) |

El LLM no sabe simular física de peces mejor que una regla; sí sabe simular decisiones sociales, transmisión de conocimiento y narrativa.

---

## 3. Los dos motores de evolución

1. **Evolución genética** (lenta, entre generaciones)
   - Rasgos físicos heredables: fuerza, resistencia, inteligencia, salud, longevidad.
   - Mutación + selección natural (los mejor adaptados sobreviven y se reproducen).
   - Es el **sustrato**; da la materia prima sobre la que actúa la cultura.

2. **Evolución cultural** (rápida, intra e intergeneracional)
   - Conocimiento, técnicas, normas, historias, símbolos.
   - Se transmite por **imitación y enseñanza** (Lamarckiana: lo aprendido se hereda).
   - **Es la estrella.** Sin agentes con memoria y lenguaje, no existe.

> La cultura evoluciona órdenes de magnitud más rápido que los genes. Por eso verás innovaciones emerger en tiempo real de observación.

---

## 4. El bucle de simulación (continuo)

El mundo corre **en tiempo real** (p. ej. 60 fps): todos los individuos actúan **a la vez y de forma continua**, como en una simulación de vida, no como turnos de tablero. El tiempo avanza con un reloj (1 día = N segundos reales, acelerable).

```
BUCLE continuo (cada frame):
  1. INSTINTO    → cada agente actúa según su comportamiento por defecto + su "intención" actual
  2. LLM ASÍNC.  → si un agente enfrenta una decisión real (dilema, §10b), se lanza una consulta al LLM en segundo plano
  3. RESOLUCIÓN  → las reglas aplican resultados (energía, salud, relaciones, inventario)
  4. EVENTOS     → ¿descubrimiento/invento/muerte? se registra; la cultura crece
  5. VISUALIZAR  → se dibuja el mundo en 2D (nunca se bloquea por el LLM)
```

**Clave**: el LLM **no detiene** el mundo. Piensa en paralelo y devuelve su decisión cuando puede; mientras, la vida sigue.

---

## 5. El individuo (agente)

| Campo | Descripción |
|---|---|
| `id`, `nombre` | Identidad |
| `edad`, `sexo` | Demografía |
| `energia`, `salud`, `sed` | Necesidades físicas |
| `genoma` | Rasgos heredables (fuerza, inteligencia, salud…) |
| `habilidades` | Lo que sabe *hacer* (cazar, fabricar, fuego…) |
| `memoria` | Episódica + semántica (ver §6) |
| `relaciones` | Vínculos con otros (parentesco, amistad, rivalidad) |
| `personalidad` | Rasgos estables: **divergencia** (conformista ↔ divergente), curiosidad, cautela, sociabilidad |
| `saliencia` | Peso narrativo *ganado*; determina cuánto "piensa" (ver §10b). Distinto de divergencia (§9b) |

### Necesidades (lo que empuja la acción)
Hambre, sed, frío, cansancio, seguridad, pertenencia (social). La **urgencia** de cada necesidad prioriza decisiones.

---

## 6. Memoria — el corazón del agente

La coherencia y la evolución cultural dependen de esto. Tres niveles:

1. **Memoria episódica** (individual): qué le pasó a *mí* ("el lobo me atacó junto al río", "frotar palos calienta").
2. **Memoria semántica/procedimental** (individual): qué *sé* ("sé encender fuego", "sé tallar sílex").
3. **Memoria colectiva** (la tribu): tradiciones, técnicas compartidas, mitos, tabúes. **Se transmite entre generaciones** (los ancianos enseñan a los jóvenes).

> Regla clave: la memoria **crece sin límite** → hay que **resumir/comprimir** periódicamente (los recuerdos viejos se funden en "conocimiento" y "tradición").

### La cultura como grafo de conocimiento
- La **memoria colectiva** se modela como un **grafo**: nodos = conceptos/técnicas/mitos (`fuego`, `caza`, `sílex`, `mito del gran jabalí`), aristas = relaciones (`fuego → cocinar → carne`).
- El LLM, en vez de recibirlo todo en el prompt, **recorre el grafo** y carga solo lo relevante (GraphRAG ligero). Así la memoria crece sin llenar el contexto.
- La cultura **nace, se conecta y a veces muere** como el grafo: un divergente añade un nodo, los conformistas lo agrandan al copiarlo, un anciano que muere sin enseñar deja un nodo "apagado".
- **Observación**: el grafo se exporta a Markdown (`[[wikilinks]]`) para verlo en **Obsidian (graph view)**, y en la propia app como **grafo vivo** (D3, Fase 3). Es "la mente de la tribu" dibujada.

---

## 7. Acciones (conjunto finito, para constreñir al LLM)

- **Supervivencia**: cazar, recolectar, beber, descansar, refugiarse, huir.
- **Producción**: fabricar herramienta, encender fuego, construir refugio.
- **Social**: conversar, enseñar, cuidar, cortejar, cooperar, competir.
- **Cognitivas**: explorar, observar, experimentar, recordar.
- **Culturales**: ritual, contar historia, pintar (arte rupestre).

> Cada acción se resuelve con **reglas simples + habilidades + azar + entorno**. El LLM *elige* la acción, no la *ejecuta*.

> **Cómo elige (viabilidad, §viabilidad-modelo):** el LLM no elige entre las ~20
> acciones del vocabulario —eso falla—; elige entre **2–4 candidatas que las
> reglas ya filtraron como viables para ese estado**, con **few-shot** (1–2
> ejemplos de estado→acción) y **temperatura baja (~0.3)**. El motor valida y
> solo corrige si viola una restricción dura (depredador encima → huir).

---

## 8. Árbol de conocimiento / cultura (progresión)

Para dar sensación de avance **sin** que el LLM invente fuego el día 1. Ramas orientativas (parcialmente abiertas):

- **Lítica**: guijarro → lasca → bifaz → punta de lanza → caza cooperativa.
- **Fuego**: observar rayo → conservar brasas → fricción → cocinar → ahuyentar depredadores.
- **Lenguaje**: gestos/grunidos → proto-palabras → vocabulario → transmisión eficaz (acelera todo lo demás).
- **Roles**: cazador, recolectora, anciano, chamán, líder.
- **Simbólico**: arte rupestre → rituales → mitos → identidad del grupo.

> Diseño: el árbol es un **andamiaje de plausibilidad** (límites), no un guion fijo. El LLM puede proponer pasos, pero el motor valida que sean coherentes con lo ya descubierto.

---

## 8b. Qué cuenta como "emergencia" (y cómo medirla)

El árbol de §8 es un **andamiaje**, no el contenido. Si al final la cultura es solo lo que el árbol ya preveía, no hubo emergencia: se repitió el guion del diseñador. Para distinguirlo, cada nodo del grafo de cultura registra su **origen**:

| Nivel | Origen | Ejemplo | ¿Emergencia? |
|---|---|---|---|
| **0 · Guionado** | El paso ya estaba en el árbol y el motor lo fuerza | "fricción → fuego" aparece porque estaba previsto | ❌ No |
| **1 · Combinación** | El LLM une 2+ nodos existentes en un paso **no previsto**, validado por plausibilidad | "conservar brasas" + "refugio" → "fuego dentro de la cueva para calentar" | ⚠️ Débil |
| **2 · Interacción** | Un nodo nace de la dinámica social (imitación, tabú, repetición) y **persiste** porque el grupo lo copia | un tabú, un ritual, una técnica que nadie "inventó" sino que surgió de compartir | ✅ Real |

**Métrica (KPI):** cada nodo guarda `origen` (`arbol` | `combinacion` | `interaccion` | `llm`). Al final de Fase 2–3 se mira el **% de nodos que no estaban en el árbol inicial** (niveles 1 y 2). Si tras N generaciones sigue en ~0%, el sistema no está emergiendo: está reproduciendo el árbol.

> **Criterio de éxito del proyecto:** la tribu debe **abandonar el andamiaje**. El árbol existe solo para arrancar; el éxito se mide por lo rápido que la tribu lo deja atrás y genera nodos propios que sobreviven.

---

## 8c. Cómo se fomenta la espontaneidad (la "magia")

La magia que se busca no es que el LLM invente un mito bonito — eso es **guion**, y se siente falso. La magia real es que **el sistema llegue a algo no guionado por su propia dinámica**: que un mito nazca *porque* un anciano murió sin enseñar, un divergente rompió un tabú y la tribu reinterpretó el hecho. El **contenido** (el mito) lo puede aportar el LLM; la **sorpresa** (que surgiera, de quién, cuándo, tras qué cadena de causas) la produce la simulación.

La espontaneidad no se programa ("sé espontáneo"); se crean **condiciones** para que lo inesperado *pueda* pasar:

1. **Reglas locales + bucles de retroalimentación.** Necesidades + personalidad + balance divergente/conformista (§9b) ya producen dinámica social antes de que exista el LLM (como el Juego de la Vida produce "gliders" que nadie diseñó).
2. **Perturbación.** La novedad sale del estrés (sequía, depredador, extraño), que saca a los agentes de su bucle cómodo y los obliga a combinar.
3. **Amplificación social.** Un detalle al azar se vuelve cultura solo si los conformistas lo copian y lo enseñan: imitación + prestigio + repetición convierten *ruido* en *cultura*.
4. **Permiso para fallar.** Parte de la gracia es que el experimento del divergente fracase, que la tribu se extinga, que surja un tabú absurdo. La magia incluye el error; el control total la mata.

> **Regla de oro:** constriñe la **coherencia** (qué es físicamente plausible), nunca la **dirección** (qué inventan, quién lidera, qué tabú nace). En cuanto el árbol de §8 elige el camino, mató la espontaneidad.

**Papel del LLM:** no es el generador de la magia, es el **narrador** que la hace visible — elige acciones dentro de un vocabulario finito, propone combinaciones de nodos y pone palabras a lo que la simulación ya produjo.

---

## 9. Sociedad y relaciones emergentes

- **Vínculos**: parentesco, amistad, rivalidad, prestigio.
- **Estructura emergente**: líder (¿por fuerza o por sabiduría?), reparto de tareas por sexo/edad/habilidad, tabúes.
- **Cooperación vs. conflicto**: caza en grupo, reparto, disputas, expulsión.
- **Transmisión**: los ancianos concentran conocimiento; su muerte es un riesgo cultural real (pérdida de técnicas).

---

## 9b. Divergentes y conformistas — el motor de la cultura

En toda sociedad hay individuos **divergentes** (se desvían, exploran, cuestionan) y otros **conformistas** (imitan, mantienen, transmiten). Esa tensión es la que hace evolucionar la cultura.

| | Divergente | Conformista |
|---|---|---|
| Tendencia | Explora, experimenta, rompe reglas, migra | Imita, sigue la norma, enseña, mantiene rituales |
| Aporta | **Variación** (ideas/técnicas nuevas) | **Transmisión y estabilidad** (fija y copia lo que funciona) |
| Riesgo | Muere si falla (el innovador arriesga) | Se estanca si el entorno cambia |
| En el motor cultural | Es la "mutación" | Es la "selección + herencia" |

**El ciclo de innovación cultural:**
1. Un **divergente** propone algo nuevo (nueva herramienta, idea, tabú roto).
2. Si funciona (mejora la supervivencia), los **conformistas** lo copian y lo enseñan → se fija en la cultura de la tribu.
3. Si falla, el divergente muere o la idea se olvida.

**Balance dinámico (frequency-dependence):**
- En **estabilidad**, los conformistas prosperan (la tradición funciona) → la tribu se vuelve más homogénea.
- En **crisis** (sequía, depredador nuevo, cambio de clima), los divergentes prosperan (lo viejo ya no sirve) → la tribu innova.
- La **proporción** de divergentes/conformistas evoluciona con el entorno, porque la *divergencia* es un rasgo heredable sobre el que actúa la selección.

### Divergencia vs. saliencia (no confundir)
- **Divergencia** = *temperamento* (innato + moldeado): cuánto se desvía del grupo. Responde a "¿quién es así?".
- **Saliencia** = *peso narrativo ganado* (dinámico): cuánto protagonismo ha acumulado. Responde a "¿quién destaca en la historia?".

Un conformista también puede ser saliente (p. ej. un anciano muy respetado que guarda la tradición); un divergente puede pasar desapercibido si sus ideas nunca cuajan.

---

## 10. El papel exacto del LLM

1. **Elegir la acción** de los individuos que "piensan" ese turno (ver §10b), **de entre las 2–4 candidatas que las reglas ya filtraron**. Salida JSON corto, con few-shot y temperatura baja (~0.3). El motor valida y solo veta restricciones duras.
2. **Generar pensamiento/diálogo** para ver la "vida interior".
3. **Proponer descubrimientos/inventos** dentro de las reglas de plausibilidad del árbol.
4. **Narrar hitos** (primera chispa, primera caza en grupo, primera palabra, primera muerte de un anciano).

### Ejemplo de salida (JSON)
```json
{
  "accion": "fabricar",
  "objetivo": "punta_de_lanza",
  "razon": "El jabalí nos hirió ayer; necesito alcance.",
  "dialogo": "Si afilo la piedra, no tendré que acercarme tanto."
}
```
> **Obligatorio**: JSON schema / gramáticas (*constrained decoding*) para que el modelo no divague. Además, el motor **valida** la elección y la corrige solo si viola una restricción dura. Justificación empírica en `viabilidad-modelo.md` (a 3B: elegir entre candidatas acierta 6/8; generar desde cero, 1/6).

---

## 10b. Modelo de pensamiento por saliencia (híbrido)

Objetivo: que **todos los individuos tengan agencia y puedan emerger como personajes**, sin que los 20 consulten al LLM todo el rato (inviable). Tres niveles:

1. **Instinto (todos, siempre)**
   - Comportamiento por defecto continuo: beber si hay sed, comer si hay comida cerca, huir del depredador, descansar.
   - Sin LLM, barato. Mantiene a la tribu viva y en movimiento.

2. **Pensamiento LLM por dilema (asíncrono, selectivo)**
   - Un individuo lanza una consulta al LLM cuando hay *algo que decidir de verdad*:
     - conflicto de necesidades (hambre vs. miedo al depredador),
     - evento relevante propio (descubrió algo, conflicto social, muerte cercana),
     - oportunidad de innovar (materiales a mano + curiosidad).
   - Mientras el LLM responde, el agente sigue con su instinto (no se congela).

3. **Protagonismo emergente (saliencia)**
   - Cada individuo acumula **saliencia** según la relevancia de sus actos (primero en encender fuego, líder, chamán, salvó a alguien…).
   - Los de alta saliencia se convierten en **personajes emergentes**: piensan más a menudo, su diálogo se muestra más y su memoria se conserva mejor.
   - La saliencia es **dinámica**: cualquiera puede emerger, y un protagonista puede decaer.

> Resultado: un **gradiente**, no un binario "protagonistas vs. extras". Todos pueden pensar de vez en cuando; los interesantes piensan más. En la práctica, solo **~3–6 individuos "piensan" a la vez**, en **segundo plano**, sin detener el mundo.

---

## 11. Arquitectura (continuo + LLM asíncrono)

```
┌───────────────────────────────────────────────────┐
│  MOTOR DE REGLAS  (determinista, rápido)          │
│  entorno, física simple, energía, salud, recursos │
├───────────────────────────────────────────────────┤
│  AGENTES  (10–20)                                  │
│  percepción + memoria + personalidad + necesidades │
├───────────────────────────────────────────────────┤
│  CAPA LLM  (selectiva por saliencia, §10b)        │
│  decide acción, genera diálogo, propone inventos  │
├───────────────────────────────────────────────────┤
│  MEMORIA COLECTIVA  (cultura, tradición, mitos)   │
│  se transmite entre generaciones                  │
└───────────────────────────────────────────────────┘
```

---

## 12. Coste y ritmo

El mundo corre fluido a **60 fps**; el LLM **no bloquea**: las decisiones se calculan en **segundo plano** (cola asíncrona). Solo **~3–6 individuos "piensan" a la vez**; el resto va por instinto.

| Modelo (Q8_0) | VRAM | tps aprox. | Latencia por decisión (~20 tokens) |
|---|---|---|---|
| Qwen2.5-1.5B | ~2.5 GB | >100 | ~0.2–0.5 s |
| Qwen3.5-2B | ~3 GB | ~80 | ~0.3–0.8 s |
| Qwen2.5-3B | ~4.3 GB | ~55 | ~0.5–1.5 s |

**Optimizaciones** (si quieres más fluidez):
- **Cola asíncrona**: las consultas se atienden en paralelo mientras la simulación sigue.
- Salida JSON mínima (5–15 tokens).
- Solo "piensan" los agentes ante un dilema real; el resto, por instinto.

---

## 13. Mundo y presiones ambientales

- **Recursos** que se agotan y regeneran (caza, bayas, agua, sílex, madera).
- **Estaciones** (invierno = presión; empuja a innovar: refugio, fuego, almacenar).
- **Depredadores** y **otras tribus** (competencia/contacto).
- **Desastres**: incendio, sequía, enfermedad (disparadores de cambio).

> La **presión ambiental creciente** es lo que evita el bucle "cazar/recolectar para siempre" y fuerza la innovación cultural.

---

## 14. Riesgos y mitigaciones

1. **Incoherencia** (fuego el día 1, contradicciones) → árbol de plausibilidad + validación del motor + memoria estructurada.
2. **Bucle sin progresión** → presión ambiental + disparadores de eventos + descubrimientos forzados suaves.
3. **Memoria sin límite** → resumen/compresión periódica (episodios → conocimiento → tradición).
4. **Extinción de la tribu** → mecánica de reposición o persistencia (no perder todo el avance cultural).
5. **Coste de tokens** → heurística para acciones triviales + modelo pequeño + JSON mínimo.
6. **Falta de español en el modelo** → Qwen/Gemma manejan bien el español.

---

## 15. Plan por fases (cada fase funciona sola, con puertas de salida)

Cada fase termina en una **puerta go/no-go**: un criterio observable que decide si seguir o pivotar. No se invierte en la fase siguiente hasta pasar la puerta.

- **Fase 0** — Motor de reglas continuo + 2D: individuos con necesidades que sobreviven/reproducen en tiempo real. *Sin LLM* (acciones por instinto).
  - **Puerta F0→F1:** la tribu "vive": sobrevive, se reproduce, muere, y aparece **al menos un comportamiento emergente visible de las puras reglas** (agolparse junto al agua, huida en manada del depredador). Si la pantalla solo muestra sprites moviéndose sin vida, el genoma no lo arreglará.
- **Fase 1** — Genoma + habilidades + árbol de conocimiento básico (herramientas, fuego) con progresión.
  - **Puerta F1→F2:** sin LLM, la tribu descubre espontáneamente algo **más allá del primer paso forzado**, y la proporción divergente/conformista reacciona a la crisis (los divergentes innovan cuando el entorno cambia, §9b). Si aquí no emerge nada no trivial, el LLM **no** lo arreglará después.
- **Fase 2** — **Capa LLM**: decisión por saliencia + diálogo + narración de hitos.
  - **Puerta F2→F3:** el LLM propone nodos **fuera del árbol** (nivel 1 de §8b) que pasan la validación a un ritmo no trivial, y la saliencia concentra la narración en pocos individuos (§10b).
- **Fase 3** — Memoria colectiva + transmisión intergeneracional + roles/estructura social emergente.
  - **Fin de película (criterio de éxito):** la tribu pasa de **cero** a **fuego + una herramienta compuesta + un proto-lenguaje + un mito**, donde **al menos la mitad de esos nodos no estaban en el árbol inicial** (§8b). Demostrable, no una sensación.

---

## 16. Decisiones y preguntas abiertas

**Resueltas** (ver §1b):
- Motor principal → Cultura + sociedad.
- Papel del LLM → Híbrido por saliencia (§10b).
- Horizonte → Abierto con fin de película (§15).
- Criterio de éxito → fuego + herramienta compuesta + proto-lenguaje + mito, con ≥50% de nodos fuera del árbol (§8b).
- Tiempo → Continuo (60 fps) + decisiones LLM asíncronas.
- Individuos → Divergentes y conformistas (§9b).
- Vista → Mapa top-down.
- Interacción → Observar (intervenir queda para otra ocasión).
- Escala → Pequeña (8–15 individuos).
- Estética → Pixel art.

**Resueltas** (más):
- Persistencia → Guardar y reanudar la tribu entre sesiones (§17).
- Reinicio → Eliminar el mundo actual y empezar de cero (§17).
- Nombre → **Tribal**.

**Pendientes**:
1. **Escala de tiempo**: ¿cuánto tiempo real representa un día/estación (velocidad del reloj, acelerable)?

---

## 17. Guardar, cerrar y empezar de cero

Dos acciones de runtime, ambas desde la ventana del simulador (menú o teclas):

1. **Guardar y cerrar** — el estado se persiste y se puede reanudar luego.
2. **Nuevo mundo** — borra el mundo actual y empieza de cero.

### Qué se guarda

Todo lo que ya vive en SQLite (§5 del stack): individuos, relaciones, recursos,
mundo (`tick`/estación/clima), grafo de cultura (nodos/aristas), recuerdos,
diario y telemetría. Además:

- **Semilla y estado del RNG**: una partida retomada es exacta y reproducible.
  Se guarda la semilla inicial y el estado del generador, no solo el contador.
- **Metadatos del save**: nombre, fecha, seed, población y nº de nodos de cultura
  (`save_meta.json`).

### Semántica

- **Guardar y cerrar** = `COMMIT` + snapshot consistente + salir limpio. Aunque se
  cierre la ventana, SQLite ya es durable; "guardar" asegura un punto coherente.
- **Reanudar** = abrir el `world.db` existente y seguir desde el `tick` guardado.
- **Nuevo mundo** = archivar (opcional) o borrar el `world.db` actual, generar una
  semilla nueva y empezar en tick 0 con una tribu nueva de 8–15 individuos.

### UX mínima

- Al arrancar con un mundo existente: **Continuar / Nuevo mundo**.
- **Guardar y salir** con una tecla/menú, y **confirmación explícita** antes de
  **Nuevo mundo** (es destructivo e irreversible).

### Estado

Implementado como `tribal world reset` (RESET-001): archiva por defecto en
`archivo/world-<marca UTC>.db` (con la meta), `--borrar` elimina, `--seed` fija
la semilla y sin `--yes` no toca nada (sale con 2). La ventana aún no ofrece el
menú; la confirmación es la de la CLI.
