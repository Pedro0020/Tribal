# reviewer · F1-001

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

# reviewer · F1-001 · ronda 2

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

## Criterios

1. **genoma.py + habilidades.py — cumplido.** Ocho rasgos con defaults neutros (1.0 / divergencia 0.5) y `CATALOGO` exacto {cazar, recolectar, fabricar, fuego, ensenar} con su rama. `Genoma` reexportado desde `modelos` para no romper F0.
2. **Herencia media + mutación acotada y determinista — cumplido.** `media × (1 + clamp(N(0,0.05), ±5 %))` con clamp final a [0.5, 1.5] y azar de `Mundo.azar`. 100 nacimientos: medias dentro de ±0.03 del punto medio parental, signos simétricos. Determinismo comprobado en **dos subprocesos**: 600 ticks idénticos byte a byte, 3000 ticks idénticos, seed 43 distinta.
3. **100 nacimientos en rango y media mantenida — cumplido, y el test ya no es vacuo.** `fuerza` con media 0.6 (0.58/0.62) rompe una mutación absoluta; el caso de bordes (1.46/1.48 y 0.52/0.54) ejercita el clamp: 294/1000 hijos quedan exactamente en 1.5.
4. **Habilidades por enseñanza/imitación y efecto — cumplido.** +50 % real (40→60 bayas, 60→90 caza), sin bonus con la habilidad equivocada; la enseñanza transfiere la habilidad al aprendiz (no es un flag); la imitación pasiva aprende a ≤2 tiles y no a 9; resistencia simétrica (1.0→1.0, 1.5→0.8, 0.5→1.2, 1.2→0.92, 0.8→1.08); enseñar fallido ya no clava al individuo.
5. **Resumen con media de rasgos y nº de habilidades distintas — cumplido.** `media_genes` (8 claves), `habilidades_distintas`, `habilidades` por id en la salida real; con `INICIALES` vacío el contador baja a 0, no es constante. `habilidades_distintas: 1` es lo esperado: solo `ensenar` e `_imitar` crean habilidades y ambas exigen un superconjunto que hoy nadie tiene.
6. **gate success=true — cumplido.** `87 passed`, entorno listo; suite completa 616 passed, 15 skipped.

## Mutaciones ejecutadas (árbol real, restaurado y verificado por hash)
| Mutación | Resultado |
|---|---|
| quitar el clamp `[0.5,1.5]` de `_heredar_rasgo` | **1 failed** (`test_el_clamp_de_rango_actua_en_los_bordes`, 1.5435 > 1.5) |
| `media × (1+m)` → `media + m` | **2 failed** (100 nacimientos + bordes) |
| `ensenar` sin transferir (`return False`) | **2 failed** (transferencia + instinto) |
| `BONUS_HABILIDAD = 0.0` | **1 failed** (40 vs 60) |
| `factor_resistencia` → `1.0` | **1 failed** (simetría) |
| `SENSIBILIDAD_RESISTENCIA` 0.4→0.2 (extremos ±10 %) | **1 failed** |
| quitar el fallback `deambular` tras enseñar fallido | **1 failed** (`test_ensenar_fallido_no_clava...`) |
| quitar la varianza fundadora de los cuatro rasgos nuevos | **1 failed** (`test_los_fundadores_tienen_varianza...`) |

Los cinco ficheros mutados quedaron con el hash del original (`True` en los cinco).

## Fundadores
Misma semilla → genomas idénticos; semilla distinta → distintos; 12/12 fundadores únicos por partida; 0 valores fuera de rango en 50 semillas × 12 individuos.

## README y regresiones
- 600 ticks seed 42: README (55.8 / 39.4, ataques 1, muertes 0, agrupamiento 8, huidas 188) = ejecución de hoy. Idéntico.
- seed 7 benchmark: 47.61 / 49.94, ataques 1, agrupamiento 6, huidas 162 = ejecución de hoy. Idéntico.
- seed 2 a 3000 ticks: 22 / 22 / 12, 4 ataques, huidas 466, agrupamiento 14 = ejecución de hoy. Idéntico.
- `git diff tests/` sigue siendo solo las tres claves nuevas de `CLAVES`; `test_motor.py` intacto y en verde. Determinismo del resumen comprobado en 600 y 3000 (dos procesos). Benchmark 0.34 ms/tick frente a 16.67 de presupuesto; motor sin pygame.
- `ruff check`, `ruff format --check` y `mypy` en verde. Sin dependencias nuevas (`pyproject.toml` y `uv.lock` sin tocar) y sin cambios en `agents/`; `harness/` solo con lo que escriben `harness start`/`record`. `secrets scan`: 13 hallazgos, todos fixtures preexistentes de `agents/tests/`.

## No bloqueante
- El README dice "los siete funcionales entre 0.85 y 1.15", pero metabolismo y longevidad siguen en 0.85–1.20 (los tres rasgos de F0 conservan su rango). Es una frase, no una salida; las salidas del README sí coinciden.
- Persiste el comentario `sim.py`: "los tests de F0 fijan aquí el límite" — ningún test de F0 menciona `MUTACION`.
- 31 % de las mutaciones caen exactamente en el tope ±5 % (gauss recortada a 1σ); sigue siendo la nota de diseño ya aceptada.
- El benchmark del README (0.31) varía unas centésimas entre ejecuciones; hoy da 0.34. El propio README lo advierte.
