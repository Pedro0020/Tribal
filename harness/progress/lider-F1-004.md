# lider · F1-004

- **Fecha:** 2026-11-18
- **Veredicto:** blocked

Decision del lider sobre F1-004 (2026-11-18).

Estado: F1-004 queda BLOCKED en harness/featureslist.json (blocked_reason incluido).
Motivo: sus dos primeros canales de seleccion premiaban el rasgo por decreto
(penalizacion al comer y sed extra al no divergente), el tercero daba ventaja
reproductiva al divergente y el cuarto editaba el genoma en runtime
(_plasmar_divergencia / _moldear_divergencia). El usuario ha rechazado los cuatro:
la divergencia solo debe decidir conducta; la aptitud debe venir de lo que esa
conducta produce en el mundo. Ademas la sequia salia favorable por dos subsidios
reproductivos: UMBRAL_REPRODUCCION_CRISIS=30 frente a 65 y ENERGIA_CRIA=80.

Trabajo revertido: el arbol vuelve al estado de F1-003 (644 passed, gate verde).
El WIP queda fuera del repo como referencia en %TEMP% (f1-004-wip.patch,
beneficios.py, tradiciones.py, test_tradiciones.py) y el informe en
harness/progress/implementer-F1-004.md; el veredicto en reviewer-F1-004.md.

Arreglo: vault/01_PROYECTO/emergencia-seleccion.md, implementado como EMER-001
(depends_on F1-003). El criterio de la puerta NO se afloja: la proporcion
divergente/conformista tiene que reaccionar a la crisis por conducta, con el
barrido de 10 semillas publicado entero.

Nota de proceso: el agente harness no tiene accion para escribir en
harness/progress/history.md fuera de finish, asi que esta decision se registra
aqui y en el blocked_reason del backlog; EMER-001 la recogera en su entrada de
history.md.
