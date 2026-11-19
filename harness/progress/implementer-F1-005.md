# implementer · F1-005

- **Fecha:** 2026-11-19
- **Veredicto:** needs-info

## Ronda 6d: horizonte de migración (≥11 tiles) — la puerta pasa a N=12

### Cambio mínimo

`DISTANCIA_MINIMA_MIGRACION` pasa de 6.0 a **11.0**: en crisis el parche nuevo
cae fuera del horizonte del conformista (4 tiles) y dentro del divergente (14).
Si un mapa no tiene casilla válida a esa distancia, `_reubicar` no migra ese
parche (no se fuerza un salto imposible). En calma no hay migración (el parche
se regenera en el sitio, ronda 6c); `migracion=false` sigue apagándola en ambos
regímenes. No se tocaron percepciones, rasgos ni constantes de fitness.

### Test y mutación

- `test_la_migracion_en_crisis_deja_el_parche_fuera_del_horizonte_conformista`:
  el parche migrado queda a **≥10 tiles** del centro viejo (el valor real es 11;
  el test usa 10 como cota robusta). Semilla 2 del `Mundo.azar`.
- Mutación: bajando la constante a 4, el mismo test **falla** (`9.49 >= 10.0`
  no se cumple) y el destino cae dentro del horizonte del conformista.
  Restaurado a 11, pasa. Es el guard del horizonte.
- `test_en_calma_el_parche_se_regenera_en_el_sitio_y_en_crisis_migra` sigue
  fijando que en calma no hay migración y el recurso vuelve donde estaba.

### Tabla N=12 (10 × 8000, default del juego)

```
seed | div% c->x | nac_div c/x | S_fec c/x | S_via c/x | desc/d c/x | desc/c c/x | imit/desc c/x | long_d c/x | long_c c/x | media c/x | sigma c/x | nac c/x | nodos c/x | pob c/x | ext
   1 |   0.0->  0.0 | 0.415/0.458 | -0.039/+0.003 | -0.053/-0.012 | 0.000/1.250 | 0.000/0.000 | 0.00/3103.00 | 0/3480 | 3040/3195 | 0.407/0.448 | 0.029/0.027 | 40/38 | 6/11 | 18/ 8 | 0/0
   2 |  26.3->  0.0 | 0.508/0.412 | +0.022/-0.042 | +0.011/-0.139 | 0.000/0.714 | 0.000/0.000 | 0.00/2660.80 | 0/2861 | 3046/2940 | 0.496/0.346 | 0.075/0.017 | 46/15 | 5/11 | 19/ 3 | 0/0
   3 |   0.0-> 10.0 | 0.504/0.529 | -0.053/-0.035 | -0.065/-0.044 | 0.000/0.278 | 0.000/0.000 | 0.00/2447.60 | 0/2839 | 2996/3010 | 0.504/0.524 | 0.026/0.051 | 20/42 | 2/10 |  4/10 | 0/0
   4 |   0.0-> 100.0 | 0.377/0.590 | -0.038/+0.129 | +0.000/+0.150 | 0.000/0.294 | 0.000/0.000 | 0.00/691.20 | 0/2778 | 2657/2717 | 0.000/0.595 | 0.000/0.024 | 10/14 | 6/10 |  0/ 6 | 1/0
   5 |   0.0-> 71.4 | 0.383/0.534 | -0.072/+0.064 | -0.120/+0.090 | 0.000/0.278 | 0.000/0.000 | 0.00/1393.40 | 0/2261 | 3239/2780 | 0.352/0.562 | 0.036/0.034 | 58/24 | 5/10 | 24/ 7 | 0/0
   6 |   3.1->  0.0 | 0.469/0.461 | -0.039/-0.026 | -0.050/+0.000 | 0.000/0.714 | 0.000/0.000 | 0.00/1437.40 | 0/2814 | 2788/2959 | 0.453/0.000 | 0.050/0.000 | 82/14 | 6/11 | 32/ 0 | 0/1
   7 | 100.0-> 93.3 | 0.617/0.603 | +0.018/+0.013 | +0.013/-0.005 | 0.000/0.122 | 0.000/0.000 | 0.00/504.20 | 0/2969 | 2740/2740 | 0.613/0.594 | 0.030/0.037 | 89/41 | 4/9 | 43/15 | 0/0
   8 |   0.0-> 88.9 | 0.000/0.519 | +0.000/+0.019 | +0.000/+0.111 | 0.000/0.312 | 0.000/0.000 | 0.00/1465.00 | 0/2940 | 3077/2898 | 0.000/0.612 | 0.000/0.054 | 0/26 | 4/10 |  0/ 9 | 1/0
   9 |   0.0->  0.0 | 0.362/0.381 | -0.014/+0.005 | -0.069/+0.001 | 0.000/2.500 | 0.000/0.000 | 0.00/9228.60 | 0/2607 | 2938/2915 | 0.311/0.380 | 0.020/0.050 | 29/51 | 9/14 |  8/21 | 0/0
  10 |   0.0->  0.0 | 0.372/0.443 | -0.032/+0.030 | -0.056/+0.073 | 0.000/1.000 | 0.000/0.000 | 0.00/2791.40 | 0/2994 | 2932/2890 | 0.355/0.484 | 0.015/0.022 | 25/28 | 5/11 |  9/ 6 | 0/0

S_fecundidad crisis>0: 7/10 | S_fecundidad calma<0: 7/10 | SENAL True
secundario div%: sube 4/10 | empata 3/10 | baja 3/10 | sube>=8/10 False | no baja False | crisis<=calma>=6/10 True | extinciones crisis<=calma True | PASA False
```

**Cumple a N=12 con la medida primaria:** crisis `S_fec > 0` 7/10, calma
`S_fec < 0` 7/10, crisis ≤ calma y extinciones crisis ≤ calma. El `div%`
secundario sigue sin pasar y no decide.

### Confirmación N=50

`--individuos 50` (solo parámetro de medición; default del juego 12):

```
S_fecundidad crisis>0: 9/10 | S_fecundidad calma<0: 6/10 | SENAL True
secundario: crisis<=calma>=6/10 False | extinciones crisis<=calma False | PASA False
```

La señal S **se refuerza** con N=50 (crisis 9/10, calma 6/10), así que no es
deriva. Pero **crisis ≤ calma no se replica** (4/10) y hay una extinción en
crisis (semilla 5): la condición de régimen favorable depende de la escala. Se
documenta como salvedad; la puerta se mide con el N=12 del juego. La tabla
completa de 50 está en el README.

### Verificación

```text
$ uv run ruff check tribal/ tests/ agents/
All checks passed!
$ uv run ruff format --check tribal/ tests/
47 files already formatted
$ uv run mypy tribal/ tests/
Success: no issues found in 47 source files
$ uv run pytest -q
770 passed, 15 skipped in 198.35s (0:03:18)
$ ./init.sh
━━ ENTORNO LISTO ━━  0 aviso(s)
pytest 241 passed in 134.68s (0:02:14)
$ uv run python -m agents --json run harness gate
"success": true, "message": "ENTORNO LISTO — se puede trabajar.",
"ready": true, "errors": 0, "warnings": 0
```

### Qué falta

- Decisión del líder: la puerta cumple a N=12 con S; N=50 confirma S pero no
  crisis ≤ calma. No se tocó nada más; no hay commit.
- No se commiteó; no se tocó el backlog ni `current.md` a mano.
