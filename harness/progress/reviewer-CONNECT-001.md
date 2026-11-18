# reviewer · CONNECT-001

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

# Reviewer · CONNECT-001

## Ejecutado en esta sesión (no leído del informe)

- `uv run python -m agents --json run harness gate` → `"success": true`, `155 passed` (gate corre `pytest tests/`).
- `uv run pytest -q` → `684 passed, 15 skipped in 91.07s`.
- `uv run pytest -q tests/test_practicas.py` → `19 passed in 1.94s`.
- `uv run ruff check tribal tests agents` → `All checks passed!`; `ruff format --check` → `41 files already formatted`; `mypy tribal tests` → `Success: no issues found in 41 source files`.
- `review_package` → `success true`, 8 hallazgos (3 estructurales + 5 deep), 1 grupo de duplicación.
- `test coverage_report` → `95.6%` total; `instinto.py` 100%, `acciones.py` 93.5%, `sim.py` 97.5%.
- `secrets scan` → 13 hallazgos, **todos** en `agents/tests/` (fixtures sintéticos preexistentes; `agents/` no entra en este diff).
- `doctor checkup` → 7/7.

## Criterios

### 1. Una práctica del instinto por rama — CUMPLIDO
- `tribal/sim.py:68-76` mapea 7 verbos a las 5 ramas: `comer/tallar→litica`, `frotar_madera→fuego`, `hablar→lenguaje`, `ensenar/cuidar→roles`, `pintar→simbolico`.
- `tribal/agents/instinto.py:60-71` solo elige prácticas en el tramo ocioso (`if not _urgente`) y rota con `(id + tick) % len(disponibles)`; con urgencia devuelve beber/comer/descansar/moverse/huir.
- Efectos reales, no decorativos: `tallar` −0.5 energía, `frotar_madera` −1.0, `pintar` −0.2, `cuidar` +0.5 salud al atendido/−0.2 al cuidador, `hablar` puede transmitir una habilidad (`acciones.py:295-303`). Con test directo para hablar y cuidar (`tests/test_practicas.py:221-237`) y para la ausencia de práctica con urgencia (`:134-142`).
- Partida real (12 individuos, 600 ticks, calma): seed 42 → `litica 5, fuego 5, lenguaje 4, roles 7, simbolico 6`; seed 7 → `5/5/4/2/7`; seed 123 → `5/5/4/7/7`. Seed 2026 tarda: roles 0 a 600 ticks, pero a 1500 y 3000 las cinco ramas están. Ninguna rama queda inalcanzable por requisitos.
- Determinismo: `test_dos_procesos_dan_la_misma_salida_con_practicas` compara dos procesos y pasa; la rotación por `(id+tick)` no introduce orden dependiente de hash.

### 2. Combinación distinta de `raedera` alcanzable — CUMPLIDO
- `test_un_nodo_combinacion_distinto_de_raedera_es_alcanzable_en_partida` (seed 42, 600 ticks, `crisis=True`) exige `canto_ritual` con origen `combinacion` y `proto_palabras`/`ritual` activos. Pasa.
- No está inyectado: el único camino que crea combinaciones es `Simulacion._intentar_combinacion` → `grafo.descubrir(..., origen="combinacion")` (`tribal/sim.py:309-321`); `tradiciones` solo añade `tradicion_*` y `Grafo.avanzar` solo recorre `ARBOL`.
- Prueba de reversión que hice yo: sustituyendo `PRACTICAS` por solo `{comer→litica}`, misma seed 42 y crisis, aparecen únicamente `raedera` y `proto_palabras`/`ritual` quedan inactivos. Es decir, el test falla si se revierte CONNECT-001: no es un test amañado.
- Otras semillas, 600 ticks con crisis: seed 7 → `canto_ritual` tick 91; seed 123 → tick 31; seed 2026 → tick 17. Además salen los cinco cruces (`raedera`, `cuchillo_al_fuego`, `canto_ritual`, `caceria_dirigida`, `turnos_de_vigilia`).

### 3. La puerta F1→F2 documenta qué ramas avanzan y cómo — CUMPLIDO
- `vault/01_PROYECTO/arquitectura.md:388-418` (§9.1) tiene la tabla rama → verbo → condición → efecto y explicita que la proporción divergente es de DIVERGENCIA-002/EMER-001 y el >50 % de Fase 3. `README.md:106-144` tiene la misma tabla y la nota de alcance.
- Verificado contra ejecución: las cinco ramas avanzan en calma; los cinco cruces son alcanzables en 600 ticks con crisis; `pct_fuera_arbol` 14.8 (seed 42, calma) y 30.3 (seed 42, crisis). Las cifras del README coinciden con la corrida real.
- La frase del criterio es verificable: no promete que la puerta completa esté pasada, solo el material (ramas y cruces).

### 4. `uv run pytest -q` y gate — CUMPLIDO
- `684 passed, 15 skipped`; `harness gate` → `"success": true`, `ENTORNO LISTO — se puede trabajar.`, `155 passed`.

## Bloqueantes

Ninguno.

## No bloqueante

1. **Criterio 3 desactualizado en el backlog (dueño: `harness`).** `harness/featureslist.json:543` y `harness/progress/current.md:16` todavía dicen «documenta que en F1 solo avanza la litica». La documentación y la ejecución demuestran lo contrario (avanzan las cinco ramas). No lo puede corregir el implementer; el líder debe actualizar el criterio con `harness` antes de `finish` para que el histórico no afirme algo falso.
2. **`README.md:133`** afirma que `pct_fuera_arbol` «ya no es cero». Contradicción reproducible: seed 2026, 600 ticks, calma → `pct_fuera_arbol = 0.0` (sin tradiciones todavía). Conviene matizar («puede ser > 0 cuando aparecen tradiciones»). No afecta a las ramas ni a los verbos.
3. **`vault/01_PROYECTO/arquitectura.md:400`** dice que `hablar` «transmite una habilidad»; el verbo puede no prender (probabilístico) y la rama avanza igualmente. El README (`:124`) lo dice bien: «puede transmitir». Alinear la tabla de arquitectura.
4. **`tests/test_practicas.py:116-121`** comprueba qué verbo elige el instinto, pero no afirma el coste de energía de `tallar`/`frotar_madera`/`pintar`. Añadir tres aserciones directas evitaría que una implementación futura los deje decorativos sin romper tests.
5. **`candidato_a_cuidar`** incluye crías con salud 100: se paga −0.2 de energía sin ganancia de salud (solo avanza la rama). Es coherente con «la técnica gasta», pero conviene decidir si se quiere evitar el gasto inútil cuando roles ya está completo.
6. **Complejidad:** `review_package` marca `instinto.elegir` (12 ramas) y `sim.step` (78 líneas) por encima del umbral. No rompe nada ni lo pide el criterio; si se toca, extraer el tramo ocioso a un helper.
7. **`secrets scan`** devuelve 13 hallazgos, todos en `agents/tests/test_redaction.py` y `test_secrets_agent.py` (claves AWS/PEM sintéticas de fixtures). Preexistentes y fuera del alcance de CONNECT-001; además falta `detect-secrets`.
8. **Informe del implementer:** atribuye a CONNECT-001 todo el cambio de `tests/test_arbol.py`, pero el diff también relaja `pct_fuera_arbol == 0.0` y exige `interaccion >= 1` (base EMER-001). No es un fallo funcional; sí conviene que el informe no mezcle alcances.
9. **`harness/progress/current.md:21`** sigue con la bitácora «(pendiente)». La evidencia está en `implementer-CONNECT-001.md`, pero la bitácora viva no se actualizó.
