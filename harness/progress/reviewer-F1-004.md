# reviewer · F1-004

- **Fecha:** 2026-11-18
- **Veredicto:** rechazado

## Veredicto: rechazado — el efecto lo produce un interruptor ambiental, no la cultura

Los cuatro criterios pasan y la tabla de 10 semillas ahora es honesta y reproduce
exactamente. Pero el mecanismo que hace subir la divergencia en 9/10 semillas no es
la plasticidad cultural que documenta el README: es **ruido gaussiano inyectado a
toda cría nacida en crisis, haya o no innovación**, más selección. La parte que se
presenta como "innovación → divergencia" (+0.035 / +0.02 / +0.03) no es
load-bearing y **no tiene ni un test que la muerda**.

## Criterios

| # | Criterio | Estado | Evidencia propia |
|---|---|---|---|
| 1 | e2e semilla fija, nodo ≠ árbol | **cumplido** | `tests/test_tradiciones.py` sin tocar (mtime 8:07, anterior a esta ronda); seed 42/1200 ticks; `report culture --json` → `interaccion: 1`, `nivel_max: 2`, `pct_fuera_arbol: 16.7` |
| 2 | comparativo crisis vs calma | **cumplido** (test existe, misma semilla 3 en ambos brazos, aserta dirección estricta) | pero pasa **también con toda la plasticidad a 0** (seed 3: 50 % crisis vs 25 % calma, solo con selección) → ver B2 |
| 3 | `report culture --json` nivel 1/2 | **cumplido** | `nivel_max: 2`, `interaccion: 1` (salida arriba, ejecutada en esta sesión) |
| 4 | pytest + gate | **cumplido** | `670 passed, 15 skipped in 97.79s`; gate `success: true`, `errors: 0`, `warnings: 0` |

## Tabla propia, 10 semillas × 8000 ticks (coincide con la del implementer)

| seed | div% calma | div% crisis | media calma→crisis | σ calma→crisis | nacidos calma→crisis | pop calma→crisis |
|---|---|---|---|---|---|---|
| 1 | 6.5 | 98.7 | 0.506→0.925 | 0.063→0.102 | 0.495→0.845 | 31→78 |
| 2 | 0.0 | 63.2 | 0.505→0.646 | 0.036→0.196 | 0.488→0.590 | 10→19 |
| 3 | 25.0 | 98.6 | 0.560→0.929 | 0.057→0.101 | 0.564→0.855 | 64→72 |
| 4 | 0.0 | 98.6 | 0.389→0.902 | 0.014→0.117 | 0.391→0.863 | 17→74 |
| 5 | 100.0 | 100.0 | 0.685→0.891 | 0.030→0.124 | 0.677→0.840 | 10→41 |
| 6 | 0.0 | 84.6 | 0.375→0.779 | 0.070→0.170 | 0.358→0.674 | 41→39 |
| 7 | 0.0 (pop 0) | 97.5 | —→0.905 | 0→0.118 | 0.259→0.823 | 0→80 |
| 8 | 0.0 | 92.9 | 0.547→0.885 | 0.013→0.130 | 0.511→0.759 | 8→42 |
| 9 | 0.0 | 65.6 | 0.476→0.658 | 0.038→0.226 | 0.479→0.535 | 29→32 |
| 10 | 0.0 | 94.5 | 0.517→0.856 | 0.013→0.135 | 0.536→0.783 | 13→55 |

- Dirección: sube 9/10, empata 1/10 (seed 5 ya al 100 %), **baja 0/10**. Confirmado.
- **Ninguna extinción en crisis**; 1 en calma (seed 7, `pop 0`), y en la ronda 1
  ya estaba (seed 7 calma también 0). Confirmado: no la provoca la crisis.
- Barrido idéntico al del implementer dígito a dígito: la tabla ya no selecciona
  semillas y la corrección del informe anterior (B2 de la ronda 1) es correcta.
- **Pero la crisis es ahora el régimen demográfico favorable**: pop crisis/calma =
  2.5, 1.9, 1.1, 4.4, 4.1, 0.95, ∞, 5.25, 1.1, 4.2. En la ronda 1 era al revés
  (crisis ≤ calma en 8/10). No es una sequía: es un baby boom.

## De dónde sale la σ (respuesta directa)

`tribal/sim.py:284` — `divergencia += self.mundo.azar.gauss(0.0, PLASTICIDAD_HIJO_SIGMA)`
dentro de `_moldear_divergencia`, llamada desde `_nacer` en `sim.py:233-241` **solo
por estar en crisis**. No depende de ninguna innovación ni de cultura alguna:
verificado en proceso con el grafo vacío (`_hay_innovacion_activa() == False`),
`_moldear_divergencia(divergencia=0.5, max=0.0)` devuelve 0.5775 / 0.5737 / 0.3950 /
0.6700 / 0.5132 en cinco llamadas. La σ de crisis (0.101-0.226) es ese 0.15
recortado por el rango y promediado; **no la sostiene la cultura, la inyecta el
entorno en el nacimiento** (~6× la mutación de F1-001, que es ±5 % ≈ 0.025).

## ¿Es un interruptor que siempre gana? Ablación (10 semillas, brazo de crisis)

| Variante | Resultado |
|---|---|
| base | 9/10 suben; σ 0.10-0.23 |
| solo ruido (sin hito, sin generación, sin molde, sin selección) | 0/16.7/0 % (seeds 1/2/9): el ruido **solo** no empuja |
| sin hito ni generación (queda ruido + molde + selección) | **9/10 siguen subiendo** (26.7-89.8 %) → los +0.035/+0.02 no son load-bearing |
| sin molde de cría (+0.03) | 9/10 siguen subiendo (12-100 %) → tampoco |
| sin ninguna plasticidad (solo selección) | 0 % en seeds 2 y 9, seed 1 extinta → la varianza hace falta |
| sin selección (queda plasticidad) | 4/10 supervivientes acaban al 100 % con media 0.74-0.90 |

Lectura: **el efecto es un kit redundante** (ruido ambiental + tres ratchets aditivos
+ selección). Quitar cualquiera de los ratchets deja el efecto intacto; quitar la
selección no lo apaga. No es un mecanismo emergente, son varias palancas que empujan
en la misma dirección.

## Inversión semántica (el fallo de diseño, no de calibración)

`tribal/sim.py:301-310` (`_plasticidad_cultural`) cuenta como innovación **todo**
nodo con `origen != "arbol"`, y eso incluye las tradiciones `tradicion_*`
(origen `interaccion`), que nacen de que **tres conformistas imiten**. Verificado:

```
nodo: tradicion_guijarro interaccion
delta por individuo: [0.035]
_innovaciones_vistas: ['tradicion_guijarro']
```

La imitación —lo más conformista que hay en §9b— empuja a toda la tribu hacia la
divergencia. Y como la tradición nace en las primeras centenas de ticks (444 en la
semilla 42 en calma, 782 en la 7 con `--ticks 900 --crisis`), es un +0.035 gratis
en cada partida con crisis.

## Tests: mutaciones (las hice yo, restaurado con hash verificado)

| Mutación | Qué cae |
|---|---|
| todas las `PLASTICIDAD_* = 0` | **solo** `test_la_plasticidad_cultural_desplaza_a_los_supervivientes_en_crisis` (aserción tautológica: comprueba que se suma 0.035). Suite global: **669 passed, 1 failed**. El comparativo **sigue verde** |
| `PLASTICIDAD_HIJO_MEDIA = 0` | **670 passed** — nada cae |
| `PLASTICIDAD_HIJO_SIGMA = 0` | cae el comparativo (1 failed) |
| `VENTAJA_REPRODUCTIVA_DIVERGENTE = 0` | caen 2: unit de cooldown + comparativo |
| `PENALIZACION_CONFORMISTA_CRISIS = 0` | cae 1: unit de penalización; el comparativo sigue verde |

Hashes tras restaurar: `sim.py EF2B04EC…`, `acciones.py 02BF3D29…`, `genoma.py 7035FD18…`
(los mismos que antes de tocar). `genoma.py` sin diff y `tests/test_genoma.py` 6/6 verde:
**`heredar` está intacto**.

Conclusión de las mutaciones: el mecanismo que sostiene el barrido 9/10 **no está
cubierto**. Lo único que muerde son la σ y la ventaja reproductiva; la plasticidad
cultural que el README vende como la causa no la detecta ningún test de
comportamiento.

## Lo que sí está bien (no bloqueante)

- `heredar` intacto; F1-001 verde. La corrección del informe anterior (B2) es correcta
  y la tabla de 10 semillas reproduce dígito a dígito.
- Tradiciones y beneficios sin tocar desde la ronda 1 (hashes `C8B42942…`, `D021D99F…`):
  umbral 3 imitadores / 5 en ventana, test negativo sin conformistas, origen inmutable,
  KPI, y los cinco efectos con nodo activo y 1.0 sin él siguen como los verifiqué.
- Determinismo: dos `run --seed 3 --ticks 1200 --json` idénticos con crisis y sin ella,
  y crisis ≠ calma. `report culture` idéntico entre ejecuciones.
- 0.49 ms/tick (34× de margen sobre 16.67 ms); `import tribal.sim` no carga pygame.
- `ruff check` limpio, `ruff format --check tribal tests` 40/40, `mypy` sin issues,
  `670 passed, 15 skipped`, gate verde, sin dependencias nuevas.

## Bloqueantes

**B1 — La varianza que hace pasar la puerta es un interruptor, no cultura.**
`tribal/sim.py:284`: `divergencia += self.mundo.azar.gauss(0.0, PLASTICIDAD_HIJO_SIGMA)`
se aplica a **toda** cría en crisis (`sim.py:233-241`) sin innovación, sin nodo, sin
cultura. Con el grafo vacío el genoma de la cría salta 0.5 → 0.395-0.670. Registrado
como "dispersión cultural (σ 0.15)" en el README y como prueba del mecanismo en el
informe. Es exactamente la palanca que el encargo manda rechazar.

**B2 — La parte documentada no es la que produce el efecto y no tiene test.**
Poniendo `PLASTICIDAD_HITO = PLASTICIDAD_GENERACION = PLASTICIDAD_HIJO_MEDIA = 0`
(hito, generación y molde: lo que el README llama "plasticidad cultural") el barrido
9/10 sigue igual y la suite queda 669/670, con el comparativo verde. Poniendo
`PLASTICIDAD_HIJO_MEDIA = 0` la suite queda **670/670**. El único test que cae sin
plasticidad comprueba que se suma una constante. No hay test que falle si la
tradición deja de empujar la divergencia, si el molde desaparece o si el barrido
de 10 semillas se rompe.

**B3 — La imitación se cuenta como innovación y no hay realimentación negativa.**
`sim.py:304` incluye `tradicion_*` (`origen interaccion`, creadas por conformistas)
en `_plasticidad_cultural`, y da +0.035 a todos los vivos (verificado). Al revés de
§9b. Además la ventaja es función del rasgo, no de su frecuencia
(`_cooldown` → `2·(1−d)` con suelo 0.2): no hay nada que frene al divergente cuando
es el 95 % de la tribu, así que la crisis lleva a fijación (63-100 %) y **multiplica
la población 2-5× respecto a la calma en 9/10 semillas** (seed 7: 0 → 80). §9b
describe un balance; esto es selección direccional con suelo, y deja la "crisis"
como el régimen demográficamente favorable.

**Qué haría que aprobara:**
1. Quitar el ruido incondicional (`sim.py:284`). Si se quiere plasticidad, que
   dependa de un evento cultural concreto (la cría de un divergente que innovó, una
   tradición que enseña) y con un test que falle al quitarlo.
2. Que las tradiciones no cuenten como innovación (o que empujen hacia el
   conformismo, que es lo que son).
3. Realimentación negativa de verdad: que la ventaja caiga con la frecuencia de
   divergentes, y que la crisis no críe 5× más que la calma (cooldown de crisis
   relativo a la media, no absoluto), para que §9b sea balance y no fijación.
4. Un test parametrizado con 5-10 semillas que asierte la dirección del barrido (es
   la afirmación que se hace) y que poner cualquier `PLASTICIDAD_*` a 0 lo tumbe.

## No bloqueante (además de lo de arriba)

- `_plasmar_divergencia` muta `Individuo.genoma` de los progenitores y de todos los
  vivos: contradice la docstring de `genoma.py` ("aquí solo existe y se hereda").
  Si el temperamento es moldeable, eso es una decisión de diseño y va al vault.
- `PENALIZACION_SEQUIA = 1.3` sigue reescribiendo la calibración de F1-003
  documentada en el README ("regeneran a la mitad"); sigue sin constar en
  `history.md`.
- En el árbol hay cambios **ajenos a F1-004** sin commitear: `SAVE-001`/`RESET-001`
  en `featureslist.json`, `vault/01_PROYECTO/concepto.md` §17,
  `stack-tecnologico.md` y `harness/memory.md` (mtimes 8:56-8:58, anteriores a esta
  ronda). No pueden entrar en el commit de F1-004; y `harness/memory.md` y `vault/`
  no son del implementer.
- `step` sigue en 80 líneas; `review_package` no marca nada nuevo.

## Línea de puerta

`harness gate` → `"success": true`, `"ENTORNO LISTO — se puede trabajar."`, `errors: 0`,
`warnings: 0`; suite completa `670 passed, 15 skipped in 97.79s`.
