"""Diario y narración (concepto §10).

El motor anota el hito y el LLM solo pone la frase: si el modelo está apagado,
falla o no hay hueco en la cola, la entrada existe igual con `narrada=False`.
El texto que devuelve el modelo se guarda tal cual; el diálogo de una decisión
se asocia al individuo que la tomó.
"""

from __future__ import annotations

import json
import random
import time
from typing import Any

import pytest

from tribal.cli import main
from tribal.config import SimConfig
from tribal.core.genoma import Genoma
from tribal.core.habilidades import Habilidades
from tribal.core.modelos import Individuo, Mundo, Necesidades, TipoTile
from tribal.culture.diario import Diario
from tribal.llm.cliente import ClienteLLM, Transporte, backend_falso, backend_stub
from tribal.llm.cola import ColaLLM, Peticion
from tribal.sim import MS_FRAME, UMBRAL_ANCIANO, Simulacion, run


def _mundo(*individuos: Individuo) -> Mundo:
    """Seis por seis de hierba, sin recursos: un mundo mínimo para un tick."""
    tiles = [[TipoTile.HIERBA for _ in range(6)] for _ in range(6)]
    return Mundo(
        ancho=6,
        alto=6,
        tiles=tiles,
        recursos=[],
        individuos=list(individuos),
        azar=random.Random(0),
    )


def _individuo(
    id_: int,
    *,
    salud: float = 100.0,
    energia: float = 100.0,
    sed: float = 0.0,
) -> Individuo:
    return Individuo(
        id=id_,
        sexo="m",
        genoma=Genoma(divergencia=0.5),
        necesidades=Necesidades(energia=energia, sed=sed, salud=salud),
        x=1.0,
        y=1.0,
        habilidades=Habilidades.iniciales(),
    )


def _ollama(contenido: object) -> tuple[int, bytes]:
    """Sobre de `/api/chat` con el contenido JSON del mensaje."""
    sobre = {"message": {"role": "assistant", "content": json.dumps(contenido)}}
    return 200, json.dumps(sobre).encode()


def _sincrona(*respuestas: Any) -> ColaLLM:
    return ColaLLM(ClienteLLM(transporte=backend_falso(respuestas)), sincrona=True)


def _cuerpo_decision(accion: str, dialogo: str = "") -> dict[str, Any]:
    return {"accion": accion, "objetivo": "", "razon": "", "dialogo": dialogo}


def _lento(segundos: float) -> Transporte:
    """Transporte que tarda: mantiene peticiones en vuelo de verdad."""

    def transporte(
        _metodo: str,
        _url: str,
        cuerpo: dict[str, Any] | None,
        _timeout: float,
    ) -> tuple[int, bytes]:
        time.sleep(segundos)
        formato = (cuerpo or {}).get("format")
        propiedades = formato.get("properties") if isinstance(formato, dict) else None
        if isinstance(propiedades, dict) and "texto" in propiedades:
            return _ollama({"texto": "la chispa prendió"})
        return _ollama(_cuerpo_decision("beber", dialogo="hablo tarde"))

    return transporte


def test_el_diario_guarda_el_texto_tal_cual_y_cuenta_las_narradas() -> None:
    diario = Diario()
    indice = diario.registrar(7, "primer_fuego", individuo_id=3)

    assert diario.entradas[indice].narrada is False
    assert diario.narrar(indice, " el fuego es nuestro ") is True

    entrada = diario.ultimas(1)[0]
    assert entrada.texto == " el fuego es nuestro "
    assert entrada.narrada is True
    assert diario.a_json() == {"entradas": 1, "narradas": 1, "dialogos": 0}
    assert diario.ultimas(0) == []
    assert diario.ultimas(5) == [entrada]
    # Una frase vacía o un índice que no existe no narran nada.
    assert diario.narrar(0, "") is False
    assert diario.narrar(99, "tarde") is False
    assert diario.ultimas(1)[0].narrada is True


def test_un_tipo_de_entrada_inventado_es_un_error() -> None:
    with pytest.raises(ValueError, match="desconocido"):
        Diario().registrar(1, "hito_inventado")


def test_ultimas_ordena_por_tick_aunque_el_append_llegue_tarde() -> None:
    """Una decisión asíncrona puede anotar un tick anterior al último hito."""
    diario = Diario()
    diario.registrar(5, "primer_fuego", individuo_id=2)
    diario.registrar(1, "dialogo", individuo_id=1, texto="hablo tarde")

    assert [entrada.tick for entrada in diario.ultimas(2)] == [1, 5]
    assert [entrada.tick for entrada in diario.ultimas(1)] == [5]
    # El orden de inserción no se toca: solo se ordena la vista.
    assert [entrada.tick for entrada in diario.entradas] == [5, 1]

    # A igual tick manda el orden de llegada (sort estable).
    diario.registrar(7, "primer_fuego")
    diario.registrar(7, "primera_tradicion")
    assert [entrada.tipo for entrada in diario.ultimas(2)] == [
        "primer_fuego",
        "primera_tradicion",
    ]


def test_una_decision_tardia_no_desordena_el_diario() -> None:
    """Cola asíncrona lenta: el diálogo del tick 1 llega tras el hito del 5."""
    individuo = _individuo(1)
    cola = ColaLLM(ClienteLLM(transporte=_lento(0.2)))
    simulacion = Simulacion(
        _mundo(individuo),
        SimConfig(seed=0, individuos=1, depredadores=0),
        cola=cola,
    )
    try:
        simulacion.mundo.tick = 1
        assert cola.encolar(
            Peticion(
                id=1,
                tick=1,
                individuo_id=individuo.id,
                contexto={},
                candidatas=("beber", "descansar"),
                valida_hasta=100,
            )
        )
        simulacion.mundo.tick = 5
        simulacion._hito("primer_fuego", individuo, "la primera chispa")

        limite = time.perf_counter() + 5.0
        while time.perf_counter() < limite and simulacion.diario.cuenta("dialogo") == 0:
            time.sleep(0.02)
            simulacion._drenar()

        # Llegó tarde: el append queda 5, 1; la vista, 1, 5.
        assert [entrada.tick for entrada in simulacion.diario.entradas] == [5, 1]
        assert [entrada.tick for entrada in simulacion.diario.ultimas(2)] == [1, 5]
        ultimas = simulacion.resumen()["diario"]["ultimas"]
        assert [entrada["tick"] for entrada in ultimas] == [1, 5]
    finally:
        cola.cerrar()


def test_los_hitos_del_motor_entran_en_el_diario() -> None:
    """600 ticks de la semilla 42 descubren las cinco primeras veces."""
    simulacion = run(600, 42, headless=True)

    tipos = [entrada.tipo for entrada in simulacion.diario.entradas]
    for tipo in (
        "primer_fuego",
        "primera_caza_grupo",
        "primera_palabra",
        "primer_rito",
        "primera_tradicion",
    ):
        assert tipos.count(tipo) == 1, tipo

    # Sin capa LLM el hito se registra igual y la narración es opcional.
    assert simulacion.diario.a_json()["narradas"] == 0
    assert all(entrada.texto == "" for entrada in simulacion.diario.entradas)

    # El tick de la entrada es el del nodo que la provocó, y el nodo es el del
    # hecho: una palabra es `proto_palabras`, no los gestos del escalón 0.
    ticks = {
        entrada.tipo: entrada.tick
        for entrada in simulacion.diario.entradas
        if entrada.tipo != "primera_tradicion"
    }
    assert ticks["primer_fuego"] == simulacion.grafo.nodos["observar_rayo"].tick
    assert ticks["primera_palabra"] == simulacion.grafo.nodos["proto_palabras"].tick
    assert ticks["primer_rito"] == simulacion.grafo.nodos["ritual"].tick
    assert ticks["primera_caza_grupo"] == simulacion.grafo.nodos["caza_cooperativa"].tick


def test_el_texto_del_llm_se_usa_tal_cual() -> None:
    texto = "  la chispa prendió y nadie la dejó morir  "
    individuo = _individuo(1)
    simulacion = Simulacion(
        _mundo(individuo),
        SimConfig(seed=0, individuos=1, depredadores=0),
        cola=_sincrona(_ollama({"texto": texto})),
    )

    assert simulacion._practicar(individuo, "frotar_madera", descubrir=True) is True
    simulacion._drenar()

    entrada = simulacion.diario.ultimas(1)[0]
    assert entrada.tipo == "primer_fuego"
    assert entrada.texto == texto
    assert entrada.narrada is True


def test_si_el_llm_falla_el_hito_se_registra_sin_narracion() -> None:
    individuo = _individuo(1)
    simulacion = Simulacion(
        _mundo(individuo),
        SimConfig(seed=0, individuos=1, depredadores=0),
        cola=_sincrona(TimeoutError("ollama caído")),
    )

    assert simulacion._practicar(individuo, "frotar_madera", descubrir=True) is True
    simulacion._drenar()

    entrada = simulacion.diario.ultimas(1)[0]
    assert entrada.tipo == "primer_fuego"
    assert entrada.texto == ""
    assert entrada.narrada is False
    assert simulacion.diario.a_json()["entradas"] == 1


def test_cada_hito_del_motor_produce_su_entrada() -> None:
    individuo = _individuo(1)
    simulacion = Simulacion(_mundo(individuo), SimConfig(seed=0, individuos=1, depredadores=0))

    for accion, tipo, veces in (
        ("frotar_madera", "primer_fuego", 1),
        ("hablar", "primera_palabra", 2),  # gestos, luego proto_palabras
        ("pintar", "primer_rito", 2),  # arte_rupestre, luego ritual
    ):
        for escalon in range(veces):
            assert simulacion._practicar(individuo, accion, descubrir=True) is True
            if escalon < veces - 1:
                # El escalón intermedio no es el hecho: no hay entrada todavía.
                assert simulacion.diario.cuenta(tipo) == 0
        assert simulacion.diario.ultimas(1)[0].tipo == tipo

    # La lítica llega a la caza cooperativa en el quinto escalón.
    assert all(simulacion._practicar(individuo, "tallar", descubrir=True) for _ in range(5))
    assert simulacion.diario.cuenta("primera_caza_grupo") == 1

    simulacion.grafo.imitadores["guijarro"] = {2, 3, 4}
    simulacion.grafo.ultimo_imitador["guijarro"] = individuo.id
    simulacion.step()
    assert simulacion.diario.cuenta("primera_tradicion") == 1


def test_la_muerte_de_un_anciano_entra_en_el_diario() -> None:
    anciano = _individuo(1, salud=0.0)
    joven = _individuo(2, salud=0.0)
    anciano.edad = UMBRAL_ANCIANO
    joven.edad = 10
    simulacion = Simulacion(_mundo(anciano, joven), SimConfig(seed=0, individuos=2, depredadores=0))

    simulacion._enterrar()

    assert simulacion.muertes == 2
    entradas = simulacion.diario.entradas
    assert [entrada.tipo for entrada in entradas] == ["muerte_ancestro"]
    assert entradas[0].individuo_id == anciano.id


def test_el_dialogo_de_una_decision_se_asocia_a_su_individuo() -> None:
    individuo = _individuo(1)
    habla = "bebo yo primero y luego los demás"
    simulacion = Simulacion(
        _mundo(individuo),
        SimConfig(seed=0, individuos=1, depredadores=0),
        cola=_sincrona(_ollama(_cuerpo_decision("beber", dialogo=habla))),
    )
    assert simulacion.cola is not None
    assert simulacion.cola.encolar(
        Peticion(
            id=1,
            tick=3,
            individuo_id=individuo.id,
            contexto={},
            candidatas=("beber", "descansar"),
            valida_hasta=100,
        )
    )

    simulacion._drenar()

    entrada = simulacion.diario.ultimas(1)[0]
    assert entrada.tipo == "dialogo"
    assert entrada.texto == habla
    assert entrada.individuo_id == individuo.id
    assert simulacion.resumen()["diario"]["dialogos"] == 1


def test_con_backend_falso_cada_hito_y_el_dialogo_quedan_en_el_diario() -> None:
    """Los cuatro hitos del criterio y el diálogo, con un backend de mentira."""
    narraciones: list[str] = []

    def transporte(
        _metodo: str,
        _url: str,
        cuerpo: dict[str, Any] | None,
        _timeout: float,
    ) -> tuple[int, bytes]:
        formato = (cuerpo or {}).get("format")
        propiedades = formato.get("properties") if isinstance(formato, dict) else None
        if isinstance(propiedades, dict) and "texto" in propiedades:
            narraciones.append("narracion")
            return _ollama({"texto": "lo vieron y desde entonces lo cuentan"})
        return _ollama(_cuerpo_decision("beber", dialogo="bebo yo primero"))

    individuo = _individuo(1)
    simulacion = Simulacion(
        _mundo(individuo),
        SimConfig(seed=0, individuos=1, depredadores=0),
        cola=ColaLLM(ClienteLLM(transporte=transporte), sincrona=True),
    )
    for accion, veces in (
        ("frotar_madera", 1),
        ("hablar", 2),  # gestos → proto_palabras
        ("pintar", 2),  # arte_rupestre → ritual
    ):
        for _ in range(veces):
            assert simulacion._practicar(individuo, accion, descubrir=True) is True
    for _ in range(5):
        assert simulacion._practicar(individuo, "tallar", descubrir=True)
    simulacion._drenar()

    tipos = {entrada.tipo for entrada in simulacion.diario.entradas}
    assert {"primer_fuego", "primera_palabra", "primer_rito", "primera_caza_grupo"} <= tipos
    assert all(entrada.narrada for entrada in simulacion.diario.entradas)
    assert all(entrada.individuo_id == individuo.id for entrada in simulacion.diario.entradas)
    assert len(narraciones) == 4

    assert simulacion.cola is not None
    assert simulacion.cola.encolar(
        Peticion(
            id=1,
            tick=5,
            individuo_id=individuo.id,
            contexto={},
            candidatas=("beber", "descansar"),
            valida_hasta=100,
        )
    )
    simulacion._drenar()

    dialogo = simulacion.diario.ultimas(1)[0]
    assert (dialogo.tipo, dialogo.texto, dialogo.individuo_id) == (
        "dialogo",
        "bebo yo primero",
        individuo.id,
    )


def test_la_narracion_sincrona_es_determinista() -> None:
    def corrida() -> list[dict[str, Any]]:
        cola = ColaLLM(ClienteLLM(transporte=backend_stub()), sincrona=True)
        simulacion = run(600, 42, headless=True, cola=cola)
        return [entrada.a_json() for entrada in simulacion.diario.entradas]

    primera = corrida()
    assert primera and all(entrada["narrada"] for entrada in primera)
    assert primera == corrida()


def test_report_diary_json_imprime_las_ultimas(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["report", "diary", "--json", "--last", "5"]) == 0

    informe = json.loads(capsys.readouterr().out)
    assert informe["seed"] == 42
    assert len(informe["ultimas"]) == 5
    tipos = {entrada["tipo"] for entrada in informe["ultimas"]}
    assert {"primer_fuego", "primera_palabra", "primera_caza_grupo"} <= tipos
    assert all(entrada["narrada"] is False for entrada in informe["ultimas"])


def test_report_diary_rechaza_parametros_invalidos() -> None:
    assert main(["report", "diary", "--last", "0"]) == 2
    assert main(["report", "diary", "--llm", "http", "--llm-sincrono"]) == 2


def test_report_diary_ordena_una_serie_desordenada(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`report diary` usa `Diario.ultimas`: un append tardío no rompe el orden."""
    simulacion = Simulacion(_mundo(_individuo(1)), SimConfig(seed=0, individuos=1, depredadores=0))
    simulacion.diario.registrar(5, "primer_fuego", individuo_id=1)
    simulacion.diario.registrar(1, "dialogo", individuo_id=1, texto="hablo tarde")
    monkeypatch.setattr("tribal.cli.run_sim", lambda *_args, **_kwargs: simulacion)

    assert main(["report", "diary", "--json", "--last", "5"]) == 0

    informe = json.loads(capsys.readouterr().out)
    assert [entrada["tick"] for entrada in informe["ultimas"]] == [1, 5]


def test_la_cola_no_bloquea_el_tick_con_un_transporte_lento() -> None:
    """Con 400 ms por inferencia, el tick sigue por debajo de 16.67 ms."""
    dilematico = _individuo(1, energia=40.0, sed=70.0, salud=10.0)
    cola = ColaLLM(ClienteLLM(transporte=_lento(0.4)))
    simulacion = Simulacion(
        _mundo(dilematico),
        SimConfig(seed=0, individuos=1, depredadores=0, max_pensando=1),
        cola=cola,
    )
    try:
        for _ in range(10):
            simulacion.step()

        assert simulacion.mundo.tick == 10
        assert simulacion.ms_tick_medio < MS_FRAME
        assert cola.estadisticas["enviadas"] >= 1
        # La inferencia sigue en vuelo mientras el motor ya pasó de tick.
        assert cola.estadisticas["en_vuelo"] >= 1
    finally:
        cola.cerrar()


def test_el_backend_stub_narra_por_hash() -> None:
    transporte: Transporte = backend_stub()
    cliente = ClienteLLM(transporte=transporte)

    primera = cliente.narrar("primer_fuego", {"tick": 2})
    segunda = cliente.narrar("primer_fuego", {"tick": 2})

    assert primera.estado == "ok"
    assert primera.texto and primera.texto == segunda.texto
