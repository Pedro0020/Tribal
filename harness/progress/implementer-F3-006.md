# implementer · F3-006

- **Fecha:** 2026-11-20
- **Veredicto:** ok

# implementer · F3-006 (corrección de la métrica)

- **Fecha:** 2026-11-20
- **Veredicto:** ok (mecanismo y tests); **la corrida real da 14.8 % y `False`**

## Qué cambié

1. `vault/01_PROYECTO/objetivo.md` §3.2 — el SQL pasa a
   `origen IN ('combinacion','interaccion','llm')`; nota: `llm` es nivel 1 de
   concepto §8b, su exclusión fue un error de transcripción, la prosa ya decía
   «origen distinto de `arbol`» y la solución E1 de `auditoria-llm.md` §4 ya lo
   pedía. Nivel 1 se describe como `combinacion`/`llm`.
2. `tribal/culture/kpi.py` — `ORIGENES_FUERA = ("combinacion","interaccion","llm")`
   y docstring alineado. `Grafo.pct_fuera_arbol` también cuenta `llm`.
3. `tests/test_kpi.py` — SQL literal con `llm`; el test exige que `evaluar`
   cuente `llm` y coincida; un test nuevo comprueba que excluirlo daría otro
   número. El e2e tiene 19 nodos `llm` (el cambio está anclado).
4. **Cadena prohibida.** `propuestas.validar` rechaza con `cadena` cualquier
   `comb_*` cuyo requisito sea otro `comb_*` o un `llm_*`. El backend solo
   propone parejas del árbol/catálogo; un cruce del modelo nace como `llm` y un
   `comb_*` como `combinacion`. Test: `test_una_combinacion_comb_no_puede_encadenarse`
   (acepta el mismo cruce con requisitos del árbol, rechaza los dos encadenados).
5. **Tradiciones: una por rama.** `MAX_POR_RAMA = 1`; ids `tradicion_<rama>_1`,
   contenido propio, nunca desde `llm`, +0.25 de saliencia al descubrir en su
   rama (efecto cultural, no multiplicador de comida) y apagado a los 1200 ticks
   sin imitación. Tests: tope, no-llm, apagado, efecto.
6. `tribal/gate_f2.py` — la tabla usa **activos** en todo: `activos`, `nuevos`
   (`comb`+`llm`), `fuera` (`comb`+`inter`+`llm`), `%fuera = fuera/activos`, una
   sola cabecera. `FilaF2.nodos_totales` y `pct_fuera_arbol_llm` usan activos;
   `fuera_arbol` excluye apagados.
7. `README.md` y `arquitectura.md` §9.4/§9.5 — SQL nuevo, tabla del mecanismo,
   corrida real y retirada de la afirmación de que `llm` no contaba.

## Test determinista del mecanismo (backend falso; no es la evidencia del criterio)

Semilla 1, 3000 ticks, crisis, 12 individuos, `backend_guionizado`:
**50.0 % (21/42), 4/4 hitos, veredicto `True`**. Barrido de 5 semillas
(`report gate-f2`, activos):

| seed | activos | arbol | comb | inter | llm | nuevos | fuera | %fuera | ok |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 42 | 21 | 2 | 0 | 19 | 21 | 21 | 50.0 | True |
| 2 | 46 | 23 | 4 | 0 | 19 | 23 | 23 | 50.0 | True |
| 3 | 46 | 23 | 4 | 0 | 19 | 23 | 23 | 50.0 | True |
| 4 | 49 | 23 | 3 | 4 | 19 | 22 | 26 | 53.1 | True |
| 5 | 52 | 23 | 5 | 5 | 19 | 24 | 29 | 55.8 | True |

`nuevos` = `comb`+`llm` (K de la puerta F2); `fuera` = `comb`+`inter`+`llm`
(KPI). 30 propuestas solicitadas, 19 aceptadas, 11 rechazadas por semilla.

## Corrida real (evidencia del criterio)

`llm selfcheck --json`:
`{"disponible": true, "endpoint": "http://127.0.0.1:11434", "modelo": "tribal-llm", "modelo_presente": true, "latencia_ms": 90.6, "error": null}`.

Comando real: misma cola `--llm http` (`ClienteLLM()` + `ColaLLM` asíncrona),
semilla 1, 3000 ticks, crisis, 12 individuos, `--db tribu.db`. El headless sin
throttle corre a ~2 ms/tick y no da ventana al modelo (7.04 s, 1 petición, 0
aplicadas); para que la cola HTTP responda se corre el mismo motor a 60 fps:
**60.37 s**. Resultado literal:

```
db tribu.db
  fuego                  si
  herramienta_compuesta  si
  proto_lenguaje         si
  mito                   si
  pct_fuera_arbol         14.8 % (4/27, umbral 50.0 %)
  veredicto              False
```

Resumen LLM de la corrida a 60 fps: 17 peticiones, **0 aplicadas**, 16
descartadas, 1 fallo; 3 propuestas de nodo, 0 aceptadas, 1 rechazada por
`transporte`. **El modelo real NO llega al 50 %: 14.8 %, veredicto `False`.**
No se sustituye por el 50.0 % del script.

## Evidencia de tests y gate

```
$ uv run pytest -q
1018 passed, 15 skipped in 340.78s (0:05:40)

$ uv run python -m agents --json run harness gate
"success": true
"check": "pytest", "detail": "462 passed in 262.88s (0:04:22)"

$ uv run ruff check tribal/ tests/ agents/   -> All checks passed!
$ uv run ruff format --check tribal/ tests/  -> 86 files already formatted
$ uv run mypy tribal/ tests/                 -> Success: no issues found in 86 source files
```

Tests con dientes: SQL literal con `llm` + exclusión da otro número;
`comb` no se encadena; tope de una tradición por rama; tradición sin imitación
se apaga; tradición nunca desde `llm`; P2 5/5 con tabla de activos.

## Qué falta

El criterio real no se cumple (14.8 %, `False`): el modelo real no produjo
nodos válidos (16 respuestas descartadas, 1 fallo de transporte). No se
commitea; decide el líder con esta evidencia.
