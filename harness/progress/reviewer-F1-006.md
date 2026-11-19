# reviewer · F1-006

- **Fecha:** 2026-11-19
- **Veredicto:** aprobado

## Criterios

1. **Métricas por semilla/brazo — cumplido.** `report gate-f1 --seeds 1-10 --ticks 8000`
   reproduce la tabla publicada con todas las columnas: `S_fec`, `S_via`, `nac_div`,
   `desc/d`, `desc/c`, `imit/desc`, `long_d`, `long_c`, `media`, `sigma`, nacimientos,
   nodos, población y extinciones. El JSON por brazo incluye las mismas claves
   (`S_fecundidad`, `S_viabilidad`, `mean_div_nacidos`, `tasa_descubrimiento_*`,
   `tasa_imitacion`, `longevidad_*`, `div_media`, `div_sigma`, etc.).

2. **S_fecundidad — cumplido.** Reproducido exactamente:
   `VEREDICTO PRIMARIO (S): S crisis>0 7/10 | S calma<0 7/10 | PRIMARIA True`.
   La primaria está separada de la secundaria en texto («VEREDICTO PRIMARIO (S)» frente
   a «SECUNDARIO (div%, no decide)») y en JSON (`senal`/`primaria` frente a
   `secundaria`; no existe la clave ambigua `pasa`).
   Aritmética comprobada a mano en la semilla 1: inicial `0.460245`; calma 37
   reproductores con media `0.421055` → S `-0.0392` (= `0.421055 - 0.460245`), con 18
   vivos; crisis 38 reproductores con media `0.463637` → S `+0.0034`, con 8 vivos. Es
   decir, S sale de **reproductores reales** (una vez por individuo), no de los vivos,
   y la base es la media inicial del brazo (idéntica en calma y crisis; el script lo
   verificó en ambos brazos). `mean_div_nacidos` también cuadra con la media de
   `_div_nacidos`.

3. **La crisis no es el régimen favorable — cumplido.** Población crisis ≤ calma en
   **6/10** (semillas 1, 2, 5, 6, 7, 10) y extinciones crisis 2 (4, 6) = calma 2 (4, 8).

4. **Test de mecanismo — cumplido.** `tests/test_puerta_f1.py` cubre descubridor vs no
   descubridor con la misma divergencia (parametrizado 0.1/0.5/0.9), que descubrir es
   lo que enseña la habilidad, que un divergente sin descubrimientos rinde igual que un
   conformista y que en calma explorar no mejora la energía. Los 5 tests pasan.

5. **Guard AST + snapshots + memoria condicional — cumplido.** Verdes
   `test_el_rasgo_solo_se_lee_donde_es_conducta`, `test_el_rasgo_no_se_escribe_en_runtime`,
   `test_temperamento_solo_se_llama_donde_es_conducta`,
   `test_las_funciones_de_conducta_no_editan_genoma_ni_necesidades` y
   `test_el_paseo_no_edita_genoma_ni_necesidades`. La lista blanca nueva
   (`sim._nacer`, `sim.resumen`, `sim._media_divergencia_inicial`, `gate_f1.medir_brazo`)
   es solo medición: leen el rasgo para publicarlo, no deciden aptitud.
   `test_la_informacion_del_conformista_es_precisa_si_el_parche_no_migra` fija la
   memoria condicional: sin migración la copia es válida aunque el parche esté vacío;
   con migración caduca. `DISTANCIA_MINIMA_MIGRACION = 11.0` deja el parche fuera del
   radio 4 y dentro del 14; el test exige ≥10 y las mutaciones lo confirman.

6. **Barrido publicado — cumplido.** La tabla 1..10 está en el informe, el README y
   `vault/01_PROYECTO/arquitectura.md` §9.3, con `div%` como columna secundaria y la
   explicación de por qué no decide (12 fundadores → proporción binomial ruidosa).
   README incluye además la confirmación N=50 y la salvedad de que no replica
   crisis ≤ calma. La tabla del README es idéntica a la reproducción salvo un espacio
   colapsado en la fila 7 (mismos valores; no bloqueante).

7. **pytest y gate — cumplido.** `uv run pytest -q` → **770 passed, 15 skipped**;
   `uv run pytest tests/` → 241 passed; `harness gate` → `success=true`,
   `ready=true`, 0 errores, 0 avisos (ejecutado dos veces en esta sesión: al empezar y
   tras restaurar las mutaciones).

## Mutaciones (las 5 caen y se restauran)

| Mutación | Test | Resultado |
|---|---|---|
| `_memoria_vigente` forzada a `True` | `test_la_informacion_del_conformista_es_precisa...` | **FAIL** esperado |
| quitar `individuo.habilidades.aprender(...)` | `test_descubrir_es_lo_que_ensena_la_habilidad...` | **FAIL** esperado |
| leer `individuo.genoma.divergencia` en `acciones.comer` | `test_el_rasgo_solo_se_lee_donde_es_conducta` | **FAIL** esperado |
| `DISTANCIA_MINIMA_MIGRACION = 4.0` | `test_la_migracion_en_crisis_deja_el_parche...` | **FAIL** esperado (destino a 9.49) |
| migrar también en calma | `test_en_calma_el_parche_se_regenera_en_el_sitio...` | **FAIL** esperado (`migraciones 1 != 0`) |

Tras restaurar: los 5 tests vuelven a verde y `git diff --stat` coincide con el diff
original (sin residuo de mutación).

## Bloqueantes

Ninguno.

## No bloqueante

- **N=50:** se reproduce la semilla 1 (calma S `+0.0021`, crisis `+0.0306`, div
  14.75→25.71, pob 61→70, nac 172/187), coherente con la tabla publicada. La salvedad
  (S se refuerza, pero crisis ≤ calma baja a 4/10 y hay una extinción en crisis) está
  escrita en README y arquitectura como límite de escala, no como excusa. La puerta se
  mide a N=12, que es el default del juego.
- **Umbrales absolutos del veredicto:** `veredicto()` usa 6 y 8 sobre el total de
  filas, lo que es correcto para el barrido 1..10 pero hace que `--seeds` con menos de
  6/8 semillas nunca pueda dar `primaria`/`sube_en_8_de_10` en True aunque todas las
  semillas vayan bien. No afecta a la puerta (default 1..10), pero conviene impedir o
  avisar de barridos parciales si se usan como veredicto.
- **README/informe:** la fila 7 tiene un espacio menos que la salida real
  (`| 100.0` frente a `|  100.0`); los valores son idénticos. Comprobar el resto de
  constantes rebalanceadas que no aparecen en docs: `N_BOSQUES` 6→12,
  `REGENERACION[BAYAS]` 420→300, `FACTOR_REGENERACION_SEQUIA` 0.75 y
  `FACTOR_SED_SEQUIA` 1.25→1.1. Son cambios de balance del mundo, no solo de
  medición; justificados en el mecanismo, pero merecen una línea en la doc.
- **Semántica de las tasas:** `tasa_imitacion` es `imitaciones / descubrimientos`
  (p. ej. 3103.0), no una tasa por individuo; está definida, pero se lee como tasa.
  `desc/c = 0` es por diseño (los conformistas no experimentan), ya explicado.
- **Estilo preexistente:** `review_package` señala funciones largas (`resumen` 117
  líneas, `elegir` 62, `step` 118) y 1 grupo de duplicación (`tallar`/`frotar_madera`),
  casi todo anterior a esta feature. `ruff`, `format` y `mypy` limpios.
- **Secretos:** `secrets scan` devuelve 13 hallazgos, todos fixtures de
  `agents/tests/test_redaction.py` y `test_secrets_agent.py` (sin tocar en este diff);
  no hay secretos en el código de producto.
- **Documentación:** el apartado nuevo se titula F1-005 aunque la feature es
  F1-006. Cosmético.
- **featureslist:** el diff incluye `HARNESS-MODELOS` (pendiente, sin implementar).
  No es atribuible al implementer de F1-006; conviene que el líder confirme su
  procedencia.

## Línea de gate

`success: true · "ENTORNO LISTO — se puede trabajar." · ready: true · errors: 0 · warnings: 0 · pytest 241 passed`
