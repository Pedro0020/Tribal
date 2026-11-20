# reviewer · MEDIR-LLM

- **Fecha:** 2026-11-20
- **Veredicto:** aprobado

## Criterios

1. **`resumen()` expone % LLM vs instinto por tramo — cumplido.**
   `uv run python -m tribal run --headless --json --llm stub --llm-sincrono --ticks 1200 --seed 42`
   → `llm 1400 / instinto 13359 / total 14759 / 9,5 %`, **20 tramos** con índices
   0–19 sin huecos. Verificado: Σllm=1400, Σinstinto=13359, los 20 tramos cumplen
   `pct == round(100·llm/(llm+instinto),1)` (0 malos). `peticiones` 1415 ≠
   `aplicadas` 1400 = acciones LLM 1400: el denominador es la acción aplicada, no
   la petición. Línea de texto: `acciones 17/3600 llm (0.5 %)`.

2. **auditoria-llm.md §1 con el número medido y su comando — cumplido.**
   Reproducido: `... --llm http --ticks 2000 --seed 1 --crisis` → peticiones 1,
   aplicadas 0, descartadas 3, fallos 0, **0/24 972 = 0,0 %**, **34 tramos**
   (índices 0–33). §1 publica ambos números y comandos; README también. §2.12 ya
   no dice «cubre el 95 %»: publica 100 % real / ≈90,5 % stub con referencia a §1.
   No queda ningún «~5 %» de uso del LLM en auditoría ni README.

3. **Test ancla que distingue instinto de LLM y cae si se finge — cumplido.**
   `test_una_intencion_caducada_cuenta_instinto_no_llm` aserta el bloque completo
   (`llm 0, instinto 1, total 1, pct 0.0, por_tramo [0/1/0.0]`) y también cae con
   la mutación exacta que motivó el rechazo (contar «había intención» sin aplicar
   la caducada). Las cuatro mutaciones caen (tabla abajo).

## Mutaciones (baseline `sim.py` SHA256 5543B683…6767, restaurado y verificado tras cada una)

| Mutación | Resultado |
|---|---|
| `decidida_llm = intencion is not None` (contar no aplicable/corregida) | **cae** `test_una_intencion_no_aplicable_cuenta_instinto_no_llm` (1 == 0) |
| `_contar_accion(True)` al drenar la cola (contar encoladas) | **cae** `test_el_resumen_publica_...` (llm 2815 > peticiones 1415) |
| quitar `if self.mundo.tick > hasta: return None` (aplicar la caducada) | **cae** `test_una_intencion_caducada_cuenta_instinto_no_llm` |
| B1 métrico puro: `tenia_intencion and intencion is None → decidida_llm = True` (sin tocar comportamiento) | **cae** el mismo test (llm 1 != 0) |

Tras cada corrida: `sim.py` restaurado con hash idéntico al baseline y
`tests/test_medir_llm.py` intacto (`5FDC3421…A286`). En limpio: 8 passed.

## Otras comprobaciones

- **Tramos vacíos:** `test_los_tramos_sin_acciones_se_incluyen` (tribu sin
  individuos, 120 ticks → tramos `[0,1]`, todo 0). El rango de `_acciones_json`
  cubre `(tick-1)//60 + 1` y coincide con el tramo de `_contar_accion`.
- **Reanudar contadores:** 300 ticks con stub a `db` → `17/3 583/3 600`, 5 tramos;
  `Simulacion.reanudar(db)` devuelve **el bloque idéntico** (mismos 5 tramos). El
  test nuevo cubre además el caso 600+600 con monotonicidad por tramo.
- **LLM off:** sin bloque `llm` (documentado), `acciones_llm == 0`,
  `instinto == total > 0`, sin errores.
- **ruff check / format --check / mypy:** verde, 91 ficheros.
- **secrets scan:** 13 hallazgos, todos fixtures preexistentes en `agents/tests`;
  ninguno en los ficheros tocados. Sin dependencias nuevas, sin `.tmp-*`,
  `opencode.json` fuera del diff.
- **Gate:** ver línea al final.

## No bloqueante

- `_aplicar_contadores` sigue en 67 líneas (ya era larga; +7 de este cambio).
- El test de reanudar usa `>=` en vez de igualdad exacta. Verifiqué la igualdad
  exacta a mano; apretarlo a `==` lo haría más fuerte.
- **Para el líder, no para este aprobado:** el diff de `auditoria-llm.md` incluye
  reescrituras de §3, §6 y §7, y `harness/featureslist.json` gana `LLM-CONFIG`,
  posteriores al informe del implementer (mtimes 8:40 y 8:44 frente a 8:38:56) y
  no mencionados en él. No las atribuyo a MEDIR-LLM ni las apruebo aquí; todas las
  IDs que citan existen y el contenido es coherente, pero son cambios de rumbo
  que debe firmar el líder.
