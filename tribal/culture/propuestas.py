"""
Propuestas de nodo del LLM: nivel 1 de concepto §8b, validadas por el motor.

El modelo no escribe en el grafo: propone y el motor decide. Una propuesta es
una combinación de dos técnicas **ya activas**. Si el id está en
`combinaciones.py`, la propuesta se delega al catálogo curado y el nodo nace
con `origen="combinacion"`, como si lo hubiera cruzado un divergente. Si el id
no está en el catálogo, se aplica una **regla de plausibilidad**: los dos
requisitos activos, de la misma rama o de ramas adyacentes en `RAMAS`, y la
rama propuesta es una de las dos. El contenido se ancla a los dos requisitos y
el efecto es un −1 %/−2 % de sed derivado de sus ids
(`beneficios.perfil_de`). Un id `comb_*` nace como `combinacion` (regla de
plausibilidad) y **no puede encadenarse**: sus requisitos no pueden ser otro
`comb_*` ni un `llm_*`. El resto de propuestas nuevas nace como `llm` —nivel 1
de §8b: el modelo une dos nodos existentes en un paso no previsto—. El catálogo
curado sigue teniendo prioridad en el backend y conserva sus efectos y
habilidades.

Lo que no cumple la regla se rechaza y se cuenta: un nodo inventado no puede
saltarse el árbol por ser una frase bonita. La validación vive aquí y no en el
prompt para que sea la misma con cualquier modelo y se pueda probar sin red.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from tribal.culture.arbol import ARBOL, RAMAS, Nodo, Origen, Rama
from tribal.culture.combinaciones import COMBINACIONES
from tribal.culture.grafo import Grafo, PrerequisitoFaltante

#: Id de nodo: minúsculas, empieza por letra, sin acentos ni espacios.
ID_VALIDO = re.compile(r"^[a-z][a-z0-9_]{1,39}$")
#: Topes de texto: una propuesta es una frase, no un ensayo.
MAX_TITULO = 80
MAX_CONTENIDO = 240


class PropuestaInvalida(ValueError):
    """La propuesta no pasa la regla de plausibilidad; el nodo no nace."""

    def __init__(self, motivo: str) -> None:
        self.motivo = motivo
        super().__init__(motivo)


@dataclass(frozen=True, slots=True)
class Propuesta:
    """Lo que devuelve el modelo, ya desenvuelto del JSON."""

    id: str
    rama: Rama
    requisitos: tuple[str, str]
    titulo: str
    contenido: str


def parsear(datos: object) -> Propuesta:
    """Lee el JSON del modelo y lo convierte en `Propuesta`; nunca toca el grafo."""
    if not isinstance(datos, Mapping):
        raise PropuestaInvalida("formato: la propuesta no es un objeto JSON")

    nodo_id = datos.get("id")
    if not isinstance(nodo_id, str) or not ID_VALIDO.match(nodo_id):
        raise PropuestaInvalida(f"formato: id inválido: {nodo_id!r}")

    rama = datos.get("rama")
    if not isinstance(rama, str) or rama not in RAMAS:
        raise PropuestaInvalida(f"formato: rama inválida: {rama!r}")

    requisitos = datos.get("requisitos")
    if (
        not isinstance(requisitos, list)
        or len(requisitos) != 2
        or not all(isinstance(requisito, str) for requisito in requisitos)
    ):
        raise PropuestaInvalida("formato: requisitos deben ser dos ids")
    primero, segundo = requisitos
    if primero == segundo:
        raise PropuestaInvalida("formato: los dos requisitos son el mismo nodo")

    titulo = datos.get("titulo")
    if not isinstance(titulo, str) or not titulo.strip() or len(titulo) > MAX_TITULO:
        raise PropuestaInvalida("formato: falta el título o es demasiado largo")

    contenido = datos.get("contenido")
    if not isinstance(contenido, str) or not contenido.strip() or len(contenido) > MAX_CONTENIDO:
        raise PropuestaInvalida("formato: falta el contenido o es demasiado largo")

    return Propuesta(
        id=nodo_id,
        rama=rama,
        requisitos=(primero, segundo),
        titulo=titulo.strip(),
        contenido=contenido.strip(),
    )


def validar(propuesta: Propuesta, grafo: Grafo, *, autor: int, tick: int) -> Nodo:
    """Crea el nodo si la propuesta es plausible; `PropuestaInvalida` si no.

    El catálogo manda: si el id existe en `COMBINACIONES`, se comprueba que la
    propuesta no cambie sus requisitos y se delega en `Grafo.descubrir`, que
    vuelve a validar prerrequisitos y escribe `origen="combinacion"`. Un id
    nuevo solo entra si los dos requisitos están activos, son de la misma rama o
    de ramas adyacentes, y la rama propuesta es una de las dos.
    """
    if propuesta.id in ARBOL:
        raise PropuestaInvalida(f"duplicado: {propuesta.id!r} ya está en el árbol")

    if propuesta.id in grafo.nodos:
        raise PropuestaInvalida(f"duplicado: {propuesta.id!r} ya está descubierto")

    if propuesta.id in COMBINACIONES:
        plantilla = COMBINACIONES[propuesta.id]
        if set(propuesta.requisitos) != set(plantilla.requisitos):
            raise PropuestaInvalida(
                f"catalogo: {propuesta.id!r} exige {plantilla.requisitos}, "
                f"no {propuesta.requisitos}"
            )
        try:
            return grafo.descubrir(propuesta.id, autor=autor, tick=tick, origen="combinacion")
        except PrerequisitoFaltante as exc:
            raise PropuestaInvalida(f"prerrequisito: {exc}") from None

    # La cadena comb -> comb (o comb -> llm) era inflación: cada cruce se
    # apoyaba en el anterior y el KPI crecía con el grafo, no con la cultura.
    if propuesta.id.startswith("comb_") and any(
        requisito.startswith(("comb_", "llm_")) for requisito in propuesta.requisitos
    ):
        raise PropuestaInvalida(
            "cadena: una combinación no puede apoyarse en otra combinación ni en un nodo llm"
        )

    ramas: list[Rama] = []
    niveles: list[int] = []
    for requisito in propuesta.requisitos:
        nodo = grafo.nodos.get(requisito)
        if nodo is None or nodo.estado != "activo":
            raise PropuestaInvalida(f"prerrequisito: {requisito!r} no está activo")
        ramas.append(nodo.rama)
        niveles.append(nodo.nivel)

    if not _ramas_plausibles(ramas, propuesta.rama):
        raise PropuestaInvalida(
            f"rama: {propuesta.rama!r} no es la misma ni adyacente a {tuple(ramas)!r}"
        )

    nivel = max(niveles) + 1
    # El contenido se ancla a los dos requisitos: la técnica nueva no es una
    # frase suelta, es el cruce de dos prácticas que la tribu ya tiene.
    enlaces = " y ".join(grafo.nodos[requisito].titulo for requisito in propuesta.requisitos)
    contenido = f"{propuesta.contenido} Une {enlaces}."
    if len(contenido) > MAX_CONTENIDO:
        contenido = contenido[:MAX_CONTENIDO].rstrip()
    # `comb_*` es una combinación de la regla de plausibilidad; el resto de
    # propuestas nuevas son del modelo y se guardan como nivel 1 `llm`.
    origen: Origen = "combinacion" if propuesta.id.startswith("comb_") else "llm"
    nodo = Nodo(
        id=propuesta.id,
        rama=propuesta.rama,
        nivel=nivel,
        titulo=propuesta.titulo,
        contenido=contenido,
        requisitos=propuesta.requisitos,
        origen=origen,
        autor=autor,
        tick=tick,
    )
    return grafo.agregar(nodo)


def _ramas_plausibles(ramas: list[Rama], rama: Rama) -> bool:
    """Misma rama o adyacentes en `RAMAS`, y la propuesta es una de las dos."""
    if rama not in ramas:
        return False
    if len(set(ramas)) == 1:
        return rama == ramas[0]
    primera, segunda = (RAMAS.index(item) for item in ramas)
    return abs(primera - segunda) == 1
