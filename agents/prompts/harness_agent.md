# harness — dueño del backlog y del progreso

Ejecuta la parte mecánica del arnés. No decide nada: los agentes markdown
(`lider`, `explorer`, `implementer`, `reviewer`) razonan, este escribe.

## Acciones

| Acción | Qué hace |
|--------|----------|
| `status` | Recuento del backlog + qué está in_progress + qué es elegible |
| `next` | La feature que toca (in_progress, o la primera con deps en done) |
| `start --id <ID>` | Abre la feature y vuelca sus criterios en `harness/progress/current.md` |
| `gate [--quick true]` | Ejecuta `./init.sh` y devuelve el veredicto estructurado |
| `finish --id <ID> --evidence "<salida real>"` | Cierra la feature y escribe el histórico |
| `block --id <ID> --reason "<motivo>"` | Marca bloqueada |
| `record --agent <a> --id <ID> --content "<informe>"` o `--content-file <ruta>` | Guarda `progress/<a>-<ID>.md` (el fichero, UTF-8, evita los truncados de PowerShell) |
| `add --id <ID> --title "<t>" --criteria "a;b;c"` | Añade feature al backlog |
| `edit --id <ID> [--title "<t>"] [--description "<d>"] [--criteria "a;b"] [--depends_on "A;B"]` | Corrige una feature `pending` sin tocar el JSON; `--depends_on ""` limpia las dependencias |

```bash
uv run python -m agents --json run harness next
uv run python -m agents --json run harness start --id DATA-001
uv run python -m agents --json run harness gate
uv run python -m agents --json run harness finish --id DATA-001 --evidence "$(make test 2>&1 | tail -5)"
uv run python -m agents --json run harness edit --id F2-001 --depends_on "F1-006"
```

## Corregir una feature: el precedente

El criterio de una feature **se puede corregir** — un backlog que se atasca
porque una dependencia la cerró otra feature, o porque el criterio estaba mal
escrito, no se arregla editando `featureslist.json` a mano. Pero el cambio no
se esconde: `edit` lo devuelve en `data` como campo → antes/después, y el líder
tiene que pegarlo en el informe de la feature. Si el cambio no queda escrito en
ningún sitio, no ha pasado.

`edit` solo toca `title`, `description`, `acceptance_criteria` y `depends_on`
de features `pending`. `status` y `blocked_reason` son de `start`, `block` y
`finish`: cambiar un estado por aquí sería cerrar una feature sin puerta.

### Flags sin valor (PowerShell)

PowerShell descarta los argumentos vacíos al llamar a un ejecutable: `--depends_on ""`
llega al CLI como un flag sin valor, que `_parse_kwargs` entrega como `True`.
`edit` lo interpreta como «limpiar» — es la única lectura posible de ese flag —
y así `--depends_on ""` funciona igual en bash (cadena vacía) que en PowerShell
(`True`). No uses `--depends_on=`: el parser no parte por `=` y lo rechaza como
campo desconocido.

En los campos de texto no hay interpretación posible: `--title`, `--description`
o `--criteria` sin valor llegan como `True` y `edit` **rechaza** con `needs`,
sin escribir nada. Escribir `"title": true` en el backlog lo corrompe en
silencio, y el arnés existe justo para que un flag mal escrito no lo haga.

## Lo que rechaza

- **`finish` sin `./init.sh` en verde** → `success=false`. La regla del arnés es
  código, no un consejo.
- **`finish` sin `evidence`** → devuelve `needs`. Una afirmación no es evidencia.
- **`start` con otra feature abierta** → una cosa a la vez.
- **`start` con `depends_on` sin cerrar** → primero las dependencias.
- **`add` con `depends_on` inexistente** → el backlog no se corrompe.
- **`edit` de un id inexistente o de una feature que no está `pending`** →
  `success=false`: lo abierto o cerrado no se reescribe.
- **`edit --depends_on` con una dependencia inexistente o que crea un ciclo** →
  el grafo queda como estaba.
- **`edit` intentando cambiar `status` o `blocked_reason`** → esos los cambian
  `start`, `block` y `finish`, no una edición de texto.
- **`edit --title`, `--description` o `--criteria` sin valor** (llegan como
  `True`) → `needs` y el backlog intacto: un flag olvidado no es un texto.
- **`edit --criteria ";"`** → lista vacía tras el split; una feature sin
  criterios pasa la puerta por vacuidad.

## Por qué existe

Editar JSON a mano desde un prompt se rompe: comas, ids duplicados, estados
inventados, un `done` que nadie verificó. Este agente hace esas operaciones
de forma determinista y es el único dueño de `harness/featureslist.json` y `harness/progress/`.

Ver el ciclo completo: `skill harness_workflow`.

<!-- BEGIN AUTOGEN — lo regenera `make prompts-sync`; no lo edites a mano -->

## Acciones

| Acción | Argumentos |
|--------|------------|
| `run harness status` | — |
| `run harness next` | — |
| `run harness start` | `--id`, `--owner` |
| `run harness finish` | `--id`, `--evidence`, `--changes`, `--decisions`, `--pending` |
| `run harness block` | `--id`, `--reason` |
| `run harness record` | `--agent`, `--id`, `--content`, `--content_file`, `--verdict` |
| `run harness gate` | `--quick` |
| `run harness add` | `--id`, `--title`, `--description`, `--criteria`, `--depends_on` |
| `run harness edit` | `--id`, `--title`, `--description`, `--criteria`, `--depends_on` |

## Límites

**Rol.** Dueño mecánico del arnés: mantiene el backlog y el progreso, y ejecuta la puerta init.sh.

**No hace:**
- decidir QUÉ feature toca ni cómo implementarla → eso lo razonan los agentes markdown del arnés (lider, explorer, implementer, reviewer)
- escribir código del producto → 'refactor' y el implementer
- ejecutar los tests por su cuenta → los ejecuta init.sh, o el agente 'test'
- cerrar una feature sin evidencia → devuelve needs, nunca la da por buena

**Necesita que le den:** el id de la feature; la evidencia real de verificación para cerrarla

**Escribe en (nadie más toca esto):** harness/featureslist.json, harness/progress/, harness/memory.md

**Se apoya en:** plan, test, review, memory

<!-- END AUTOGEN -->
