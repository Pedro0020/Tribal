"""Puerta F2→F3: nodos fuera del árbol y narración concentrada (F2-006).

La propuesta del LLM no escribe en el grafo: el motor la valida. Una
combinación del catálogo se delega a `Grafo.descubrir`; un cruce nuevo solo
entra si sus dos requisitos están activos y son de la misma rama o de ramas
adyacentes. El cruce del modelo nace con `origen="llm"` y un `comb_*` de la
regla de plausibilidad con `origen="combinacion"`; ambos son nivel 1 de §8b. Un
`comb_*` no puede encadenarse con otro `comb_*` ni con un `llm_*`. La narración
se concentra porque el
cronista sale del peso de saliencia, no del censo.
"""

from __future__ import annotations

import json

import pytest

from tribal.cli import main
from tribal.culture.arbol import Nodo
from tribal.culture.grafo import Grafo
from tribal.culture.propuestas import Propuesta, PropuestaInvalida, parsear, validar
from tribal.gate_f2 import (
    CONCENTRACION_MINIMA,
    K_NODOS_FUERA,
    ORIGENES_FUERA,
    medir_semilla,
)


def _grafo(*nodos: str) -> Grafo:
    grafo = Grafo()
    for tick, nodo in enumerate(nodos, start=1):
        grafo.descubrir(nodo, autor=1, tick=tick)
    return grafo


def test_una_propuesta_nueva_plausible_nace_como_llm() -> None:
    grafo = _grafo("guijarro", "lasca", "bifaz", "observar_rayo", "conservar_brasas")
    propuesta = Propuesta(
        id="hacha_de_mano",
        rama="litica",
        requisitos=("bifaz", "conservar_brasas"),
        titulo="Hacha de mano",
        contenido="El bifaz atado a un mango de madera golpea con más fuerza.",
    )

    nodo = validar(propuesta, grafo, autor=7, tick=99)

    assert nodo.origen == "llm", "nivel 1 de §8b: el modelo une dos nodos activos"
    assert (nodo.autor, nodo.tick) == (7, 99)
    assert nodo.requisitos == ("bifaz", "conservar_brasas")
    assert "Bifaz" in nodo.contenido and "Conservar brasas" in nodo.contenido
    # Bifaz es nivel 2; el cruce nuevo un escalón por encima.
    assert nodo.nivel == 3
    assert grafo.nodos["hacha_de_mano"] is nodo

    with pytest.raises(PropuestaInvalida, match="duplicado"):
        validar(propuesta, grafo, autor=7, tick=100)


def test_una_combinacion_comb_no_puede_encadenarse() -> None:
    grafo = _grafo("guijarro", "lasca")
    grafo.agregar(
        Nodo(
            "comb_base",
            "litica",
            2,
            "Base",
            "Una combinación de la regla de plausibilidad.",
            requisitos=("guijarro", "lasca"),
            origen="combinacion",
            autor=1,
            tick=3,
        )
    )
    grafo.agregar(
        Nodo(
            "llm_base",
            "litica",
            1,
            "LlM base",
            "Un nodo del modelo.",
            requisitos=("guijarro",),
            origen="llm",
            autor=1,
            tick=4,
        )
    )

    for requisitos in (("comb_base", "lasca"), ("llm_base", "lasca")):
        propuesta = Propuesta(
            id="comb_nueva",
            rama="litica",
            requisitos=requisitos,
            titulo="Cadena",
            contenido="No puede apoyarse en otro nodo emergente.",
        )
        with pytest.raises(PropuestaInvalida, match="cadena"):
            validar(propuesta, grafo, autor=7, tick=99)

    # Con requisitos del árbol sí se acepta: el problema es la cadena.
    aceptada = validar(
        Propuesta(
            id="comb_nueva",
            rama="litica",
            requisitos=("guijarro", "lasca"),
            titulo="Cruce limpio",
            contenido="Dos nodos del árbol y nada más.",
        ),
        grafo,
        autor=7,
        tick=100,
    )
    assert aceptada.origen == "combinacion"


def test_una_propuesta_de_ramas_no_adyacentes_se_rechaza() -> None:
    grafo = _grafo("guijarro", "lasca", "bifaz", "arte_rupestre")
    propuesta = Propuesta(
        id="piedra_que_canta",
        rama="litica",
        requisitos=("bifaz", "arte_rupestre"),
        titulo="Piedra que canta",
        contenido="Un cruce entre lítica y símbolo que el árbol no permite.",
    )

    with pytest.raises(PropuestaInvalida, match="rama"):
        validar(propuesta, grafo, autor=7, tick=99)
    assert "piedra_que_canta" not in grafo.nodos


def test_una_propuesta_con_prerrequisito_inactivo_se_rechaza() -> None:
    grafo = _grafo("guijarro", "lasca")
    propuesta = Propuesta(
        id="canto_que_habla",
        rama="lenguaje",
        requisitos=("lasca", "gestos"),
        titulo="Canto que habla",
        contenido="Combina una lasca con algo que la tribu todavía no sabe.",
    )

    with pytest.raises(PropuestaInvalida, match="prerrequisito"):
        validar(propuesta, grafo, autor=7, tick=99)
    assert "canto_que_habla" not in grafo.nodos


def test_una_combinacion_del_catalogo_nace_con_origen_combinacion() -> None:
    grafo = _grafo("guijarro", "lasca", "bifaz")
    propuesta = Propuesta(
        id="raedera",
        rama="litica",
        requisitos=("lasca", "bifaz"),
        titulo="Raedera",
        contenido="La lasca ancha raspada con el filo del bifaz limpia la piel.",
    )

    nodo = validar(propuesta, grafo, autor=3, tick=12)

    assert nodo.origen == "combinacion"
    assert (nodo.autor, nodo.tick) == (3, 12)

    otra = Propuesta(
        id="raedera",
        rama="litica",
        requisitos=("lasca", "guijarro"),
        titulo="Raedera",
        contenido="Requisitos cambiados a mano.",
    )
    with pytest.raises(PropuestaInvalida, match="catalogo"):
        validar(otra, _grafo("guijarro", "lasca", "bifaz"), autor=3, tick=13)


def test_parsear_rechaza_un_id_inventado() -> None:
    with pytest.raises(PropuestaInvalida, match="id"):
        parsear(
            {
                "id": "NO VALE",
                "rama": "litica",
                "requisitos": ["lasca", "bifaz"],
                "titulo": "Mala",
                "contenido": "La forma no vale.",
            }
        )


def test_gate_f2_e2e_crea_nodos_y_rechaza_los_imposibles() -> None:
    """Una semilla fija con el backend guionizado: válidos entran, inválidos no."""
    fila = medir_semilla(1, ticks=3000, crisis=True, llm="script", sincrono=True)

    assert fila.por_origen["combinacion"] + fila.por_origen["llm"] >= K_NODOS_FUERA
    # El canal acepta cruces nuevos, que son nodos `llm` (nivel 1). Las cinco
    # del catálogo pueden llegar por el divergente; las imposibles se cuentan
    # por motivo, no se inscriben.
    assert fila.por_origen["llm"] >= 1
    assert fila.propuestas["por_origen"]["llm"] >= 1
    assert fila.propuestas["aceptadas"] == sum(fila.propuestas["por_origen"].values())
    assert fila.propuestas["rechazadas"] >= 1
    assert {"prerrequisito", "rama"} <= set(fila.propuestas["rechazos"])

    ids = {nodo["id"] for nodo in fila.fuera_arbol}
    assert all(nodo["origen"] in ORIGENES_FUERA for nodo in fila.fuera_arbol)
    assert all(isinstance(nodo["autor"], int) for nodo in fila.fuera_arbol)
    assert not any(
        nodo_id.startswith(("propuesta_imposible_", "propuesta_lejana_")) for nodo_id in ids
    )
    assert fila.veredicto()["success"]


@pytest.mark.parametrize("seed", (1, 3))
def test_los_tres_con_mas_saliencia_concentran_la_narracion(seed: int) -> None:
    fila = medir_semilla(seed, ticks=3000, crisis=True, llm="script", sincrono=True)

    assert fila.lineas_narradas > 0
    assert len(fila.top3) == 3
    assert all(saliencia > 0.0 for _, saliencia in fila.top3)
    assert [saliencia for _, saliencia in fila.top3] == sorted(
        (saliencia for _, saliencia in fila.top3), reverse=True
    )
    assert fila.concentracion >= CONCENTRACION_MINIMA


def test_gate_f2_sincrono_es_determinista() -> None:
    primera = medir_semilla(1, ticks=600, crisis=True, llm="script", sincrono=True)
    segunda = medir_semilla(1, ticks=600, crisis=True, llm="script", sincrono=True)

    assert primera.a_json() == segunda.a_json()


def test_report_culture_json_muestra_fuera_arbol_con_origen_y_autor(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["report", "culture", "--json", "--crisis", "--ticks", "3000"]) == 0

    datos = json.loads(capsys.readouterr().out)
    assert datos["fuera_arbol"]
    assert all(nodo["origen"] in ORIGENES_FUERA for nodo in datos["fuera_arbol"])
    assert all(
        isinstance(nodo["autor"], int) and isinstance(nodo["tick"], int)
        for nodo in datos["fuera_arbol"]
    )
    assert any(nodo["origen"] == "combinacion" for nodo in datos["fuera_arbol"])
