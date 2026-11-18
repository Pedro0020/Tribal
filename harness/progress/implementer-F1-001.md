# implementer · F1-001

- **Fecha:** 2026-11-18
- **Veredicto:** ok

## Qué cambié (ronda 2)

- `tests/test_genoma.py`: `fuerza` con media 0.6 en el caso de 100 nacimientos (distingue mutación relativa de absoluta) y nuevo `test_el_clamp_de_rango_actua_en_los_bordes` con progenitores 1.46/1.48 y 0.52/0.54 (rango + cota relativa). Nuevo `test_los_fundadores_tienen_varianza_y_es_determinista`.
- `tribal/core/mundo.py`: la generación fundadora sortea también fuerza, resistencia, inteligencia y salud (0.85–1.15) y divergencia (0.2–0.8) con `mundo.azar`.
- `tribal/agents/necesidades.py`: `factor_resistencia` simétrico, `1 + (1 - resistencia) * 0.4` → 0.5 da 1.2 y 1.5 da 0.8 (1.0 neutro).
- `tribal/agents/instinto.py` / `tribal/sim.py`: `deambular()` público; si `ensenar` no prende, el individuo deambula en el mismo tick en vez de quedarse clavado.
- `tests/test_habilidades.py`: resistencia simétrica (incluye 0.8 y 1.2), instinto no elige `ensenar` sin aprendiz válido y enseñanza fallida no inmoviliza.
- `README.md`: fundadores con varianza, resistencia simétrica, enseñanza fallida no clava, y salidas de ejemplo regeneradas.

## Criterios y verificación

1. **Clamp de rango** — `test_genoma.py::test_el_clamp_de_rango_actua_en_los_bordes`: con medias 1.47 y 0.53 exige `[0.5, 1.5]` y `abs(valor - media) <= media * 0.05`.
2. **Mutación relativa** — `test_cien_nacimientos_quedan_en_rango_y_la_media_se_mantiene`: `fuerza` con media 0.6; una mutación absoluta de 0.05 rompe la cota 0.6×0.05 = 0.03.
3. **Fundadores con varianza determinista** — `test_los_fundadores_tienen_varianza_y_es_determinista`: dos `mundo.crear(seed=42)` idénticos, >1 valor distinto en fuerza/resistencia/inteligencia/salud/divergencia y todo en rango.
4. **Resistencia simétrica** — `test_la_resistencia_es_simetrica_alrededor_de_1`: 1.0→1.0, 0.8→1.08, 1.2→0.92, 0.5→1.2, 1.5→0.8.
5. **Enseñanza sin coste cuando falla** — `test_el_instinto_no_elige_ensenar_sin_aprendiz` y `test_ensenar_fallido_no_clava_al_individuo` (semilla 0 falla el dado y el maestro cambia de posición).
6. **Sin regresiones** — `pytest -q`: 616 passed, 15 skipped; gate success=true.

Nota sobre el punto 4: `(1 - resistencia) * 0.2` daría [0.9, 1.1], no el [0.8, 1.2] pedido; uso coeficiente 0.4 para conservar el 20 % en ambos extremos que ya validaba la ronda anterior.

## Mutaciones comprobadas (todas en rojo, fichero restaurado por hash)

- Quitar el clamp de `_heredar_rasgo` → `1 failed, 5 passed` (`test_el_clamp_de_rango_actua_en_los_bordes`, valor 1.5435 > 1.5); hash restaurado `True`.
- `media * (1 + mutacion)` → `media + mutacion` → `2 failed, 4 passed` (100 nacimientos con media 0.6 y clamp); hash `True`.
- `ensenar` sin transferir (`return False`) → `2 failed, 16 passed` (transferencia e instinto); hash `True`.
- `BONUS_HABILIDAD = 0.0` → `1 failed, 17 passed` (+50 %); hash `True`.
- `factor_resistencia` neutral (`return 1.0`) → `1 failed, 17 passed` (simetría); hash `True`.
- Quitar el fallback de `sim.step` tras `ensenar` fallido → `1 failed, 17 passed` (no clava); hash `True`.

## Evidencia

`uv run pytest -q`:

```
616 passed, 15 skipped in 68.73s (0:01:08)
```

`uv run ruff check tribal/ tests/ agents/`:

```
All checks passed!
```

`uv run ruff format --check tribal/ tests/`:

```
31 files already formatted
```

`uv run mypy tribal/ tests/`:

```
Success: no issues found in 31 source files
```

`uv run python -m agents --json run harness gate`:

```
"success":  true,
"message":  "ENTORNO LISTO — se puede trabajar.",
"check":  "pytest",
"detail":  "87 passed in 7.82s"
```

`uv run python -m tribal run --headless --json --ticks 3000` (media_genes con varianza inicial):

```
{"seed": 42, "ticks": 3000, "poblacion_inicial": 12, "poblacion_final": 30, "nacimientos": 29, "muertes": 11, "media_energia": 59.73, "media_sed": 38.23, "media_genes": {"velocidad": 0.995, "metabolismo": 1.085, "longevidad": 1.079, "fuerza": 1.037, "resistencia": 0.957, "inteligencia": 0.984, "salud": 1.011, "divergencia": 0.56}, "habilidades_distintas": 1, "habilidades": {"8": ["recolectar"], "13": ["recolectar"], "14": ["recolectar"], "15": ["recolectar"], "16": ["recolectar"], "17": ["recolectar"], "18": ["recolectar"], "19": ["recolectar"], "20": ["recolectar"], "21": ["recolectar"], "22": ["recolectar"], "23": ["recolectar"], "24": ["recolectar"], "25": ["recolectar"], "26": ["recolectar"], "27": ["recolectar"], "28": ["recolectar"], "29": ["recolectar"], "30": ["recolectar"], "31": ["recolectar"], "32": ["recolectar"], "33": ["recolectar"], "34": ["recolectar"], "35": ["recolectar"], "36": ["recolectar"], "37": ["recolectar"], "38": ["recolectar"], "39": ["recolectar"], "40": ["recolectar"], "41": ["recolectar"]}, "individuos_movidos": 41, "depredador": {"activos": 1, "ataques": 4, "muertes": 1}, "agrupamiento_max": 16, "huidas": 1254, "config": {"seed": 42, "individuos": 12, "ancho": 60, "alto": 34, "tasa_sed": 0.16, "tasa_energia": 0.15, "tasa_salud": 0.6, "cooldown_reproduccion": 600, "depredadores": 1, "depredador_activo": true}}
```

`./init.sh` sigue sin poder ejecutarse en este shell (no hay bash/WSL); `harness gate` ejecuta sus mismas comprobaciones y devuelve `success=true`.

## Qué falta

- `habilidades_distintas` sigue siendo 1 en la partida por defecto: no hay habilidades nuevas que aprender hasta F1-002/F1-003; las rutas de enseñanza/imitación ya están probadas.
- `divergencia` solo existe y se hereda; su efecto es de F1-003.
- La distribución de la mutación sigue siendo normal truncada a ±5 % (31 % de los hijos caen exactamente en el tope); es la nota no bloqueante que no se pidió cambiar.
