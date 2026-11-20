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
| `discard --id <ID> --reason "<motivo>"` | Abandona una feature pending/blocked: `discarded` con motivo, fecha y línea en el histórico |
| `revive --id <ID>` | Devuelve una feature descartada a `pending` |
| `remove --id <ID> [--dry-run true]` | Borra una feature `pending` del backlog. Destructiva: sin `--yes` no se ejecuta |
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

## Descartar no es borrar

`blocked` mezcla dos cosas que no son la misma: «todavía no se puede» y «ya no
se quiere». Con cuatro bloqueadas nadie sabe cuál es la alarma. `discard` es el
segundo caso: deja `status=discarded`, `discarded_reason` y `discarded_on`, y
**escribe una línea en `harness/progress/history.md`** con id, título y motivo.
La feature sale de `next` y de las elegibles, pero no del backlog: el motivo
sigue ahí para quien pregunte después por qué no se hizo.

`revive` la devuelve a `pending` y limpia el rastro del descarte; mientras siga
descartada, `start` la rechaza. `remove` es otra cosa y solo para features
`pending` creadas por error: borra la entrada del JSON, se niega si otra
feature la lista en `depends_on` (nombrando a los dependientes) y **conserva**
los informes `<agente>-<ID>.md` de `harness/progress/`. Sin `--yes` la puerta de
permisos no la ejecuta; con `--dry-run true` enseña qué borraría sin escribir
nada.

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
- **`discard` sin motivo, de una `done` o de una `in_progress`** → el descarte
  deja rastro y no tira lo cerrado ni lo abierto. De una `blocked` sí: limpia
  `blocked_reason` (un motivo, no dos) y avisa con los dependientes en
  `warnings`/`data`, sin impedir el descarte.
- **`start`, `block` o `finish` de una feature `discarded`** → primero `revive`.
- **`remove` de algo que no está `pending`** → bloqueadas y descartadas se
  conservan con su motivo; una cerrada es histórico.
- **`remove` de una feature que otro `depends_on` lista** → `success=false` con
  los dependientes en `data`; se reapuntan con `edit`.
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
| `run harness discard` | `--id`, `--reason` |
| `run harness revive` | `--id` |
| `run harness remove` ⚠️ pide confirmación | `--id`, `--dry_run` |
| `run harness record` | `--agent`, `--id`, `--content`, `--content_file`, `--verdict` |
| `run harness gate` | `--quick` |
| `run harness add` | `--id`, `--title`, `--description`, `--criteria`, `--depends_on` |
| `run harness edit` | `--id`, `--title`, `--description`, `--criteria`, `--depends_on` |

## Límites

**Rol.** Dueño mecánico del arnés: mantiene el backlog y el progreso, y ejecuta la puerta init.sh.

**No se deshacen** (la puerta de permisos las bloquea sin `--yes`; propón, no ejecutes): `remove`

**No hace:**
- decidir QUÉ feature toca ni cómo implementarla → eso lo razonan los agentes markdown del arnés (lider, explorer, implementer, reviewer)
- escribir código del producto → 'refactor' y el implementer
- ejecutar los tests por su cuenta → los ejecuta init.sh, o el agente 'test'
- cerrar una feature sin evidencia → devuelve needs, nunca la da por buena
- borrar una feature que no está pending o de la que otra depende → discard conserva el motivo; el grafo se corrige con edit

**Necesita que le den:** el id de la feature; la evidencia real de verificación para cerrarla

**Escribe en (nadie más toca esto):** harness/featureslist.json, harness/progress/, harness/memory.md

**Se apoya en:** plan, test, review, memory

<!-- END AUTOGEN -->
