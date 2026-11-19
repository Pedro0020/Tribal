"""
Export del grafo de cultura a Markdown para Obsidian (stack §6).

`exportar_obsidian` es el **único** dueño de la salida a Markdown: lee nodos y
aristas de una partida a través de `Repositorio` —no importa `sqlite3`— y escribe
un `.md` por nodo más un `index.md`. Cada nota lleva frontmatter simple con los
datos de nacimiento del nodo y una sección de relaciones con un `[[wikilink]]`
por cada arista que entra o sale, de modo que el grafo se ve como constelación
en el vault de la tribu.

La escritura es determinista e idempotente: nodos ordenados por id, aristas por
`(origen, destino)`, UTF-8 sin BOM y saltos LF. Dos exports seguidos dejan los
mismos bytes. **Los `.md` viejos que ya no corresponden a ningún nodo no se
borran**: un vault puede tener notas humanas y este módulo no es su dueño. Si
quieres un export limpio, vacía `out` antes de ejecutarlo; `index.md` se
reescribe siempre y sirve de mapa de lo que el export generó.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from tribal.culture.arbol import ORIGENES, Nodo
from tribal.culture.grafo import Arista, Grafo
from tribal.store.repositorio import Repositorio

#: Nombres de fichero seguros para cualquier sistema: ASCII, minúsculas y `-_`.
_NO_SEGURO = re.compile(r"[^a-z0-9_-]+")


class ExportInvalido(RuntimeError):
    """La partida tiene una arista que apunta a un nodo que no existe."""


@dataclass(frozen=True, slots=True)
class ResumenExport:
    """Lo que dejó el export: recuentos y carpeta de destino."""

    nodos: int
    aristas: int
    ficheros: int
    out: Path


def exportar_obsidian(repo: Repositorio, out: str | Path) -> ResumenExport:
    """Vuelca nodos y aristas de `repo` a `out` como Markdown para Obsidian."""
    grafo = repo.cargar().grafo
    destino = Path(out)
    destino.mkdir(parents=True, exist_ok=True)

    ids = sorted(grafo.nodos)
    slugs = _slugs(ids)
    salientes: dict[str, list[Arista]] = {nodo_id: [] for nodo_id in ids}
    entrantes: dict[str, list[Arista]] = {nodo_id: [] for nodo_id in ids}
    for arista in sorted(grafo.aristas, key=lambda a: (a.origen, a.destino)):
        if arista.origen not in slugs or arista.destino not in slugs:
            raise ExportInvalido(
                f"arista {arista.origen} -> {arista.destino}: extremo inexistente en la partida"
            )
        salientes[arista.origen].append(arista)
        entrantes[arista.destino].append(arista)

    for nodo_id in ids:
        _escribir(
            destino / f"{slugs[nodo_id]}.md",
            _nota(grafo.nodos[nodo_id], slugs, salientes[nodo_id], entrantes[nodo_id]),
        )
    _escribir(destino / "index.md", _indice(grafo, ids, slugs))

    return ResumenExport(
        nodos=len(ids),
        aristas=len(grafo.aristas),
        ficheros=len(ids) + 1,
        out=destino,
    )


def _slugs(ids: Sequence[str]) -> dict[str, str]:
    """Slug estable por id; una colisión de saneado se resuelve con `-2`, `-3`."""
    usados = {"index"}
    mapa: dict[str, str] = {}
    for nodo_id in ids:
        base = _slug(nodo_id)
        slug = base
        sufijo = 2
        while slug in usados:
            slug = f"{base}-{sufijo}"
            sufijo += 1
        usados.add(slug)
        mapa[nodo_id] = slug
    return mapa


def _slug(nodo_id: str) -> str:
    """Id a nombre de fichero: sin acentos, sin espacios y sin mayúsculas."""
    plano = unicodedata.normalize("NFKD", nodo_id).encode("ascii", "ignore").decode("ascii")
    limpio = _NO_SEGURO.sub("-", plano.lower()).strip("-_")
    return limpio or "nodo"


def _nota(
    nodo: Nodo,
    slugs: dict[str, str],
    salientes: Sequence[Arista],
    entrantes: Sequence[Arista],
) -> str:
    lineas = [
        "---",
        f"id: {_yaml(nodo.id)}",
        f"rama: {_yaml(nodo.rama)}",
        f"nivel: {nodo.nivel}",
        f"origen: {_yaml(nodo.origen)}",
        f"estado: {_yaml(nodo.estado)}",
        f"autor: {nodo.autor}",
        f"tick: {nodo.tick}",
        f"tick_apagado: {nodo.tick_apagado}",
        f"motivo_apagado: {_yaml(nodo.motivo_apagado)}",
        "---",
        "",
        f"# {_una_linea(nodo.titulo)}",
        "",
    ]
    contenido = _texto(nodo.contenido).strip()
    if contenido:
        lineas.extend([contenido, ""])
    lineas.extend(["## Relaciones", ""])
    if not salientes and not entrantes:
        lineas.append("_(ninguna)_")
    else:
        for arista in salientes:
            lineas.append(f"- [[{slugs[arista.destino]}]] — lo desbloquea")
        for arista in entrantes:
            lineas.append(f"- [[{slugs[arista.origen]}]] — requiere")
    lineas.append("")
    return "\n".join(lineas)


def _indice(grafo: Grafo, ids: Sequence[str], slugs: dict[str, str]) -> str:
    nodos = [grafo.nodos[nodo_id] for nodo_id in ids]
    activos = sum(1 for nodo in nodos if nodo.estado == "activo")
    apagados = len(nodos) - activos
    por_origen = {origen: sum(1 for nodo in nodos if nodo.origen == origen) for origen in ORIGENES}
    detalle = " · ".join(f"{origen} {cuenta}" for origen, cuenta in por_origen.items())
    lineas = [
        "---",
        'tipo: "indice"',
        f"nodos: {len(nodos)}",
        f"aristas: {len(grafo.aristas)}",
        "---",
        "",
        "# Grafo de la tribu",
        "",
        "Export de `tribal export obsidian`: un fichero por nodo y un enlace "
        "wiki por cada arista de entrada y de salida.",
        "",
        "## Resumen",
        "",
        f"- Nodos: {len(nodos)} (activos {activos}, apagados {apagados})",
        f"- Aristas: {len(grafo.aristas)}",
        f"- Por origen: {detalle}",
        "",
        "## Nodos",
        "",
    ]
    lineas.extend(
        f"- [[{slugs[nodo.id]}]] — {_una_linea(nodo.titulo)} ({nodo.rama}, {nodo.estado})"
        for nodo in nodos
    )
    lineas.append("")
    return "\n".join(lineas)


def _yaml(valor: str) -> str:
    """Escalar YAML entre comillas dobles seguro ante `:`, `#` y comillas."""
    return json.dumps(_texto(valor), ensure_ascii=False)


def _una_linea(valor: str) -> str:
    return " ".join(_texto(valor).split())


def _texto(valor: str) -> str:
    """Una sola convención de salto de línea: LF, también en el contenido."""
    return valor.replace("\r\n", "\n").replace("\r", "\n")


def _escribir(ruta: Path, contenido: str) -> None:
    ruta.write_text(_texto(contenido), encoding="utf-8", newline="\n")
