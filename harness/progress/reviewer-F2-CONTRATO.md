# reviewer · F2-CONTRATO

- **Fecha:** 2026-11-19
- **Veredicto:** aprobado

## Puerta (ejecutada en esta sesión)

`uv run python -m agents --json run harness gate` → `success: true`,
`ENTORNO LISTO — se puede trabajar.`, `pytest | 322 passed in 161.06s`
(init.sh ejecuta `tests/`; la suite completa se ejecutó aparte):

`uv run pytest -q` → **878 passed, 15 skipped in 230.02s**.

## Criterios

1. **CUMPLIDO.** La invariante es ahora 2–4 con al menos dos acciones viables
   y 1 solo en el borde sin terreno practicable. Reproducido por mí con un
   script independiente (temporal, borrado):
   ```text
   (100,0)  grass 24×24, sin recursos/vecinos/depredador:
            ['moverse', 'descansar']    _hay_dilema=False
   (45,60)  mismo mundo:
            ['descansar', 'moverse']    _hay_dilema=True
   (45,60)  mundo todo agua (sin tiles pisables):
            ['descansar']               _hay_dilema=False
   isla-1   hierba rodeada de agua, (100,0):
            ['pintar', 'descansar']     # 2, no borde
   ```
   Además, 20 estados aleatorios (necesidades, recursos, vecino, amenaza,
   hierba/bosque/agua): todos 2–4 salvo los 4 mundos todo-agua, que devuelven
   `['descansar']` y `_hay_dilema=False`. En los 20+3 comprobé viabilidad de
   cada candidata: `beber` solo con agua al alcance, `comer` solo con comida,
   `huir` solo con amenaza, `hablar` solo con vecino, `tallar`/`frotar_madera`
   solo con bosque, `pintar` con bosque u orilla, y `moverse` con `destino`
   pisable no nulo. `_hay_dilema(ind, mundo, opciones)` coincide siempre con
   `(sed_crítica ∧ energía_baja) ∨ salud_crítica` **y** `len(opciones) >= 2`;
   el test `test_el_dilema_sin_recursos_tambien_deja_dos_candidatas` lo muerde
   y el mundo sin pisables queda excluido.

2. **CUMPLIDO.** Dos few-shot por defecto (`test_el_payload_lleva_few_shot_estado_accion`,
   2 mensajes `assistant`), few-shot inyectable de 1 ejemplo
   (`test_el_payload_usa_los_ejemplos_del_cliente`) y `temperature: 0.3` en el
   cuerpo real (`test_el_payload_limita_el_enum_a_las_candidatas`).
   `ESQUEMA_RESPUESTA` de F2-001 sigue intacto para narración; `esquema_para()`
   solo cambia el enum.

3. **CUMPLIDO.** Válida no se corrige (`test_una_eleccion_valida_no_se_corrige`:
   elige `comer` con `[beber, comer]` y `corregida is False`); fuera de
   candidatas → corrige a la primera con motivo (`test_accion_fuera_de_candidatas...`);
   `huir` sin amenaza → corrige; transporte caído → `decision=None` y no se
   corrige. Correcciones tardías: `test_correccion_tardia_no_cuenta_como_corregida`
   (ventana 0, `drenar(1)` → `corregidas == 0`, `descartadas == 1`) y
   `test_correccion_aceptada_cuenta_como_corregida` (en ventana → `corregidas == 1`).
   `resumen()["llm"]` publica `corregidas` y el test de claves del CLI lo exige.

4. **CUMPLIDO (con la salvedad documentada).** `llm eval --backend simulado --json`
   → `escenarios: 20`, `aciertos: 20`, `acierto: 1.0`, `corregidas: 0`,
   `sin_decision: 0`; el test exige `> 0.70`. `--backend http` sin Ollama →
   `sin_decision: 2`, `acierto: 0.0`, exit 0 (no revienta). El backend
   simulado es una regla de utilidad, no el modelo: mide contrato/filtrado;
   está dicho en `eval.py`, README, `arquitectura.md` y el `--help`.

5. **CUMPLIDO.** 878 passed, 15 skipped; gate `success: true`; `ruff check
   tribal/ tests/ agents/` → All checks passed; `ruff format --check` de los
   11 ficheros tocados → ya formateados; `mypy tribal/` → sin issues.

## Integración F2-002 y alcance

- `tests/test_llm_cola.py` + candidatas/decision/eval: **36 passed** (cola,
  ventana, cierre sin hilos, 1200 ticks con backend de 200 ms, determinismo
  del stub síncrono entre procesos).
- Benchmark propio: población 12 → `1.18 ms/tick`; población 60 → `5.88 ms/tick`,
  ambos < `MS_FRAME` (16.67). El test de 60 fps sigue verde.
- `--llm off` idéntico a HEAD: mismo JSON para `--seed 42 --ticks 600`
  (hash 481326460 en ambos árboles); sin la clave `llm` en el resumen.
- Sin dependencias nuevas (`pyproject.toml` intacto), sin canales de fitness,
  sin `.tmp-*`. Diff limitado a los ficheros de la feature + tests + docs.

## No bloqueante

- Docstring de `sim._intencion_llm` desactualizado: sigue diciendo que
  `moverse`/`huir` sin parámetros lanzarían `ValueError` y menciona
  `_candidatas_llm`, función que ya no existe. El código sí resuelve ambos;
  corregir la prosa en el próximo toque.
- Borde de terreno: si el individuo está sobre un tile no pisable, se devuelve
  `['descansar']` aunque haya agua/comida/depredador al alcance (vi esto en un
  estado aleatorio todo-agua). Es un estado no alcanzable en la simulación
  normal, `_hay_dilema=False` y el instinto cubre el tick; si el borde quiere
  decir «sin ninguna acción posible» conviene documentar que ignora recursos y
  amenaza, no solo el movimiento.
- `corregidas` se cuenta en `drenar` al aceptar por ventana, no en
  `registrar_aplicada`: una respuesta corregida para un individuo que murió
  antes de aplicarse sigue sumando. Los tests de tardía/ventana pasan; aclarar
  si el contador debe ser de correcciones aceptadas o de acciones aplicadas.
- La candidata `moverse` lleva un `destino` orientativo, pero al aplicar
  `_intencion_llm` lo re-resuelve con `instinto.deambular` (correcto por la
  ventana de 180 ticks); conviene decirlo en el docstring de `Accion`/candidata.
- `arquitectura.md` abre con «Devuelve 2–4 acciones viables» y el borde se
  explica después; el README es más preciso («siempre que existan al menos dos
  acciones viables»). Un matiz de redacción.
- `_encolar_dilema` calcula `candidatas()` para todos los individuos cada tick
  (aunque no haya dilema); medido barato a 12/60, pero si la población crece
  conviene mirar las necesidades antes de barrer el mundo.
- `llm eval` sigue siendo circular por diseño (regla, no modelo); ya está
  documentado y no se usa como evidencia de precisión real.

## Mutaciones revisadas

- Nuevos: `tribal/llm/{candidatas,decision,eval}.py`, `tests/test_llm_candidatas.py`,
  `tests/test_llm_decision.py`, `tests/test_llm_eval.py`.
- Modificados: `tribal/llm/{esquema,cliente,cola}.py`, `tribal/sim.py`,
  `tribal/agents/instinto.py`, `tribal/cli.py`, `tests/test_llm_cola.py`,
  README y `vault/01_PROYECTO/arquitectura.md` §2.3.
- Sin dependencias nuevas, sin canales de fitness, sin `.tmp-*`; `--llm off`
  idéntico a HEAD; F2-002 (cola, cierre, determinismo, 60 fps) intacto.
