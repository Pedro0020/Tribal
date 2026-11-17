# reviewer · SCOPE-001

- **Fecha:** 2026-11-18
- **Veredicto:** aprobado

# reviewer · SCOPE-001 · ronda 2

Veredicto: aprobado.

## Criterios

- [x] Existe vault/01_PROYECTO/objetivo.md con cuatro apartados: cumplido.
  Comprobado leyendo el fichero entero: ## 1. Problema (linea 9),
  ## 2. Usuario / consumidor (29), ## 3. Criterio de hecho (47),
  ## 4. Fuera de alcance (106).
- [x] Criterio de hecho verificable: fuego + herramienta compuesta +
  proto-lenguaje + mito, con al menos la mitad de nodos fuera del arbol.
  Cumplido: tabla 3.1 con los cuatro hitos, cada uno con su consulta a
  `nodos`; 3.2 fija el umbral en 50 por ciento con origen distinto de
  `arbol`, denominador = todos los nodos activos (evita el 100 por
  construccion), consulta SQL literal y exigencia de test en `tests/`.
- [x] Fuera de alcance con al menos dos cosas: cumplido y superado.
  Seis puntos numerados (intervencion, multijugador/red, entrenar o nube,
  distribucion/Docker, render 3D, escala masiva), cada uno citando el
  concepto o stack que lo respalda.
- [x] README con frase propia, no la plantilla: cumplido. Linea 11:
  `El objetivo no es dibujar una tribu: es un experimento observable sobre
  como nace la cultura sin que nadie la escriba.` El diff es quirurgico:
  una frase, una fila de tabla y un enlace al KPI.
- [x] ./init.sh termina con ENTORNO LISTO: cumplido via el agente de la
  puerta, que es el mismo codigo (harness gate). Evidencia literal:
  success=true, ready=true, errors=0, warnings=0, pytest 7 passed in 0.36s.

## Bloqueantes (ronda 1) — re-verificados

- B1 pyproject/uv.lock con pygame-ce: RESUELTO. `git status --short` no
  lista ninguno de los dos y `git diff --stat HEAD -- pyproject.toml uv.lock`
  sale vacio; `project.dependencies` = [] leido con tomllib. pygame-ce
  queda para CORE-001, su dueno.
- B2 informe del implementer truncado: RESUELTO. Leido entero (24 lineas,
  termina en la frase sobre el re-grabado en ASCII) y contiene las cinco
  evidencias, incluida la linea de la puerta y el comando de comprobacion
  de encabezados.

Sin bloqueantes abiertos.

## No bloqueante

- `secrets scan` devuelve 13 hallazgos, todos en agents/tests/
  (test_redaction.py, test_secrets_agent.py): fixtures falsos del propio
  detector, preexistentes y fuera del diff de esta feature.
- `review review_package`: 0 hallazgos en los 4 ficheros analizados.
- Git avisa de que harness/featureslist.json esta en CRLF y pasara a LF;
  lo posee harness, no es del implementer.
- Alcance del diff limpio: README.md, harness/featureslist.json,
  harness/progress/current.md y los dos informes de progreso; sin
  reformateos ni refactors ajenos.
- La causa raiz del truncado de `harness record` (comillas y no-ASCII
  desde PowerShell) queda como criterio de QA-001, segun lo acordado.
