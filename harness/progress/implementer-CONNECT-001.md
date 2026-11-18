# implementer · CONNECT-001

- **Fecha:** 2026-11-18
- **Veredicto:** ok

# CONNECT-001 — implementer (ronda de matices del reviewer)

## Qué cambié en esta ronda

- `README.md` — matiz de `pct_fuera_arbol`: depende de la semilla y de si nace tradición o cuaja combinación; en calma puede seguir en 0.0. Salidas reales regeneradas (600, 3000 y 5000 ticks).
- `vault/01_PROYECTO/arquitectura.md` — `hablar` pasa a «puede transmitir una habilidad» (es probabilístico y la rama avanza igual). `cuidar` queda como herido (salud < 100).
- `tribal/core/acciones.py` — `SALUD_PARA_CUIDAR = 100.0`: `candidato_a_cuidar` filtra a quien está a salud máxima; ya no se gasta −0,2 sin ganancia.
- `tribal/agents/instinto.py` — `_punto_errante` añade `SESGO_COHESION = 0.4`: 40 % de los paseos van hacia el vecino más cercano. Al filtrar el cuidado, el ocio caía a deambular y dispersaba al grupo; con cohesión la calma vuelve a tener encuentros. No se tocó el filtro ni el test de EMER.
- `tests/test_practicas.py` — aserciones directas de coste (`tallar` 0,5; `frotar_madera` 1,0; `pintar` 0,2), `hablar` sin coste, `cuidar` −0,2/+0,5, y test de que `candidato_a_cuidar` ignora a una cría sana a salud 100 aunque esté más cerca.

## Base CONNECT-001 (ya aprobada)

- Prácticas por rama: `tallar`→lítica, `frotar_madera`→fuego, `hablar`→lenguaje, `ensenar`/`cuidar`→roles, `pintar`→simbólico.
- `PRACTICAS` verbo→(rama, habilidad opcional); el instinto las elige solo en ocio con rotación `(id + tick)`; el árbol valida el nivel y hay máximo un nodo por tick.
- Documentación en `README.md` (tabla y límites) y `arquitectura.md` §9.1.

## Criterios de aceptación

1. **Práctica por rama.** `tests/test_practicas.py`: `test_practicas_cubre_las_cinco_ramas_del_arbol` y los cinco casos de `test_una_practica_por_rama_descubre_su_rama`. Comando: `uv run pytest -q tests/test_practicas.py`.
2. **Combinación distinta de `raedera` alcanzable.** `test_un_nodo_combinacion_distinto_de_raedera_es_alcanzable_en_partida` (seed 42, 600 ticks, crisis) exige `canto_ritual` con `proto_palabras` y `ritual` activos.
3. **La puerta F1→F2 documenta qué ramas avanza F1.** `README.md` y `arquitectura.md` §9.1; se explicita que la proporción divergente es de DIVERGENCIA-002 y el >50 % de Fase 3.
4. **`pytest -q` y gate.** `689 passed, 15 skipped`; `harness gate` → `success True`.

## Evidencia

### `report culture --json` (calma, seed 42, 600 ticks)

```json
{"seed": 42, "ticks": 600, "crisis": false, "nodos": [{"id": "guijarro", "rama": "litica", "nivel": 0, "titulo": "Guijarro", "origen": "arbol", "autor": 6, "tick": 1}, {"id": "lasca", "rama": "litica", "nivel": 1, "titulo": "Lasca", "origen": "arbol", "autor": 6, "tick": 4}, {"id": "bifaz", "rama": "litica", "nivel": 2, "titulo": "Bifaz", "origen": "arbol", "autor": 6, "tick": 7}, {"id": "punta_de_lanza", "rama": "litica", "nivel": 3, "titulo": "Punta de lanza", "origen": "arbol", "autor": 6, "tick": 10}, {"id": "caza_cooperativa", "rama": "litica", "nivel": 4, "titulo": "Caza cooperativa", "origen": "arbol", "autor": 6, "tick": 13}, {"id": "observar_rayo", "rama": "fuego", "nivel": 0, "titulo": "Observar el rayo", "origen": "arbol", "autor": 6, "tick": 2}, {"id": "conservar_brasas", "rama": "fuego", "nivel": 1, "titulo": "Conservar brasas", "origen": "arbol", "autor": 6, "tick": 5}, {"id": "friccion", "rama": "fuego", "nivel": 2, "titulo": "Fricci\u00f3n", "origen": "arbol", "autor": 6, "tick": 8}, {"id": "cocinar", "rama": "fuego", "nivel": 3, "titulo": "Cocinar", "origen": "arbol", "autor": 6, "tick": 11}, {"id": "ahuyentar_depredadores", "rama": "fuego", "nivel": 4, "titulo": "Ahuyentar depredadores", "origen": "arbol", "autor": 6, "tick": 14}, {"id": "gestos", "rama": "lenguaje", "nivel": 0, "titulo": "Gestos y gru\u00f1idos", "origen": "arbol", "autor": 9, "tick": 9}, {"id": "proto_palabras", "rama": "lenguaje", "nivel": 1, "titulo": "Proto-palabras", "origen": "arbol", "autor": 9, "tick": 12}, {"id": "vocabulario", "rama": "lenguaje", "nivel": 2, "titulo": "Vocabulario", "origen": "arbol", "autor": 9, "tick": 16}, {"id": "transmision_eficaz", "rama": "lenguaje", "nivel": 3, "titulo": "Transmisi\u00f3n eficaz", "origen": "arbol", "autor": 9, "tick": 17}, {"id": "tradicion_ahuyentar_depredadores", "rama": "roles", "nivel": 5, "titulo": "Tradici\u00f3n de ahuyentar depredadores", "origen": "interaccion", "autor": 11, "tick": 219}, {"id": "tradicion_caza_cooperativa", "rama": "roles", "nivel": 5, "titulo": "Tradici\u00f3n de caza cooperativa", "origen": "interaccion", "autor": 11, "tick": 218}, {"id": "arte_rupestre", "rama": "simbolico", "nivel": 0, "titulo": "Arte rupestre", "origen": "arbol", "autor": 6, "tick": 3}, {"id": "ritual", "rama": "simbolico", "nivel": 1, "titulo": "Ritual", "origen": "arbol", "autor": 6, "tick": 6}, {"id": "mito", "rama": "simbolico", "nivel": 2, "titulo": "Mito", "origen": "arbol", "autor": 6, "tick": 15}, {"id": "identidad_grupo", "rama": "simbolico", "nivel": 3, "titulo": "Identidad del grupo", "origen": "arbol", "autor": 6, "tick": 18}, {"id": "tradicion_identidad_grupo", "rama": "simbolico", "nivel": 4, "titulo": "Tradici\u00f3n de identidad del grupo", "origen": "interaccion", "autor": 11, "tick": 220}, {"id": "tradicion_transmision_eficaz", "rama": "simbolico", "nivel": 4, "titulo": "Tradici\u00f3n de transmisi\u00f3n eficaz", "origen": "interaccion", "autor": 5, "tick": 49}], "aristas": [{"origen": "guijarro", "destino": "lasca"}, {"origen": "observar_rayo", "destino": "conservar_brasas"}, {"origen": "arte_rupestre", "destino": "ritual"}, {"origen": "lasca", "destino": "bifaz"}, {"origen": "conservar_brasas", "destino": "friccion"}, {"origen": "bifaz", "destino": "punta_de_lanza"}, {"origen": "friccion", "destino": "cocinar"}, {"origen": "gestos", "destino": "proto_palabras"}, {"origen": "punta_de_lanza", "destino": "caza_cooperativa"}, {"origen": "cocinar", "destino": "ahuyentar_depredadores"}, {"origen": "proto_palabras", "destino": "mito"}, {"origen": "ritual", "destino": "mito"}, {"origen": "proto_palabras", "destino": "vocabulario"}, {"origen": "vocabulario", "destino": "transmision_eficaz"}, {"origen": "mito", "destino": "identidad_grupo"}, {"origen": "transmision_eficaz", "destino": "tradicion_transmision_eficaz"}, {"origen": "caza_cooperativa", "destino": "tradicion_caza_cooperativa"}, {"origen": "ahuyentar_depredadores", "destino": "tradicion_ahuyentar_depredadores"}, {"origen": "identidad_grupo", "destino": "tradicion_identidad_grupo"}], "pct_fuera_arbol": 18.2, "nodos_por_origen": {"arbol": 18, "combinacion": 0, "interaccion": 4, "llm": 0}, "nivel_max": 2}
```

Resumen: `{"arbol": 18, "combinacion": 0, "interaccion": 4, "llm": 0}`, `pct_fuera_arbol 18.2`, `nivel_max 2`. En 600 ticks de calma la lítica, el fuego, el lenguaje y el símbolo tienen nodos de árbol; roles aparece como tradición y completa sus nodos de árbol en corridas más largas o con heridos.

### `report culture --json --crisis --ticks 600`

```json
{"seed": 42, "ticks": 600, "crisis": true, "nodos": [{"id": "guijarro", "rama": "litica", "nivel": 0, "titulo": "Guijarro", "origen": "arbol", "autor": 6, "tick": 1}, {"id": "lasca", "rama": "litica", "nivel": 1, "titulo": "Lasca", "origen": "arbol", "autor": 6, "tick": 4}, {"id": "bifaz", "rama": "litica", "nivel": 2, "titulo": "Bifaz", "origen": "arbol", "autor": 6, "tick": 7}, {"id": "cuchillo_al_fuego", "rama": "litica", "nivel": 2, "titulo": "Cuchillo al fuego", "origen": "combinacion", "autor": 7, "tick": 78}, {"id": "punta_de_lanza", "rama": "litica", "nivel": 3, "titulo": "Punta de lanza", "origen": "arbol", "autor": 6, "tick": 10}, {"id": "raedera", "rama": "litica", "nivel": 3, "titulo": "Raedera", "origen": "combinacion", "autor": 7, "tick": 113}, {"id": "caza_cooperativa", "rama": "litica", "nivel": 4, "titulo": "Caza cooperativa", "origen": "arbol", "autor": 6, "tick": 13}, {"id": "observar_rayo", "rama": "fuego", "nivel": 0, "titulo": "Observar el rayo", "origen": "arbol", "autor": 6, "tick": 2}, {"id": "conservar_brasas", "rama": "fuego", "nivel": 1, "titulo": "Conservar brasas", "origen": "arbol", "autor": 6, "tick": 5}, {"id": "friccion", "rama": "fuego", "nivel": 2, "titulo": "Fricci\u00f3n", "origen": "arbol", "autor": 6, "tick": 8}, {"id": "cocinar", "rama": "fuego", "nivel": 3, "titulo": "Cocinar", "origen": "arbol", "autor": 6, "tick": 11}, {"id": "ahuyentar_depredadores", "rama": "fuego", "nivel": 4, "titulo": "Ahuyentar depredadores", "origen": "arbol", "autor": 6, "tick": 14}, {"id": "gestos", "rama": "lenguaje", "nivel": 0, "titulo": "Gestos y gru\u00f1idos", "origen": "arbol", "autor": 9, "tick": 9}, {"id": "proto_palabras", "rama": "lenguaje", "nivel": 1, "titulo": "Proto-palabras", "origen": "arbol", "autor": 9, "tick": 12}, {"id": "vocabulario", "rama": "lenguaje", "nivel": 2, "titulo": "Vocabulario", "origen": "arbol", "autor": 9, "tick": 16}, {"id": "transmision_eficaz", "rama": "lenguaje", "nivel": 3, "titulo": "Transmisi\u00f3n eficaz", "origen": "arbol", "autor": 9, "tick": 17}, {"id": "cazador", "rama": "roles", "nivel": 0, "titulo": "Cazador", "origen": "arbol", "autor": 2, "tick": 49}, {"id": "recolectora", "rama": "roles", "nivel": 0, "titulo": "Recolectora", "origen": "arbol", "autor": 2, "tick": 57}, {"id": "anciano", "rama": "roles", "nivel": 1, "titulo": "Anciano", "origen": "arbol", "autor": 7, "tick": 208}, {"id": "chaman", "rama": "roles", "nivel": 2, "titulo": "Cham\u00e1n", "origen": "arbol", "autor": 7, "tick": 209}, {"id": "lider", "rama": "roles", "nivel": 2, "titulo": "L\u00edder", "origen": "arbol", "autor": 8, "tick": 216}, {"id": "caceria_dirigida", "rama": "roles", "nivel": 5, "titulo": "Cacer\u00eda dirigida", "origen": "combinacion", "autor": 2, "tick": 217}, {"id": "tradicion_ahuyentar_depredadores", "rama": "roles", "nivel": 5, "titulo": "Tradici\u00f3n de ahuyentar depredadores", "origen": "interaccion", "autor": 11, "tick": 192}, {"id": "tradicion_caza_cooperativa", "rama": "roles", "nivel": 5, "titulo": "Tradici\u00f3n de caza cooperativa", "origen": "interaccion", "autor": 11, "tick": 191}, {"id": "turnos_de_vigilia", "rama": "roles", "nivel": 5, "titulo": "Turnos de vigilia", "origen": "combinacion", "autor": 2, "tick": 43}, {"id": "arte_rupestre", "rama": "simbolico", "nivel": 0, "titulo": "Arte rupestre", "origen": "arbol", "autor": 6, "tick": 3}, {"id": "ritual", "rama": "simbolico", "nivel": 1, "titulo": "Ritual", "origen": "arbol", "autor": 6, "tick": 6}, {"id": "canto_ritual", "rama": "simbolico", "nivel": 2, "titulo": "Canto ritual", "origen": "combinacion", "autor": 2, "tick": 19}, {"id": "mito", "rama": "simbolico", "nivel": 2, "titulo": "Mito", "origen": "arbol", "autor": 6, "tick": 15}, {"id": "identidad_grupo", "rama": "simbolico", "nivel": 3, "titulo": "Identidad del grupo", "origen": "arbol", "autor": 6, "tick": 18}, {"id": "tradicion_identidad_grupo", "rama": "simbolico", "nivel": 4, "titulo": "Tradici\u00f3n de identidad del grupo", "origen": "interaccion", "autor": 11, "tick": 193}, {"id": "tradicion_transmision_eficaz", "rama": "simbolico", "nivel": 4, "titulo": "Tradici\u00f3n de transmisi\u00f3n eficaz", "origen": "interaccion", "autor": 5, "tick": 49}], "aristas": [{"origen": "guijarro", "destino": "lasca"}, {"origen": "observar_rayo", "destino": "conservar_brasas"}, {"origen": "arte_rupestre", "destino": "ritual"}, {"origen": "lasca", "destino": "bifaz"}, {"origen": "conservar_brasas", "destino": "friccion"}, {"origen": "bifaz", "destino": "punta_de_lanza"}, {"origen": "friccion", "destino": "cocinar"}, {"origen": "gestos", "destino": "proto_palabras"}, {"origen": "punta_de_lanza", "destino": "caza_cooperativa"}, {"origen": "cocinar", "destino": "ahuyentar_depredadores"}, {"origen": "proto_palabras", "destino": "mito"}, {"origen": "ritual", "destino": "mito"}, {"origen": "proto_palabras", "destino": "vocabulario"}, {"origen": "vocabulario", "destino": "transmision_eficaz"}, {"origen": "mito", "destino": "identidad_grupo"}, {"origen": "proto_palabras", "destino": "canto_ritual"}, {"origen": "ritual", "destino": "canto_ritual"}, {"origen": "ahuyentar_depredadores", "destino": "turnos_de_vigilia"}, {"origen": "caza_cooperativa", "destino": "turnos_de_vigilia"}, {"origen": "transmision_eficaz", "destino": "tradicion_transmision_eficaz"}, {"origen": "lasca", "destino": "cuchillo_al_fuego"}, {"origen": "conservar_brasas", "destino": "cuchillo_al_fuego"}, {"origen": "lasca", "destino": "raedera"}, {"origen": "bifaz", "destino": "raedera"}, {"origen": "caza_cooperativa", "destino": "tradicion_caza_cooperativa"}, {"origen": "ahuyentar_depredadores", "destino": "tradicion_ahuyentar_depredadores"}, {"origen": "identidad_grupo", "destino": "tradicion_identidad_grupo"}, {"origen": "cazador", "destino": "anciano"}, {"origen": "recolectora", "destino": "anciano"}, {"origen": "anciano", "destino": "chaman"}, {"origen": "anciano", "destino": "lider"}, {"origen": "caza_cooperativa", "destino": "lider"}, {"origen": "caza_cooperativa", "destino": "caceria_dirigida"}, {"origen": "lider", "destino": "caceria_dirigida"}], "pct_fuera_arbol": 28.1, "nodos_por_origen": {"arbol": 23, "combinacion": 5, "interaccion": 4, "llm": 0}, "nivel_max": 2}
```

Combinaciones: `cuchillo_al_fuego` (78), `raedera` (113), `caceria_dirigida` (217), `turnos_de_vigilia` (43), `canto_ritual` (19).

### e2e de la combinación nueva

```
$ uv run pytest -q tests/test_practicas.py::test_un_nodo_combinacion_distinto_de_raedera_es_alcanzable_en_partida
.                                                                        [100%]
1 passed in 0.64s
```

### Mutaciones de los costes (los tests caen si se ponen a 0)

```
$ uv run python .tmp_mut.py
COSTE_TALLAR -> test cae: True
COSTE_FROTAR_MADERA -> test cae: True
COSTE_PINTAR -> test cae: True
COSTE_CUIDAR -> test cae: True
SALUD_PARA_CUIDAR -> test cae: True
```

### Suite completa

```
$ uv run pytest -q
689 passed, 15 skipped in 92.31s
```

### Lint, formato y tipos

```
$ uv run ruff check tribal tests agents
All checks passed!

$ uv run ruff format --check tribal tests
41 files already formatted

$ uv run mypy tribal tests
Success: no issues found in 41 source files
```

### Puerta

```
$ uv run python -m agents --json run harness gate
success True
warnings []

$ ./init.sh
pytest 160 passed
━━ ENTORNO LISTO ━━  0 aviso(s)
```

## Qué falta

Nada de esta ronda. `test_la_crisis_no_es_el_regimen_favorable` de EMER-001 no se tocó y vuelve a estar en verde con el sesgo de cohesión (seed 3, 4000 ticks: crisis ≤ calma).
