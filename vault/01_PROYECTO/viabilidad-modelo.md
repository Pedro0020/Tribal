# Viabilidad del modelo local — tribal-llm (qwen2.5-3B Q8_0)

> Evaluación empírica del modelo que sirve Ollama para la Fase 2.
> Fecha: 2026-11-18. Modelo: `tribal-llm` (base `qwen2.5:3b-instruct-q8_0`).

## Método

Batería de pruebas contra `http://127.0.0.1:11434/api/chat`, en cuatro variantes:
(1) sin system prompt, (2) con persona ("eres un homínido"), (3) con estado
numérico estructurado, (4) **eligiendo entre una lista corta de acciones
candidatas** + un ejemplo (few-shot) + temperatura baja. Se midió: validez JSON,
acción en el vocabulario, acierto de la decisión, latencia, determinismo y
calidad del español.

## Resultados

| Prueba | Resultado |
|---|---|
| JSON válido (schema `format`) | **12/12** válido, acción en el vocabulario |
| Latencia media de decisión | **~1,0 s**, ~48 tokens (encaja en el presupuesto) |
| Narración en español (sin schema) | **3/3** coherente y gramatical |
| Acierto **generando la acción desde cero** (con persona) | **1/6** |
| Acierto **generando desde cero** (estado numérico, temp 0.3) | **2/4** |
| **Acierto eligiendo entre candidatas** (few-shot, temp 0.3) | **6/8** |
| Determinismo (mismo prompt ×3) | bajo: `recolectar`, `explorar`, `explorar` |
| Guardarraíl (petición imposible) | **1/2** JSON roto |

## Veredicto (corregido)

- **NO sirve para generar la acción desde cero**: no mapea estado→acción de
  forma fiable, ni con persona ni con estado numérico (elige lo contrario de su
  propio razonamiento).
- **SÍ sirve para decidir eligiendo entre una lista corta de candidatas**: 6/8,
  y los dos fallos son decisiones defendibles (huir de una pelea en vez de
  mediar), no absurdas.
- **Sí sirve para salida JSON y narración en español.**

## Implicación para F2 (arquitectura)

El LLM **sí es el cerebro que decide** — pero el contrato es "elige entre
opciones viables", no "genera la acción". El flujo correcto:

1. **Las reglas proponen 2–4 acciones candidatas** (las que son físicamente
   posibles y no absurdas para ese estado).
2. **El LLM elige una y la justifica** (`accion` + `razon` + `dialogo`),
   con few-shot y temperatura baja (~0.3).
3. **El motor valida** la elección: solo corrige si viola una restricción dura
   (depredador encima → huir), no la segunda-guess.

Así el LLM toma decisiones *de verdad* (su valor está en los dilemas, lo social
y la innovación, donde no hay respuesta única), mientras el instinto se queda
con lo trivial (sed→beber, lobo→huir) que ya hace 100 % bien.

## Alternativas si se quiere más

| Opción | Coste | Riesgo |
|---|---|---|
| Modelo mayor (7–8B, Q4) para decidir | ~4,5–5 GB VRAM, más lento | ajustado en 6 GB; sin garantía |
| Nube para decisiones (stack §12) | latencia + red | diferido |
| Few-shot más rico + validación del motor | bajo | sube algo más la fiabilidad |

## Conclusión

`tribal-llm` **sí es apto como cerebro de decisión**, con una condición de
interfaz: **elegir entre candidatas, no generar desde cero**, y con validación
del motor. Para narración y salida JSON es fiable. F2 debe implementar el
contrato "candidatas → elige → valida", no "el LLM decide en el vacío".
