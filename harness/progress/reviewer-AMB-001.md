# reviewer · AMB-001

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

## Criterios

1. **Parches que se agotan y migran / estación — CUMPLIDO.** El bloqueante B1 de la ronda 1 está cerrado. Caso reproducido en `modulo_mundo.crear(seed=42)`: un parche de BAYAS agotado migra (`migrados=[(4, 'BAYAS')]`), cambia de coordenadas (`[(6,2),(6,3),(4,4),(6,4),(8,4),(5,5),(7,5)]` → `[(17,7),(17,8),(15,9),(17,9),(19,9),(16,10),(18,10)]`), se rellena a capacidad (4/4 por fuente), todas sus fuentes caen en casilla pisable y el centro en BOSQUE, a 12.14 tiles del centro viejo. Barrido propio (agotando a mano **todos** los parches de comida): 60×34 y 80×50 × seeds 1, 2, 3, 5 y 42 → **todos los parches de comida migran (11-14 de 11-14), ambos tipos**, 0 migraciones de agua, 0 fuentes no pisables, 0 fuera del mapa, todas rellenas y distancia nuevo-viejo ≥6 en los 10 casos. `max fuentes por casilla` = 1 (no se apilan): distancia mínima entre fuentes de bayas 1.0, de caza 1.41-13.04. Determinista por semilla: `misma semilla → mismas posiciones` (True en los dos tipos) y 7 destinos distintos con 7 semillas. Estación sin cambios y ya verificada: invierno aplica factor 0.5 y frena la regeneración de verdad.
2. **Test de mecanismo — CUMPLIDO.** `_superviviente` fija `sexo="m"`, `Genoma()` y ahora ambos arrancan en la misma casilla (4.5, 4.0), con `assert` explícitos de posición, genoma y sexo. Mutaciones ejecutadas por mí: «quedarse = seguir» → CAE («el que patrulla la zona agotada no murió»); «quedarse clonado» → CAE; «sin migración» → CAE; «migra pero sin comida» → CAE. Sin mutación, PASA.
3. **Resumen — CUMPLIDO.** `estacion`, `parches` con `id`/`tipo`/`activo`/`abundancia`/`x`/`y` y `migraciones`; `_parches()` calcula `abundancia()` una vez por parche. Verificado en salida real (seed 42, 600 ticks, estaciones de 150: `poblacion 12 -> 13`, `estacion primavera  parches 17  migraciones 4`).
4. **Dos subprocesos / otra semilla — CUMPLIDO.** Dos `python -m tribal run --ticks 1200 --config` con la misma config: JSON idéntico (7154 bytes). Semilla 1 vs 2: `migraciones 4 / 3` y posiciones (`tipo, x, y, abundancia`) distintas; en esa partida migran bayas **y** caza.
5. **pytest y gate — CUMPLIDO.** Gate `success=true`, `ready=true`, 0 errores, 0 avisos, `pytest 206 passed in 59.12s`. Suite completa `735 passed, 15 skipped in 123.30s`. `ruff check` / `ruff format --check` / `mypy` verdes (45 ficheros).

## Bloqueantes

Ninguno. B1 (bayas que no migraban) resuelto: el filtro fuente a fuente con `DISTANCIA_ENTRE_FUENTES = 1.0` y el barajado con `Mundo.azar` hacen viable la migración en el bosque sin apilar fuentes ni pisar agua, y hay test que lo cubre en el mundo real.

## No bloqueante

- `_reubicar` sortea **todas** las casillas del terreno en cada migración (`shuffle` de ~700-1900 elementos). A 0.57 ms/tick no se nota; si el mapa crece, sembrar unos pocos candidatos al azar bastaría.
- El destino solo exige `pisable` para las fuentes: una fuente puede quedar sobre terreno distinto al del centro (p. ej. bayas fuera del bosque). El centro sí cae en el terreno que toca y el README lo dice así.
- Con el filtro de 1 tile, dos parches pueden quedar solapados en el espacio (no en la misma casilla). Es consecuencia buscada del arreglo; si se quiere separación visual, es eje de presentación, no del criterio.
- `review review_package` sigue marcando `config.validar` (68 líneas/16 ramas) y `sim.step` (101). Preexistente y ya anotado por el implementer.
- `test_la_migracion_es_determinista_y_depende_de_la_semilla` solo exige ≥2 destinos distintos entre 6 semillas; mi comprobación da 7 de 7, pero el `assert` podría ser más fuerte.
- `secrets scan`: 13 hallazgos, todos fixtures preexistentes de `agents/tests/` (redaction y secrets), ninguno de este diff.
- Sin `.tmp-*`; `git diff tests/` razonable (dos ficheros con las claves nuevas y el fichero nuevo de 505 líneas). El renombrado de `test_los_defaults_son_los_de_fase_0` está justificado porque los defaults cambiaron.

## Comprobaciones propias

- **Fase 0 sin regresión:** con `migracion=false` y `ticks_por_estacion=0`, 400 ticks y dos seeds (7 y 3): 37 claves comunes idénticas a HEAD, solo difiere el bloque `config` (claves nuevas). El `shuffle` de la migración no toca el camino apagado.
- **Render / 60 fps:** frame de 480×286 en invierno con tinte y marcador gris `(96, 96, 96)` en el parche agotado; 486-498 fps en driver dummy (300 frames); `tests/test_render.py` y `tests/test_motor.py` verdes; `benchmark: 0.57 ms/tick, cabe en 16.67 ms`.
- **Guard DIVERGENCIA-002:** `tests/test_divergencia_calma.py` 16 passed.
- **Docs al día:** la salida JSON de 600 ticks del README es **byte a byte** la real (7176 caracteres, comparadas), y el ejemplo de estaciones de 150 coincide (`migraciones 4`, `poblacion 12 -> 13`). `INTENTOS_REUBICAR` ya no aparece en el repo.
- **Config:** sin cambios respecto a la ronda 1 (validación de `migracion`, `ticks_por_estacion >= 0`, `umbral_agotamiento` en (0, 1] con mensajes clave+valor y exit 2).
