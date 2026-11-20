# reviewer · MEM-LOOP

- **Fecha:** 2026-11-20
- **Veredicto:** aprobado

# reviewer · MEM-LOOP

- **Fecha:** 2026-11-20
- **Puerta (ejecutada en esta sesión):** `harness gate` → `success=true`,
  `ENTORNO LISTO — se puede trabajar.` (checks: python 3.12, uv 0.10.7, venv,
  arnés OK, backlog 54 features · 7 pending · 1 in_progress · 39 done · 7 blocked,
  `pytest 503 passed in 337.38s`, 0 errores, 0 avisos).
- **Veredicto:** aprobado

## Criterios

1. **La recuperación inyecta el TEXTO del recuerdo en el contexto, no solo id y score — CUMPLIDO.**
   Capturé las peticiones reales de una corrida de 700 ticks (940 peticiones, 940 con
   `contexto["memoria"]`). Ejemplo (individuo 3, tick 281):
   ```
   [{'id': 'transmision_eficaz', 'texto': 'lenguaje transmision_eficaz Transmisión eficaz practicando hablar', 'score': 0.2887},
    {'id': 'ahuyentar_depredadores', 'texto': 'fuego ahuyentar_depredadores Ahuyentar depredadores practicando frotar_madera', 'score': 0.0},
    {'id': 'arte_rupestre', 'texto': 'simbolico arte_rupestre Arte rupestre practicando pintar', 'score': 0.0}]
   ```
   Comprobado en las 940: claves exactamente `{id, texto, score}`, `texto` es el
   literal del índice (recortado a `MAX_TEXTO_RECUERDO=160`, nunca más largo),
   `id` presente en el índice y `score` ordenado descendente. El contexto se
   serializa entero en `construir_prompt` (`json.dumps(estado)`), así que el texto
   llega al prompt, no se queda en el camino.

2. **Narración y diálogo se indexan y son recuperables por similitud en ticks posteriores — CUMPLIDO.**
   En la corrida de 700 ticks: 5 entradas narradas, las 5 en el índice como
   `narracion_<i>` con `texto` idéntico al del diario, y las 5 recuperadas en
   top-5 con una consulta de 3 palabras del propio texto (sin la frase completa).
   Diálogo: `Peticion` con `dialogo="la piedra del rio corta mejor"` en tick 1,
   drenada en tick 40 → `recuperar("piedra rio corta", hablante)` devuelve
   `('dialogo_0', individuo, 'la piedra del rio corta mejor')`. D2 cerrado.

3. **La memoria se asocia al individuo: no se recuperan recuerdos de otro sin vínculo — CUMPLIDO.**
   Índice: `recuperar("fuego hoguera", A)` → `{propio_a, tribal}`;
   `recuperar(..., B)` → `{ajeno_b, tribal}` (tribal = `individuo_id=None` la ven
   ambos). En la simulación real, de las 940 peticiones **ninguna** llevó en
   `memoria` un recuerdo con `individuo_id` distinto al de la petición y distinto
   de `None`. Segunda corrida: el diálogo del hablante no aparece en la memoria de
   otro individuo.

## Mutaciones (cada guarda nueva, por separado)

`uv run pytest -q tests/test_memoria.py tests/test_embeddings.py` tras mutar y restaurar:

| Mutación | Resultado | Tests que caen |
|----------|-----------|----------------|
| M1 `Recuerdo.a_contexto` sin `texto` (solo id+score) | 2 failed, 16 passed | `test_el_contexto_lleva_el_texto_del_recuerdo`, `test_integracion_indexa_hitos_y_llena_el_contexto` |
| M2 filtro por individuo desactivado (devuelve todo) | 3 failed, 15 passed | `test_recuperar_no_cruza_individuos`, `test_el_contexto_lleva_el_texto_del_recuerdo`, `test_el_dialogo_se_indexa_y_se_recupera_despues` |
| M3 solo lo propio, sin tribal | 1 failed, 17 passed | `test_recuperar_no_cruza_individuos` (`{'propio'} != {'propio','tribal'}`) |
| M4 narración deja de indexarse | 1 failed, 17 passed | `test_la_narracion_se_indexa_y_se_recupera_despues` |
| M5 diálogo deja de indexarse | 1 failed, 17 passed | `test_el_dialogo_se_indexa_y_se_recupera_despues` |

Ningún test pasa por casualidad de otra guardia: cada mutación cae por su propia
aserción.

## Otras verificaciones

- **Gate:** verde (arriba). **Suite completa ejecutada por mí:**
  `1085 passed, 15 skipped in 404.83s` (0:06:44).
- **ruff / format / mypy:** `All checks passed!` · `92 files already formatted` ·
  `Success: no issues found in 92 source files`.
- **60 fps:** `tests/test_cli_run.py::test_benchmark_cabe_en_el_presupuesto_de_frame`
  passa (1 passed in 0.78s).
- **Determinismo:** dos corridas con seed 42 dan la misma foto del índice
  `(id, texto, individuo_id, tick, tipo)`; el test del contrato también pasa.
- **Coste por tick (medido, no leído):** índice crece ~0.8 recuerdos/tick
  (diálogo en cada decisión). A 3000 ticks (escala de referencia) son 2473
  recuerdos; `recuperar` cuesta p50 1.37 ms y p95 7.15 ms por llamada, y hay
  ~1.45 llamadas/tick → ~2 ms/tick de media. A/B contra el mismo escenario sin
  indexar el bucle: p95 del tick 13.92 ms vs 4.12 ms a 2000 ticks. Sigue dentro
  del presupuesto de 16.67 ms, pero el coste es O(N) y N no tiene tope.
- **Sin deps nuevas** (`pyproject.toml` intacto), sin `.tmp-*`, sin
  `opencode.json`, sin rutas absolutas en el código.
- **Alcance:** solo `tribal/llm/embeddings.py`, `tribal/sim.py`, sus tests y los
  tres documentos. `featureslist.json` y `current.md` los tocó `harness start`.
- **secretos:** `secrets scan` da 13 hallazgos, todos en
  `agents/tests/test_redaction.py` y `agents/tests/test_secrets_agent.py`
  (fixtures preexistentes, fuera del diff).
- **D1-D3:** marcados resueltos en `auditoria-llm.md` con su criterio.
  README §memoria y `arquitectura.md` §2.3 al día.
- **Persistence:** `arquitectura.md` §2.5 sigue documentando que la tabla
  `recuerdos` va vacía y que reanudar no conserva el índice.

## Bloqueantes

_(ninguno)_

## No bloqueante

1. `test_la_narracion_se_indexa_y_se_recupera_despues` comprueba pertenencia al
   índice con `buscar("", k=len(indice))`, no ranking por similitud, aunque el
   criterio D2 dice "recuperable por similitud". Lo verifiqué aparte (5/5 en
   top-5 con consulta parcial), así que no bloquea, pero el test no lo cubre:
   una consulta vacía devuelve score 0 para todos y ordena por id. Sugerencia:
   afirmar `recuperar(texto_parcial, individuo)` devuelve el `narracion_<i>`
   antes que los hitos.
2. `arquitectura.md` §2.5 justifica las `recuerdos` vacías con "el índice de
   recuerdos no expone los textos". Tras MEM-LOOP el índice sí guarda el texto,
   luego el motivo ya no es cierto: falta persistir `Recuerdo`, no reescribir la
   frase. Editarlo es una línea; conviene hacerlo antes de que alguien planifique
   sobre el motivo viejo.
3. Crecimiento del índice sin tope: `dialogo_<i>`/`narracion_<i>` no se podan y
   `recuperar` recorre todo. Documentar el trade-off (o un tope por individuo)
   evitará que dentro de otras ~1000 features el coste por tick se vuelva un
   problema.
4. Atribución de la narración: va al `individuo_id` de la entrada del diario (el
   sujeto del hito; tribal si no hay sujeto). El README no lo dice y ningún test
   lo fija: si mañana alguien lo pasa a tribal, la suite no lo nota ni hay
   contrato escrito.
5. `_recuperar_memoria` devuelve `[]` con `recuerdos is None`, pero nada cubre el
   caso de una corrida sin capa LLM y otra con ella en cuanto a `resumen()["memoria"]`
   — hueco preexistente, no de esta feature.
