# reviewer · F2-004

- **Fecha:** 2026-11-19
- **Veredicto:** aprobado

## Criterios

1. **Saliencia sube por hitos y decae; independiente de divergencia — CUMPLIDO.**
   - Hitos conectados al motor: `primer_nodo` (`tribal/sim.py:734`), `combinacion` (`:695`), `tradicion` (`:341`), `ensenanza`/`rescate` (`:320-322`) y `crisis` (`_hito_crisis`, `:509`; llamada desde `step` en `:259`). Decaimiento al inicio de cada `step` (`:202-203`).
   - Independencia de divergencia: `tribal/agents/saliencia.py` solo suma/decae; cero lecturas de `genoma`, `divergencia`, `random` o `azar` (AST/grep). A mano, misma historia con 0.95 y 0.05 de divergencia → mismo valor exacto.
   - Nuevos tests que muerden: `test_el_motor_decae_la_saliencia_cada_tick` (200 `step()` sin hitos → `5.0*0.999**200`), `test_el_hito_de_crisis_llega_a_los_600_ticks_y_se_reinicia_al_salir` y `test_step_aplica_el_hito_de_crisis` (599 no, 600 sí, salir reinicia, y el tick llama al hito).
   - Mutación B (quitar el bucle `saliencia.decaer` del motor) → **FAILED** `test_el_motor_decae_la_saliencia_cada_tick` (5.0 != 4.093244). Mutación C (quitar `self._hito_crisis(en_crisis)`) → **FAILED** `test_step_aplica_el_hito_de_crisis` (0.0 != 0.5). `sim.py` restaurado con hash idéntico.

2. **Más hitos → más peticiones en la misma corrida — CUMPLIDO Y AISLADO.**
   - `test_la_saliencia_manda_frente_al_orden_de_la_lista`: ids 1/2/3, saliencia en el 3, `max_pensando=1`, 40 ticks → `pensamientos[3]==40`, ids 1 y 2 a 0. Es el caso que antes pasaba por accidente.
   - Mutación A (quitar `con_dilema.sort(key=(-saliencia, id))`) → **FAILED** `test_la_saliencia_manda_frente_al_orden_de_la_lista` (`KeyError: 3`: pensó el id 1). Restaurado con hash idéntico.

3. **Topes de pensando y en vuelo — CUMPLIDO.**
   - `_encolar_dilema` corta en `max_pensando` (`:375`) tras ordenar por saliencia; `ColaLLM.encolar` rechaza al llegar a `max_en_vuelo` (`cola.py:111`) y el bucle hace `break`. No elegidos → instinto.
   - Tests: 40 ticks con `max_pensando=2` → 80 peticiones y máximo observado 2; cola `max_en_vuelo=2` observado 1–2; `sum(pensamientos) == llm.peticiones` (1433 == 1433 en la corrida síncrona de 1200 ticks).

4. **`run --json --llm stub` reporta top y pensamientos — CUMPLIDO.**
   - `uv run python -m tribal run --headless --json --llm stub --llm-sincrono --ticks 1200` ejecutado dos veces: **JSON byte-idéntico**. Salida real: `top=[[5,0.657],[2,0.455],[8,0.304]]`, `pensamientos={2:1,3:287,5:173,6:1,9:307,10:2,11:360,12:298,13:4}`, `max_pensando=4`, `max_en_vuelo=0`; coincide exactamente con el ejemplo del README.
   - Sin LLM: bloque `saliencia` presente con `pensamientos={}` y sin clave `llm` (ronda 1).
   - El aviso del README sobre el asíncrono es correcto: dos corridas `--llm stub` (600 ticks) dieron 130 vs 112 peticiones y top distinto.

5. **Gate — CUMPLIDO.**
   - `success=true, ready=true, errors=0, warnings=0, 351 passed in 166.66s`.

## Bloqueantes

Ninguno. Las tres mutaciones B1/B2/B3 caen y `tribal/sim.py` queda restaurado con sha256 `F11DE7E4234E6847F4254236EDC7FBA98E44090C54FCEEE0C9DEF37D3BEBE248` idéntico al original.

## No bloqueante

- **`opencode.json` (inyectado por el entorno): modificado, NO staged.** Contiene un `Authorization: Bearer pixl_…` en claro. No forma parte de F2-004 y no se incluyó en la revisión. **Ojo:** `git commit_feature` ejecuta `git add -A` (`agents/agents/git_agent.py:411`), así que el líder debe excluirlo/restaurarlo antes de cerrar o el token acabaría commiteado.
- **`docs/art/` aparece como untracked** (hojas PNG, `make_sheets.py`, `_tmp_tilesets.png`), ajeno a F2-004; `git add -A` también lo arrastraría. No incluido en la revisión.
- `secrets scan`: 13 hallazgos, todos en `agents/tests/test_redaction.py` (9) y `agents/tests/test_secrets_agent.py` (4), fixtures preexistentes; nada en el código nuevo.
- `review_package`: funciones largas preexistentes (`sim.step` 164 líneas); sin duplicación nueva.
- `coverage_report` no completó en la ronda 1 (timeout 600 s); no aportó dato.

## Regresiones

- Suite completa: **907 passed, 15 skipped in 242.39s**.
- `ruff check tribal tests agents` limpio; `ruff format --check` 68 ficheros; `mypy` sin issues.
- F2-002/003 intactos (sus tests dentro de la suite); test de 60 fps `ms_tick_medio < MS_FRAME` en verde.
- Sin dependencias nuevas ni `pyproject.toml` tocado; sin ficheros `.tmp-*` de la feature.
