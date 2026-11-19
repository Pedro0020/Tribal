"""
La capa de consulta del grafo: preguntarle a la cultura, no solo verla.

Stack §6 lo pide explícito: la vista de grafo deja **ver** la constelación y
esto deja **preguntarle**. `consultar(grafo, texto)` reconoce la intención por
palabras clave —documentadas aquí porque son el contrato— y responde con datos
del grafo, sin inventar citas:

- **ruta** (`ruta`, `camino`, `lleva`/`llevo`, `llega`/`llegar`/`llego`,
  `conecta`, `hasta`): busca el nodo destino por título o id (fuzzy simple, sin
  tildes y sin mayúsculas). Si la pregunta nombra una rama (`litica`, `fuego`,
  `lenguaje`, `roles`, `simbolico`) y ningún título coincide, el destino es el
  nodo activo más avanzado de esa rama. El camino es el más corto en aristas
  tratadas como no dirigidas, desde la raíz de la rama del destino (su nivel 0,
  o el nodo más antiguo si la rama no tiene raíz) hasta el destino. Cada paso
  lleva su `origen`, `autor`, `tick` y la arista con la que se llegó.
- **apagados** (`apag*`, `perdid*`, `murieron`/`murio`,
  `fallecieron`/`fallecio`, `desaparecieron`/`desaparecio`): lista los nodos
  `apagado` con su tick y motivo, su autor (el portador original) y el último
  portador conocido si el grafo lo trae; si no, `desconocido`.

Una pregunta sin respuesta no es un error del comando: un destino que no
existe devuelve el camino vacío y `motivo="no encontrado"`. La CLI sale con 0;
solo una base inválida es un error (código 2), y eso lo decide `cli`.
"""

from __future__ import annotations

import re
import unicodedata
from collections import deque
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from tribal.culture.arbol import RAMAS, Nodo
from tribal.culture.grafo import Grafo

#: Palabras que piden una ruta. Se comparan sin tildes ni mayúsculas.
_PALABRAS_RUTA = frozenset(
    {"ruta", "camino", "lleva", "llevo", "llega", "llegar", "llego", "conecta", "hasta"}
)
#: Prefijos que piden el inventario de técnicas perdidas.
_PREFIJOS_APAGADOS = ("apag", "perdid")
#: Formas que no comparten prefijo con las anteriores pero significan lo mismo.
_PALABRAS_APAGADOS = frozenset(
    {
        "murieron",
        "murio",
        "fallecieron",
        "fallecio",
        "desaparecieron",
        "desaparecio",
    }
)
#: Palabras de la pregunta que no nombran ningún nodo ni rama.
_VACIAS = frozenset(
    {
        "a",
        "al",
        "como",
        "cual",
        "cuales",
        "cuando",
        "de",
        "del",
        "donde",
        "el",
        "en",
        "fue",
        "fueron",
        "hacia",
        "hasta",
        "la",
        "las",
        "los",
        "me",
        "nodo",
        "nodos",
        "por",
        "para",
        "que",
        "quien",
        "quienes",
        "se",
        "un",
        "una",
    }
)
#: Dos candidatos a este distancia o menos se consideran ambiguos y se avisa.
_MARGEN_AMBIGUEDAD = 0.15


@dataclass(frozen=True, slots=True)
class Paso:
    """Un nodo del camino y la arista con la que se llegó a él."""

    id: str
    titulo: str
    rama: str
    origen: str
    autor: int
    tick: int
    #: Nodo anterior en el camino; None en el primero.
    desde: str | None

    def a_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "titulo": self.titulo,
            "rama": self.rama,
            "origen": self.origen,
            "autor": self.autor,
            "tick": self.tick,
            "arista": None if self.desde is None else {"de": self.desde, "a": self.id},
        }


@dataclass(frozen=True, slots=True)
class Apagado:
    """Un nodo `apagado` con quién lo sostenía y cuándo se perdió."""

    id: str
    titulo: str
    rama: str
    autor: int
    tick: int
    tick_apagado: int
    motivo_apagado: str
    ultimo_portador: str

    def a_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "titulo": self.titulo,
            "rama": self.rama,
            "autor": self.autor,
            "tick": self.tick,
            "tick_apagado": self.tick_apagado,
            "motivo_apagado": self.motivo_apagado,
            "ultimo_portador": self.ultimo_portador,
        }


@dataclass(frozen=True, slots=True)
class Respuesta:
    """Lo que devuelve una pregunta. Vacía no es error: lleva `motivo`."""

    consulta: str
    intencion: str
    destino: str | None = None
    camino: tuple[Paso, ...] = ()
    apagados: tuple[Apagado, ...] = ()
    #: "" si hubo respuesta; si no, por qué no la hay.
    motivo: str = ""
    #: Aviso cuando la pregunta tenía varios candidatos y se eligió el más cercano.
    aviso: str = ""

    def a_json(self) -> dict[str, Any]:
        return {
            "consulta": self.consulta,
            "intencion": self.intencion,
            "destino": self.destino,
            "camino": [paso.a_json() for paso in self.camino],
            "apagados": [apagado.a_json() for apagado in self.apagados],
            "motivo": self.motivo,
            "aviso": self.aviso,
        }

    def texto(self) -> str:
        lineas = [f"pregunta: {self.consulta}", f"intencion: {self.intencion}"]
        if self.intencion == "ruta":
            if not self.camino:
                lineas.append(f"sin respuesta: {self.motivo or 'no encontrado'}")
                return "\n".join(lineas)
            destino = self.camino[-1]
            lineas.append(f"destino: {destino.id} - {destino.titulo}")
            lineas.append(f"camino ({len(self.camino)} pasos):")
            for numero, paso in enumerate(self.camino, start=1):
                arista = f"  <- {paso.desde}" if paso.desde is not None else ""
                lineas.append(
                    f"  {numero}. {paso.id} - {paso.titulo}{arista}"
                    f"  [rama {paso.rama} | origen {paso.origen} | autor {paso.autor}"
                    f" | tick {paso.tick}]"
                )
        elif self.intencion == "apagados":
            if not self.apagados:
                lineas.append("no hay nodos apagados")
                return "\n".join(lineas)
            lineas.append(f"apagados ({len(self.apagados)}):")
            for apagado in self.apagados:
                lineas.append(
                    f"  - {apagado.id} - {apagado.titulo}"
                    f"  [rama {apagado.rama} | autor {apagado.autor}"
                    f" | tick_apagado {apagado.tick_apagado}"
                    f" | motivo {apagado.motivo_apagado or 'desconocido'}"
                    f" | ultimo portador {apagado.ultimo_portador}]"
                )
        else:
            lineas.append(f"sin respuesta: {self.motivo or 'no entiendo la pregunta'}")
        if self.aviso:
            lineas.append(f"aviso: {self.aviso}")
        return "\n".join(lineas)


def consultar(grafo: Grafo, texto: str) -> Respuesta:
    """Responde a `texto` con datos de `grafo`; nunca lanza por una pregunta."""
    palabras = _palabras(texto)
    if any(
        palabra.startswith(_PREFIJOS_APAGADOS) or palabra in _PALABRAS_APAGADOS
        for palabra in palabras
    ):
        return _consultar_apagados(grafo, texto)
    if palabras & _PALABRAS_RUTA:
        return _consultar_ruta(grafo, texto, palabras)
    return Respuesta(
        consulta=texto,
        intencion="desconocida",
        motivo="no entiendo la pregunta; intenciones: ruta, apagados",
    )


def _consultar_ruta(grafo: Grafo, texto: str, palabras: set[str]) -> Respuesta:
    """Camino mínimo no dirigido hasta el nodo (o la rama) que nombra la pregunta."""
    significativas = palabras - _VACIAS - _PALABRAS_RUTA
    destino, aviso = _elegir_destino(grafo, significativas)

    if destino is None:
        return Respuesta(consulta=texto, intencion="ruta", motivo="no encontrado", aviso=aviso)

    camino = _camino_minimo(grafo, _raiz_de(grafo, destino), destino.id)
    if camino is None:
        return Respuesta(
            consulta=texto,
            intencion="ruta",
            destino=destino.id,
            motivo="sin camino",
            aviso=aviso,
        )
    pasos = tuple(
        _paso(grafo.nodos[nodo_id], camino[indice - 1] if indice else None)
        for indice, nodo_id in enumerate(camino)
    )
    return Respuesta(
        consulta=texto,
        intencion="ruta",
        destino=destino.id,
        camino=pasos,
        aviso=aviso,
    )


def _consultar_apagados(grafo: Grafo, texto: str) -> Respuesta:
    """Los nodos `apagado`, en orden de defunción (tick y luego id)."""
    apagados = tuple(
        Apagado(
            id=nodo.id,
            titulo=nodo.titulo,
            rama=nodo.rama,
            autor=nodo.autor,
            tick=nodo.tick,
            tick_apagado=nodo.tick_apagado,
            motivo_apagado=nodo.motivo_apagado,
            ultimo_portador=(
                f"ind-{grafo.ultimo_imitador[nodo.id]}"
                if nodo.id in grafo.ultimo_imitador
                else "desconocido"
            ),
        )
        for nodo in sorted(
            (nodo for nodo in grafo.nodos.values() if nodo.estado == "apagado"),
            key=lambda nodo: (nodo.tick_apagado, nodo.id),
        )
    )
    return Respuesta(consulta=texto, intencion="apagados", apagados=apagados)


def _elegir_destino(grafo: Grafo, palabras: set[str]) -> tuple[Nodo | None, str]:
    """Nodo destino y aviso si la pregunta tenía varios candidatos parecidos.

    Prioridad: un título o id que coincide entero (pocas palabras, sin duda) >
    una rama nombrada (su nodo activo más avanzado) > el título más parecido.
    Así "al fuego" va a la rama del fuego y no a "Cuchillo al fuego", pero
    "a la lasca" sigue yendo al nodo exacto.
    """
    candidatos = _candidatos(grafo, palabras)
    exactos = [(puntuacion, nodo) for puntuacion, nodo in candidatos if _exacto(nodo, palabras)]
    if exactos:
        return exactos[0][1], _aviso(exactos)
    for rama in RAMAS:
        if rama in palabras:
            nodo = _por_rama(grafo, rama)
            if nodo is not None:
                return nodo, ""
    if not candidatos:
        return None, ""
    return candidatos[0][1], _aviso(candidatos)


def _exacto(nodo: Nodo, palabras: set[str]) -> bool:
    claves = (_palabras(nodo.titulo) | _palabras(nodo.id.replace("_", " "))) - _VACIAS
    return bool(palabras) and claves == palabras


def _aviso(candidatos: list[tuple[float, Nodo]]) -> str:
    """Texto de ambigüedad cuando el segundo candidato está casi tan cerca."""
    if len(candidatos) < 2 or candidatos[0][0] - candidatos[1][0] > _MARGEN_AMBIGUEDAD:
        return ""
    otros = ", ".join(nodo.id for _, nodo in candidatos[:3])
    return f"{len(candidatos)} candidatos ({otros}); elijo {candidatos[0][1].id}, el más cercano"


def _paso(nodo: Nodo, desde: str | None) -> Paso:
    return Paso(
        id=nodo.id,
        titulo=nodo.titulo,
        rama=nodo.rama,
        origen=nodo.origen,
        autor=nodo.autor,
        tick=nodo.tick,
        desde=desde,
    )


def _candidatos(grafo: Grafo, palabras: set[str]) -> list[tuple[float, Nodo]]:
    """Nodos cuyo título o id comparte alguna palabra con la pregunta, mejor primero.

    El parecido de secuencia desempata títulos que comparten la misma palabra
    ("Fuego" gana a "Fuego sagrado"), y el id hace determinista el orden.
    """
    if not palabras:
        return []
    consulta = " ".join(sorted(palabras))
    candidatos: list[tuple[float, Nodo]] = []
    for nodo in grafo.nodos.values():
        claves = (_palabras(nodo.titulo) | _palabras(nodo.id.replace("_", " "))) - _VACIAS
        if not palabras & claves:
            continue
        cobertura = len(palabras & claves) / len(palabras)
        parecido = SequenceMatcher(None, consulta, " ".join(sorted(claves))).ratio()
        candidatos.append((cobertura + parecido, nodo))
    return sorted(candidatos, key=lambda par: (-par[0], par[1].id))


def _por_rama(grafo: Grafo, rama: str) -> Nodo | None:
    """El nodo activo más avanzado de la rama nombrada, si tiene alguno."""
    nodos = [nodo for nodo in grafo.nodos.values() if nodo.rama == rama]
    activos = [nodo for nodo in nodos if nodo.estado == "activo"]
    return max(activos, key=lambda nodo: (nodo.nivel, nodo.id)) if activos else None


def _raiz_de(grafo: Grafo, destino: Nodo) -> str:
    """Raíz de la rama del destino: su nivel 0, o el nodo más antiguo si no hay."""
    hermanos = [nodo for nodo in grafo.nodos.values() if nodo.rama == destino.rama]
    nivel_cero = [nodo for nodo in hermanos if nodo.nivel == 0]
    if nivel_cero:
        return min(nivel_cero, key=lambda nodo: (nodo.tick, nodo.id)).id
    return min(hermanos, key=lambda nodo: (nodo.tick, nodo.id)).id


def _camino_minimo(grafo: Grafo, inicio: str, destino: str) -> list[str] | None:
    """BFS no dirigido y determinista (vecinos ordenados); None si no hay camino."""
    adyacencia: dict[str, list[str]] = {}
    for arista in grafo.aristas:
        if arista.origen not in grafo.nodos or arista.destino not in grafo.nodos:
            continue
        adyacencia.setdefault(arista.origen, []).append(arista.destino)
        adyacencia.setdefault(arista.destino, []).append(arista.origen)
    for vecinos in adyacencia.values():
        vecinos.sort()

    previo: dict[str, str | None] = {inicio: None}
    cola: deque[str] = deque([inicio])
    while cola:
        actual = cola.popleft()
        if actual == destino:
            break
        for vecino in adyacencia.get(actual, ()):
            if vecino not in previo:
                previo[vecino] = actual
                cola.append(vecino)

    if destino not in previo:
        return None
    camino: list[str] = []
    actual_camino: str | None = destino
    while actual_camino is not None:
        camino.append(actual_camino)
        actual_camino = previo[actual_camino]
    return list(reversed(camino))


def _palabras(texto: str) -> set[str]:
    """Minúsculas, sin tildes y sin puntuación: '¿Qué ruta al fuego?' → palabras."""
    descompuesto = unicodedata.normalize("NFKD", texto.lower())
    limpio = "".join(caracter for caracter in descompuesto if not unicodedata.combining(caracter))
    return set(re.findall(r"[a-z0-9]+", limpio))
