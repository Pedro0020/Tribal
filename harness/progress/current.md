# Tarea actual

**Feature:** F3-006
**Estado:** in_progress
**Iniciada:** 2026-11-19
**Responsable:** implementer

## Objetivo

objetivo.md §3: cuatro hitos y al menos el 50 por ciento de nodos activos fuera del arbol, comprobado con una consulta sobre la partida y un test del repo.

## Criterios de aceptación

- [ ] test end-to-end reproducible (semilla fija + backend falso guionizado) que llega a fuego, herramienta compuesta, proto-lenguaje y mito
- [ ] test que ejecuta la consulta SQL de objetivo.md §3.2 sobre tribu.db y exige pct_fuera_arbol >= 50.0
- [ ] uv run python -m tribal report kpi --db tribu.db devuelve los cuatro hitos, el porcentaje y el veredicto
- [ ] harness gate success=true

## Bitácora

_(pendiente)_

## Bloqueos

_(ninguno)_
