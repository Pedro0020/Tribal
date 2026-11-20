"""Cola asíncrona del LLM: presupuesto, ventana de validez y cierre sin fugas."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable

import pytest

from tribal.cli import main
from tribal.llm.cliente import ClienteLLM, Transporte, backend_falso, backend_stub
from tribal.llm.cola import NOMBRE_HILO, ColaLLM, Peticion
from tribal.sim import MS_FRAME, crear

CANDIDATAS = ("beber", "comer")


def _cuerpo(accion: str) -> bytes:
    contenido = {"accion": accion, "objetivo": "", "razon": "test", "dialogo": ""}
    return json.dumps({"message": {"role": "assistant", "content": json.dumps(contenido)}}).encode()


def _lento(segundos: float, accion: str = "beber") -> Transporte:
    """Backend que tarda `segundos` en responder: el caso que no debe bloquear."""

    def transporte(
        _metodo: str,
        _url: str,
        _cuerpo_http: dict[str, object] | None,
        _timeout: float,
    ) -> tuple[int, bytes]:
        time.sleep(segundos)
        return 200, _cuerpo(accion)

    return transporte


def _peticion(id_: int, tick: int = 0, ventana: int = 180) -> Peticion:
    return Peticion(
        id=id_,
        tick=tick,
        individuo_id=1,
        contexto={"tick": tick},
        candidatas=CANDIDATAS,
        valida_hasta=tick + ventana,
    )


def _esperar(condicion: Callable[[], bool], timeout: float = 2.0) -> None:
    fin = time.perf_counter() + timeout
    while time.perf_counter() < fin:
        if condicion():
            return
        time.sleep(0.005)
    raise AssertionError("la condición no se cumplió a tiempo")


def test_cola_llena_respeta_el_maximo_en_vuelo() -> None:
    liberar = threading.Event()

    def transporte(
        _metodo: str,
        _url: str,
        _cuerpo_http: dict[str, object] | None,
        _timeout: float,
    ) -> tuple[int, bytes]:
        liberar.wait(timeout=2.0)
        return 200, _cuerpo("beber")

    cola = ColaLLM(ClienteLLM(transporte=transporte), max_en_vuelo=1)
    assert cola.encolar(_peticion(1)) is True
    assert cola.encolar(_peticion(2)) is False  # sin hueco: el instinto manda
    assert cola.estadisticas["en_vuelo"] == 1
    assert cola.estadisticas["enviadas"] == 1

    liberar.set()
    cola.cerrar()
    assert cola.estadisticas["en_vuelo"] == 0


def test_backend_lento_200ms_no_frena_el_bucle() -> None:
    """1200 ticks con una inferencia de 200 ms: el mundo avanza y cabe en frame."""
    cola = ColaLLM(ClienteLLM(transporte=_lento(0.2)), max_en_vuelo=2)
    simulacion = crear(42, 12, cola=cola)
    en_vuelo_max = 0

    inicio = time.perf_counter()
    for _ in range(1200):
        simulacion.step()
        en_vuelo_max = max(en_vuelo_max, cola.estadisticas["en_vuelo"])
    transcurrido = time.perf_counter() - inicio

    assert simulacion.mundo.tick == 1200
    assert cola.estadisticas["enviadas"] >= 1
    assert en_vuelo_max >= 1  # hubo ticks con la petición todavía en vuelo
    assert simulacion.ms_tick_medio < MS_FRAME
    assert transcurrido < 10.0  # en serie serían 240 s

    cola.cerrar()
    assert cola.estadisticas["en_vuelo"] == 0


def test_resultado_fuera_de_ventana_se_descarta() -> None:
    cola = ColaLLM(ClienteLLM(transporte=backend_stub()), max_en_vuelo=2, ventana=5)
    assert cola.encolar(_peticion(1, tick=0, ventana=5)) is True
    _esperar(lambda: cola.estadisticas["en_vuelo"] == 0)

    assert cola.drenar(tick_actual=2) != []  # dentro de la ventana sí vale
    cola.encolar(_peticion(2, tick=10, ventana=5))
    _esperar(lambda: cola.estadisticas["en_vuelo"] == 0)
    assert cola.drenar(tick_actual=16) == []  # 16 > 10 + 5: tarde
    assert cola.estadisticas["descartadas"] == 1

    cola.cerrar()


def test_cierre_no_deja_hilos_vivos() -> None:
    cola = ColaLLM(ClienteLLM(transporte=backend_stub()))
    assert cola.encolar(_peticion(1)) is True
    assert cola.cerrar() is True
    assert cola.cerrar() is True  # idempotente
    assert all(hilo.name != NOMBRE_HILO for hilo in threading.enumerate())
    assert cola.estadisticas["en_vuelo"] == 0


def test_cierre_rapido_con_peticiones_en_vuelo() -> None:
    """Dos peticiones aceptadas con un transporte de 150 ms: cierre limpio y rápido."""
    cola = ColaLLM(ClienteLLM(transporte=_lento(0.15), timeout=0.05), max_en_vuelo=2)
    assert cola.encolar(_peticion(1)) is True
    assert cola.encolar(_peticion(2)) is True
    assert cola.estadisticas["en_vuelo"] == 2

    inicio = time.perf_counter()
    assert cola.cerrar() is True
    transcurrido = time.perf_counter() - inicio

    assert transcurrido < 1.0
    assert cola.estadisticas["en_vuelo"] == 0
    assert cola.estadisticas["descartadas"] >= 1
    assert all(hilo.name != NOMBRE_HILO for hilo in threading.enumerate())
    assert cola.cerrar() is True  # idempotente: ni hilo ni contador se mueven
    assert cola.estadisticas["en_vuelo"] == 0


def _peticion_estrecha(id_: int, tick: int = 0, ventana: int = 0) -> Peticion:
    return Peticion(
        id=id_,
        tick=tick,
        individuo_id=1,
        contexto={},
        candidatas=("comer", "descansar"),
        valida_hasta=tick + ventana,
    )


def test_correccion_tardia_no_cuenta_como_corregida() -> None:
    cola = ColaLLM(
        ClienteLLM(transporte=backend_falso([_cuerpo("beber")])),
        ventana=0,
        sincrona=True,
    )
    assert cola.encolar(_peticion_estrecha(1)) is True

    assert cola.drenar(tick_actual=1) == []
    assert cola.estadisticas["corregidas"] == 0
    assert cola.estadisticas["descartadas"] == 1


def test_correccion_aceptada_cuenta_como_corregida() -> None:
    cola = ColaLLM(
        ClienteLLM(transporte=backend_falso([_cuerpo("beber")])),
        ventana=0,
        sincrona=True,
    )
    assert cola.encolar(_peticion_estrecha(1)) is True

    respuestas = cola.drenar(tick_actual=0)
    assert len(respuestas) == 1
    assert respuestas[0].corregida is True
    assert respuestas[0].decision is not None
    assert respuestas[0].decision.accion == "comer"
    assert cola.estadisticas["corregidas"] == 1


def test_http_con_servicio_muerto_cierra_limpio(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def caido(*_args: object, **_kwargs: object) -> object:
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", caido)
    inicio = time.perf_counter()
    assert main(["run", "--headless", "--json", "--llm", "http", "--ticks", "600"]) == 0
    transcurrido = time.perf_counter() - inicio

    llm = json.loads(capsys.readouterr().out)["llm"]
    assert llm["fallos"] > 0
    assert llm["en_vuelo"] == 0
    assert transcurrido < 20.0
    assert all(hilo.name != NOMBRE_HILO for hilo in threading.enumerate())


def test_sincrono_con_http_se_rechaza(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(["run", "--headless", "--json", "--llm", "http", "--llm-sincrono", "--ticks", "10"])
        == 2
    )
    assert "--llm-sincrono" in capsys.readouterr().err


def test_decision_rezagada_se_descarta_y_el_mundo_sigue_por_instinto() -> None:
    """Ventana de 1 tick y backend de 20 ms: todo llega tarde; nadie se congela."""
    cola = ColaLLM(ClienteLLM(transporte=_lento(0.02)), max_en_vuelo=4, ventana=1)
    simulacion = crear(42, 12, cola=cola)
    for _ in range(600):
        simulacion.step()

    assert simulacion.mundo.tick == 600
    assert cola.estadisticas["descartadas"] >= 1
    assert all(individuo.intencion_llm is None for individuo in simulacion.mundo.individuos)

    cola.cerrar()


def test_intencion_caducada_equivale_al_instinto() -> None:
    """Una intención fuera de ventana no cambia ni un tick: se ignora."""
    sin_llm = crear(7, 10)
    caducada = crear(7, 10)
    caducada.mundo.individuos[0].intencion_llm = ("descansar", caducada.mundo.tick - 1)

    for _ in range(5):
        sin_llm.step()
        caducada.step()

    assert caducada.resumen() == sin_llm.resumen()


def test_cli_json_con_stub_reporta_la_capa_llm(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "--headless", "--json", "--llm", "stub", "--ticks", "1200"]) == 0
    resumen = json.loads(capsys.readouterr().out)
    llm = resumen["llm"]
    assert set(llm) == {
        "peticiones",
        "aplicadas",
        "descartadas",
        "fallos",
        "corregidas",
        "en_vuelo",
        "acciones",
    }
    assert llm["peticiones"] > 0
    assert llm["en_vuelo"] == 0
    assert llm["aplicadas"] + llm["descartadas"] + llm["fallos"] <= llm["peticiones"]


def test_sin_llm_el_resumen_no_cambia(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "--headless", "--json", "--ticks", "120"]) == 0
    assert "llm" not in json.loads(capsys.readouterr().out)


def test_stub_sincrono_es_determinista_entre_procesos() -> None:
    primera = _correr_stub()
    segunda = _correr_stub()
    assert primera == segunda
    assert json.loads(primera)["llm"]["peticiones"] > 0


def _correr_stub() -> str:
    resultado = subprocess.run(
        [
            sys.executable,
            "-m",
            "tribal",
            "run",
            "--headless",
            "--json",
            "--llm",
            "stub",
            "--llm-sincrono",
            "--ticks",
            "300",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return resultado.stdout
