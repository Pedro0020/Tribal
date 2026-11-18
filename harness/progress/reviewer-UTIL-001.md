# reviewer · UTIL-001

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

# reviewer · UTIL-001

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

## Puerta (ejecutada en esta sesión)

`uv run python -m agents --json run harness gate` → `success: true`,
`ENTORNO LISTO`, 14 checks `ok`, `pytest | 186 passed in 48.87s`.

## Criterios

1. **Utilidad = función del estado, no multiplicador fijo — CUMPLIDO.**
   `tribal/culture/beneficios.py` implementa
   `utilidad = 1 + efecto_nominal_desviado · escasez · densidad`.
   - `escasez_de` sale del mundo real: `1 - Σcantidad/Σcapacidad` por tipo,
     acotada a [0,1]; no hay constante. Verificado contra una corrida real de
     5000 ticks (crisis, seed 42): JSON `escasez` = `{agua: 0.5, bayas: 0.833,
     caza: 0.688}` y las cuentas independientes sobre `sim.mundo.recursos`
     (`120/120`, `26/156`, `5/16`) dan exactamente `0.500/0.833/0.688`.
   - Abundancia ⇒ utilidad 1.0 exacta: `utilidad("raedera", lleno, 1) == 1.0`.
     En la corrida de calma la media medida es `1.0000` (máximo instantáneo
     `1.0023` en ticks con la reserva recién mordida).
   - Densidad con portadores reales: `portadores()` cuenta vivos que saben la
     habilidad. Corrida real: raedera 15 de 16 portadores ⇒ utilidad 1.0833 en
     vez del nominal 1.25; con 0 portadores y escasez 0.75 da 1.1875
     (1 + 0.25·0.75/1.0), o sea la densidad del que la sabe, no una constante.
   - El efecto nominal se conserva en `EFECTOS` y el validador de importación
     exige una sola dimensión, recurso y habilidad por nodo.

2. **Misma semilla: calma no mueve, crisis sí — CUMPLIDO (con matiz de
   métrica, ver no bloqueantes).**
   Tabla reproducida por mí, independiente del informe, 7 semillas (media de
   energía de 3000 ticks, 1 adulto, sin depredadores):

   ```
   seed | calma sin/con/dif      | crisis sin/con/dif
      1 |  61.42  61.42  +0.00 |  61.42  63.37  +1.95
      2 |  59.79  59.79  +0.00 |  59.80  64.42  +4.63
      3 |  60.71  60.71  +0.00 |  60.71  63.29  +2.58
      4 |  59.80  59.80  +0.00 |  59.80  62.71  +2.90
      5 |  60.28  60.28  +0.00 |  60.28  64.82  +4.53
   media|                +0.00 |                +3.29
   ```

   No es artefacto: el brazo "sin nodo" no tiene la habilidad, así que
   `conocidos(grafo, set(), utilidades)` devuelve `Beneficios()` todo a 1.0 —
   el grafo activo por sí solo no reparte nada. No hay canal alternativo: en el
   escenario no hay crisis de config (`crisis=False`), el temperamento 0.5 es
   neutro (no experimenta: `intentos_divergentes=0` en las cuatro ramas) y solo
   cambia el multiplicador de bayas. El individuo no muere de hambre en ningún
   brazo (salud 100, energía mínima 35-38); muere de longevidad en el último
   tick, igual en ambos brazos.

3. **Resumen con `utilidad_media` y el estado que la modula — CUMPLIDO.**
   `Simulacion.resumen()` publica `utilidad_media` (media de la utilidad
   aplicada por nodo y tick activo), `escasez` por recurso y `estacion`.
   Recalculé la media yo mismo tick a tick sobre una corrida real de 5000 ticks
   en crisis y coincide con `resumen` (diferencia de 1e-4 por redondeo en un
   nodo): `{cuchillo_al_fuego: 1.0638, canto_ritual: 0.9756,
   turnos_de_vigilia: 0.8245, raedera: 1.0868, caceria_dirigida: 1.19}`.
   `resumen.beneficios` del final (1.0833 bayas) es coherente con la utilidad
   final de raedera, no con el nominal. `tests/test_cli_run.py` amplía el
   contrato de claves. En calma sin combos, `utilidad_media` es `{}`: honesto,
   no hay nodo que promediar.

4. **La utilidad no depende del temperamento — CUMPLIDO.**
   Reproducido con divergencia 0.1, 0.5 y 0.9, misma habilidad y mismo mundo:
   energía 86.818181…, `bayas` 1.1704545…, idénticas en los tres. AST sobre
   `beneficios.py`: no hay ningún `Name` ni `Attribute` llamado `divergencia`,
   no se toca `genoma`, no se importa `genoma`; las únicas apariciones son en
   prosa del docstring. `utilidad()` recibe `Situacion` y un int de portadores,
   no un individuo. El guard de DIVERGENCIA-002
   (`test_el_rasgo_solo_se_lee_donde_es_conducta`) sigue verde.

5. **pytest y puerta — CUMPLIDO.**
   `uv run pytest -q` → `715 passed, 15 skipped in 114.76s`.
   `ruff check` → All checks passed; `ruff format --check` → 44 files already
   formatted; `mypy` → no issues in 44 files. Gate verde (arriba).

## Mutaciones (las hice yo, no las leí)

- `escasez_de ≡ 1.0` (equivale a volver al multiplicador fijo): calma pasa a
  **+4.40** en las 7 semillas ⇒ `test_en_calma_el_invento_no_mueve_la_energia`
  falla. El umbral de calma está realmente atado a la fórmula.
- `escasez_de ≡ 0.0`: crisis **+0.00** ⇒ falla la aserción de crisis
  (`d > 0.5` y media > 1.5). El premio en crisis no viene de otra vía.
- Ninguna de las dos mutaciones se escapa: los dos lados del test muerden.

## Regresiones

- Determinismo: dos `run --headless --json --ticks 400 --seed 7` producen JSON
  byte a byte idéntico.
- `test_motor.py::test_importar_el_motor_no_carga_pygame` verde: el motor no
  arrastra pygame.
- Presupuesto de frame (`test_cli_run.py::test_benchmark_cabe_en_el_presupuesto_de_frame`)
  verde; en una corrida real de crisis con 16 individuos `ms_tick_medio = 0.61`
  (presupuesto 16.67 ms para 60 fps).
- Cobertura (agente `test coverage_report`): total 95.6 %,
  `beneficios.py` 91.1 %, `sim.py` 97.8 %, ningún módulo bajo 60 %.
- `secrets scan`: 13 hallazgos, todos en `agents/tests/test_redaction.py`
  (9) y `agents/tests/test_secrets_agent.py` (4), fixtures preexistentes; nada
  en `tribal/` ni en el diff.
- `doctor checkup`: 7/7.

## Higiene y alcance

- Raíz limpia: no quedan `.tmp-medir.py`, `.tmp-probe*.py` ni `.tmp-tabla.py`.
  Mis propias sondas viven en `%TEMP%\opencode\`, fuera del repo.
- Diff acotado a `beneficios.py`, `sim.py`, docstring de `acciones.py`, los
  tests afectados, `test_utilidad.py` nuevo y README. Sin reformateos ni
  refactors ajenos. `acciones.py` solo cambia docstring.
- `harness/featureslist.json` y `current.md` los mueve `harness` (`start`), no
  el implementer: correcto.

## Bloqueantes

Ninguno.

## No bloqueante

1. **El ejemplo de README de 600 ticks ya no es una salida real, y ahora es un
   híbrido.** Dice `poblacion_final: 15, nacimientos: 3, media_energia: 70.22,
   imitaciones: 764`, pero la corrida actual (`run --headless --ticks 600
   --json`) da `13, 1, 66.58, 522`. Los campos añadidos por esta feature
   (`escasez: 0.179/0.312`, `estacion: null`) sí son de la corrida real. La
   parte obsoleta viene de antes de FIX-ENERGIA, pero el implementer tocó esa
   línea y la dejó internamente incoherente: regenerar la línea entera o
   quitar la coletilla de "salida real".
2. **El criterio dice "supervivencia" y el test mide energía media.** En el
   escenario controlado (un adulto, sin depredador, salud siempre 100) la
   supervivencia es binaria e idéntica en ambos brazos, así que la energía es
   el único canal que puede moverse; el docstring lo justifica. Si se quiere
   literalidad, falta un escenario con umbral de inanición o varios individuos
   donde la diferencia se lea en `poblacion_final`/`muertes`. El docstring dice
   además "sin vejez" y el adulto alcanza la longevidad justo en el tick 3000:
   detalle, no afecta a la media de ticks 1-2999.
3. `sim.step` pasa de ~81 a 90 líneas (`review_package` lo marca, umbral 60).
   El bloque de situación se puede extraer a un método `_situacion_del_tick()`;
   hoy no rompe nada y el resto de olores que reporta `review_package`
   (`build_parser`, `_mancha`, complejidad de `aplicar`/`elegir`, duplicado
   `tallar`/`frotar_madera`) son preexistentes.
4. `Situacion.estacion` es una abstracción anticipada (siempre `None`). Está
   pedida por el criterio y documentada como gancho en el docstring del módulo,
   en el campo, en el README y en una aserción del test; queda claro que **no**
   está implementada. Cuando llegue AMB-001 conviene que su test exija que
   module de verdad, no solo que exista.
5. `escasez_de` devuelve 0 si no hay fuentes del tipo (mundo sin caza ⇒ cazar
   no vale nada). Es una decisión razonable y está documentada, pero es una
   regla de diseño que nadie más comprueba: un test de «tipo sin fuentes ⇒
   utilidad 1.0» la fijaría.
6. `opencode.json` aparece modificado en el árbol (modelos por agente, mtime
   17:01) y no forma parte de la feature ni del informe del implementer: es
   configuración de la sesión. No debe entrar en el commit de UTIL-001.
7. `utilidad()` es pública y toma `portadores: int` en posición: fácil de
   llamar con el número de nodos activos en vez de portadores. Los tests lo
   cubren, pero un `portadores(mundo, nodo)` obligatorio en la firma habría
   hecho imposible el error.
