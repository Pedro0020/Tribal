# implementer · F3-006

- **Fecha:** 2026-11-19
- **Veredicto:** needs-info

## Abortado por el líder

Feature F3-006 abortada el 2026-11-19 a petición del usuario: había dos agentes
trabajando sobre el mismo árbol (el implementer anterior sobrevivió al reinicio).
No se commitea nada y no se cierra la feature.

### Qué encontré al reanudar (no lo escribí yo)

Al empezar mi sesión el árbol YA tenía el trabajo del agente anterior; mi brief
decía que faltaban `tribal/culture/kpi.py` y `tribal/gate_f3.py`, pero eso no era
cierto para el primero:

- `tribal/culture/kpi.py` — existe, **completo** (129 líneas): `Hitos`, `KPI` con
  `veredicto`, y `evaluar(db)` que abre la partida con `Repositorio`, comprueba
  los cuatro hitos de objetivo.md §3.1 y calcula el porcentaje de §3.2 con
  `llm` fuera del numerador.
- `tests/test_kpi.py` — existe: e2e con semilla 1 + `backend_guionizado` a 3000
  ticks, SQL literal de §3.2 comparado con `evaluar`, mutación del numerador
  (incluir `llm`) y `xfail` estricto en el umbral del 50 %.
- `tribal/cli.py` — modificado: parser `report kpi --db [--json]` y `_report_kpi`.
- `tribal/gate_f3.py` — **no existe**. Es lo único que faltaba del encargo, junto
  con README/arquitectura §9.5 y la tabla publicada.
- Temporales: `.tmp_gen.py` y `.tmp_measure.py` (del agente anterior) y
  `.tmp-probe.py` (mío, solo medidas de solo lectura).

### Lo que aporté yo

Solo lectura y medidas: confirmé con ejecuciones reales (semilla 1, crisis,
backend guionizado) que el KPI no puede llegar al 50 %:

- 600 ticks: {arbol 23, combinacion 5, interaccion 5, llm 1} -> 29.4 %
- 1000 ticks: {arbol 23, combinacion 5, interaccion 6, llm 3} -> 29.7 %
- 3000 ticks: {arbol 23, combinacion 5, interaccion 6, llm 8} -> 26.2 %
- 6000 ticks: tribu extinta -> 0 nodos activos -> 0.0 %
- Techo observado en cualquier tick: 33.3 % (semilla 1, tick 71, aún sin mito)

Diagnóstico: solo la punta de cada rama acumula imitación (`Grafo.ultimo_activo`
filtra `nodo.id in ARBOL`), así que las tradiciones (`interaccion`) se quedan en
~6 por partida; con 23 nodos de árbol y 5 combinaciones de catálogo el techo es
(5+6)/(23+5+6+L), muy por debajo de 50. Subir el ritmo de propuestas o la
duración no ayuda: cada nodo `llm` entra en el denominador y no puede generar
tradición, y a partir de ~5500 ticks la tribu se extingue. Llegar al 50 % exige
cambiar un mecanismo (imitación de nodos que no son punta, o tradiciones de
nodos `llm`), fuera del alcance de esta feature.

### Estado al abortar

Sin commits. Sin tocar `harness/featureslist.json` ni `harness/progress/`.
Temporales sin borrar por indicación del líder (`.tmp_gen.py`, `.tmp_measure.py`,
`.tmp-probe.py`). `tribu.db` en la raíz: no generado.
Criterio 1 (e2e a los cuatro hitos): cubierto por `test_kpi.py`, no ejecutado por
mí. Criterio 2 (umbral 50 %): NO cumplido por el motor, documentado como `xfail`
estricto. Criterio 3 (`report kpi`): implementado por el anterior, no verificado
por mí. Criterio 4 (gate): no ejecutado.
