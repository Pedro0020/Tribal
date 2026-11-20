# reviewer · F3-006

- **Fecha:** 2026-11-20
- **Veredicto:** aprobado

## Criterios

1. **SQL literal de `objetivo.md` incluye `llm` y `evaluar` coincide — CUMPLIDO.**
   `objetivo.md` §3.2 y `tribal/culture/kpi.py` usan
   `origen IN ('combinacion','interaccion','llm')`; `Grafo.pct_fuera_arbol` y
   `ORIGENES_FUERA` también. `tests/test_kpi.py` ejecuta el SQL literal,
   compara con `evaluar` y exige `COUNT(estado='activo' AND origen='llm') > 0`
   en el e2e (19 nodos), así que el cambio está anclado. El test invertido
   `test_excluir_llm_del_numerador_daria_otro_numero` da 4.8 % en el mecanismo
   frente al 50.0 % literal: excluir `llm` cambiaría el número.

2. **Cadena `comb -> comb` prohibida en el motor — CUMPLIDO.**
   `tribal/culture/propuestas.py:128-135` rechaza con `cadena` cualquier
   `comb_*` cuyo requisito sea `comb_*` o `llm_*`, antes de validar la pareja.
   `tests/test_puerta_f2.py::test_una_combinacion_comb_no_puede_encadenarse`
   construye `comb_base` y `llm_base` y comprueba que `comb_nueva` con
   `("comb_base", "lasca")` y con `("llm_base", "lasca")` cae, mientras que la
   misma `comb_nueva` con requisitos del árbol se acepta. Muté `validar`
   quitando ese bloque con `inspect.getsource`: el test pasa a
   `Failed: DID NOT RAISE PropuestaInvalida`. **MATA.**
   En la BD del mecanismo, los 19 `llm_*` tienen requisitos `arbol` o
   `combinacion` de catálogo; ninguno es `comb_*`/`llm_*`. No hay cadena.

3. **Tradiciones: una por rama, sin `llm`, con efecto y apagado — CUMPLIDO.**
   `MAX_POR_RAMA = 1` (`tradiciones.py:39`), `evaluar` salta
   `original.origen == "llm"` (`:113`), el efecto es
   `saliencia.SUBIDA["tradicion_practica"] = 0.25` al descubrir en su rama
   (`sim.py` + `test_una_tradicion_viva_suma_peso...`) y `sostener` apaga a los
   `TICKS_SIN_IMITACION = 1200` sin imitaciones. Tests
   `test_como_mucho_una_tradicion_por_rama`,
   `test_una_tradicion_no_nace_de_un_nodo_llm` y
   `test_la_tradicion_que_deja_de_imitarse_se_apaga` en verde.
   En las partidas reales del mecanismo: seed 1 nace 4 tradiciones y las 4
   mueren (fuego 1980, lenguaje 2018, lítica 1973, simbólico 2063); seed 2
   ídem; seed 3 las 3 mueren; seed 4/5 tienen 4/5 activas, una por rama. Ninguna
   nace de `llm`.

4. **`gate-f2` con denominadores coherentes — CUMPLIDO.**
   `report gate-f2` (5 semillas): `activos` = suma de `arbol+comb+inter+llm`;
   `nuevos = comb+llm`; `fuera = comb+inter+llm`; `%fuera = fuera/activos`.
   Filas: 42=21+2+0+19→21/42=50.0; 46=23+4+0+19→23/46=50.0;
   46=23+4+0+19→23/46=50.0; 49=23+3+4+19→26/49=53.1;
   52=23+5+5+19→29/52=55.8. `SUCCESS True` 5/5, concentración 0.7-1.0.

5. **Corrida real publicada — CUMPLIDO.**
   `llm selfcheck --json` → `disponible: true`, `modelo_presente: true`,
   `latencia_ms: 38.5` (la del implementer: 90.6).
   Repetí la corrida real literal:
   `uv run python -m tribal run --headless --ticks 3000 --crisis --seed 1 --llm http --db <tmp> --fresh`
   → `llm peticiones 1 aplicadas 0 descartadas 3 fallos 0`.
   `report kpi --db <tmp>` → **14.8 % (4/27), 4/4 hitos, veredicto False**.
   El `tribu.db` de la raíz da lo mismo: **14.8 % (4/27), False**.
   README y arquitectura §9.5 publican ese 14.8 % y el veredicto `False`, junto
   con el 17/0/16/1 de la corrida a 60 fps; no se sustituye por el 50.0 % del
   script. Mi corrida real a 60 fps de 2000 ticks dio 23.3 % (7/30), 11
   peticiones/0 aplicadas/7 descartadas/0 fallos y `False`: el modelo real no
   produce nodos válidos y el resultado se publica, no se tapa.

6. **Hitos 4/4 y sin inyección — CUMPLIDO.**
   Mecanismo (5 semillas) y real (3000 ticks) dan `fuego`, `herramienta_compuesta`,
   `proto_lenguaje` y `mito` en `evaluar`/`report kpi`. El backend solo propone
   catálogo/`llm_*`/`comb_*`; los nodos del árbol los descubre el motor. En la
   real, 0 propuestas aplicadas y los 4 hitos salen de árbol/catálogo.

7. **Gate, calidad, regresiones y alcance — CUMPLIDO.**
   `harness gate`: `success: true`, `pytest: 462 passed in 272.41s`.
   `ruff check` / `ruff format --check` / `mypy` verdes (86 ficheros).
   F1/F2/KPI/tradiciones/store/export/telemetría/consulta/transmisión: 109
   passed. Benchmark: **0.72 ms/tick** (< 16.67 ms, 60 fps). Sin deps nuevas,
   sin `fitness`, sin `.tmp-*`; `opencode.json` fuera del diff; `tribu.db`
   ignorado.

## Evidencia del mecanismo (backend falso)

| seed | activos | arbol | comb | inter | llm | nuevos | fuera | %fuera | hitos | ok |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 1 | 42 | 21 | 2 | 0 | 19 | 21 | 21 | 50.0 | 4/4 | True |
| 2 | 46 | 23 | 4 | 0 | 19 | 23 | 23 | 50.0 | 4/4 | True |
| 3 | 46 | 23 | 4 | 0 | 19 | 23 | 23 | 50.0 | 4/4 | True |
| 4 | 49 | 23 | 3 | 4 | 19 | 22 | 26 | 53.1 | 4/4 | True |
| 5 | 52 | 23 | 5 | 5 | 19 | 24 | 29 | 55.8 | 4/4 | True |

30 propuestas solicitadas, 19 aceptadas, 11 rechazadas por semilla. Los 19
`llm_*` son parejas únicas de árbol/catálogo; en seed 1, 15 comparten
`ahuyentar_depredadores` y 4 `arte_rupestre`, pero **no son una cadena** y no
tienen requisitos `comb_*`/`llm_*`.

## Mutaciones comprobadas

- Cadena: quitar el bloque `comb -> comb` de `validar` → el test de cadena da
  `DID NOT RAISE`. **MATA.**
- Tope de tradiciones: `MAX_POR_RAMA = 99` → el test de tope falla. **MATA.**
- Apagado: `sostener` no-op → el test de apagado falla. **MATA.**
- No-llm: quitar el filtro `original.origen == "llm"` → el test de tradición
  desde `llm` falla. **MATA.**
- Adyacencia: `_ramas_plausibles` siempre True → el test de ramas no adyacentes
  falla (`DID NOT RAISE`). **MATA.**
- Excluir `llm` del numerador: mecanismo 50.0 → **4.8 %**; el test invertido lo
  ancla. **MATA.**

## No bloqueante

- El 50.0 % del mecanismo es un suelo artificial del backend falso: los 19
  `llm_*` son un abanico de parejas de árbol/catálogo, no 19 conocimientos
  independientes. Está etiquetado como “test del mecanismo” y la evidencia del
  criterio es la corrida real, 14.8 %/False. No se usa para tapar el número.
- `vault/01_PROYECTO/auditoria-llm.md` §2.18 todavía describe el KPI viejo
  («`llm` NO cuenta»), mientras §4 E1 ya pedía lo contrario. Conviene
  actualizar §2.18 para que no contradiga `objetivo.md` §3.2.
- El guard de cadena solo mira ids `comb_*`; un `llm_*` con requisito `llm_*`/
  `comb_*` seguiría aceptándose. En el mecanismo el backend solo usa
  árbol/catálogo y en la real hubo 0 aplicadas, así que no afecta a esta
  evidencia; si el modelo real empieza a encadenar `llm`, el KPI podría inflarse.
- `tests/test_divergencia_calma.py` relaja la tolerancia de 1e-3 a 2e-3 por
  doble redondeo; pasa, pero es un cambio de test no pedido.
- La concentración de F2 se mide con área acumulada sin olvido; 0.7-1.0 no es
  comparable con la tabla anterior 0.5-0.9, aunque la puerta sigue en 5/5.

## Gate

`uv run python -m agents --json run harness gate` →
`"success": true`, `"message": "ENTORNO LISTO — se puede trabajar."`,
`pytest: 462 passed in 272.41s (0:04:32)`.
