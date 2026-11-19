# implementer · F1-006

- **Fecha:** 2026-11-19
- **Veredicto:** ok

## F1-006 · Puerta F1→F2 medida en la descendencia

### Veredicto primario

`report gate-f1` separa ahora explícitamente **primaria** (`senal`/`primaria`,
S_fecundidad) y **secundaria** (div%, antes `pasa`, que ya no existe como clave
que pueda confundirse con el veredicto). Texto legible y JSON.

**PRIMARIA True:** `S_fec > 0` en crisis **7/10** y `S_fec < 0` en calma
**7/10**. Crisis ≤ calma y extinciones crisis ≤ calma: sí. El `div%` sigue
publicado como secundario (4/10) y no decide.

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

VEREDICTO PRIMARIO (S): S crisis>0 7/10 | S calma<0 7/10 | PRIMARIA True
SECUNDARIO (div%, no decide): sube 4/10 | empata 3/10 | baja 3/10 | sube>=8/10 False | no baja False | crisis<=calma>=6/10 True | extinciones crisis<=calma True | SECUNDARIA False
```

### Criterios

1. **Métricas publicadas** por semilla/brazo: S_fecundidad, S_viabilidad,
   `nac_div`, descubrimientos por divergente/conformista registrado, tasa de
   imitación, longevidad de descubridores/conformistas, media/σ y `div%`
   secundario. JSON con las mismas claves.
2. **S_fecundidad:** crisis > 0 en 7/10; calma < 0 en 7/10. Primaria True.
3. **Crisis no favorable:** población crisis ≤ calma en ≥6/10 y extinciones
   crisis ≤ calma. Ambas verdaderas a N=12.
4. **Mecanismo:** 6 tests verdes (descubridor rinde más con 0.1/0.5/0.9;
   descubrir enseña la habilidad; divergente sin descubrimientos = conformista).
5. **Guard y memoria condicional:** guard AST, snapshots y lista blanca verdes;
   memoria precisa sin migración, obsoleta con migración.
6. **Barrido en informe, README y arquitectura** con `div%` secundario y por qué
   no decide (12 fundadores → proporción binomial ruidosa).
7. **`pytest -q` y gate:** verdes.

### Mutaciones re-ejecutadas

- **Memoria condicional:** `_memoria_vigente` forzada a `True` →
  `test_la_informacion_del_conformista_es_precisa_si_el_parche_no_migra` falla.
  Restaurada, pasa.
- **Descubrimiento:** quitado `individuo.habilidades.aprender(...)` →
  `test_descubrir_es_lo_que_ensena_la_habilidad_y_de_ahi_viene_la_ventaja`
  falla. Restaurado, pasa.
- **Guard:** lectura de `individuo.genoma.divergencia` en `acciones.comer` →
  `test_el_rasgo_solo_se_lee_donde_es_conducta` falla. Restaurado, pasa.
- **Horizonte:** `DISTANCIA_MINIMA_MIGRACION=4` →
  `test_la_migracion_en_crisis_deja_el_parche_fuera_del_horizonte_conformista`
  falla (9.49 < 10). Restaurado a 11, pasa.
- **Calma sin migración:** hacer migrar en calma →
  `test_en_calma_el_parche_se_regenera_en_el_sitio_y_en_crisis_migra` falla.
  Restaurado, pasa.

### Salvedad N=50

`--individuos 50` refuerza la señal S (crisis 9/10, calma 6/10, primaria True)
pero **no replica crisis ≤ calma** (4/10) y hay una extinción en crisis. La
condición de régimen favorable es dependiente de escala; la puerta se mide con
el N=12 del juego (concepto §1b) y la salvedad queda en README/arquitectura.
No se ajustó nada para ocultarla.

### Verificación literal

```text
$ uv run ruff check tribal/ tests/ agents/
All checks passed!
$ uv run ruff format --check tribal/ tests/
47 files already formatted
$ uv run mypy tribal/ tests/
Success: no issues found in 47 source files
$ uv run pytest -q
770 passed, 15 skipped in 196.86s (0:03:16)
$ ./init.sh
━━ ENTORNO LISTO ━━  0 aviso(s)
pytest 241 passed in 135.27s (0:02:15)
$ uv run python -m agents --json run harness gate
"success": true, "message": "ENTORNO LISTO — se puede trabajar.",
"ready": true, "errors": 0, "warnings": 0
```

### Qué falta

- Nada bloqueante: la puerta cumple a N=12; N=50 es una salvedad documentada.
- No se commiteó nada; no se tocó el backlog ni `current.md` a mano.
