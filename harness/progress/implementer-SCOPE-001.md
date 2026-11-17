# implementer · SCOPE-001

- **Fecha:** 2026-11-18
- **Veredicto:** ok

Implementacion de SCOPE-001.

Ficheros tocados:
- vault/01_PROYECTO/objetivo.md (nuevo): secciones 1 Problema, 2 Usuario/consumidor, 3 Criterio de hecho, 4 Fuera de alcance.
- README.md: linea 11 (frase de objetivo propia), fila de la tabla de documentacion para objetivo.md y enlace al KPI en el criterio de exito.

Criterio 1: los cuatro apartados existen como encabezados ## 1..4.
Criterio 2: el criterio de hecho queda medido en 3.1 (cuatro hitos: fuego, herramienta compuesta con dos o mas aristas entrantes, proto-lenguaje con nivel mayor que 0, mito), 3.2 (KPI al menos 50 por ciento de nodos activos con origen distinto de arbol, con la consulta SQL literal y el test que la ejecuta) y 3.3 (lo que no cuenta).
Criterio 3: seis puntos fuera de alcance, cada uno citando concepto o stack.
Criterio 4: la frase del README es propia y no repite el texto de plantilla.
Criterio 5: verificado con el comando equivalente en este equipo.

Evidencia literal:
- uv run python -m agents --json run harness gate: success=true, message ENTORNO LISTO - se puede trabajar, ready=true, errors=0, warnings=0, pytest 7 passed.
- Select-String -Pattern '^## ' vault/01_PROYECTO/objetivo.md devuelve las cuatro secciones.

Decisiones: no se invento contenido; objetivo.md destila concepto.md y stack-tecnologico.md. El KPI usa como denominador todos los nodos activos para que el porcentaje no sea 100 por construccion.

Pendiente: los 16 fallos de agents/tests en Windows pertenecen a QA-001. Registro re-grabado en ASCII porque harness record trunca la entrada con comillas y no-ASCII desde PowerShell (anotado para QA-001).
