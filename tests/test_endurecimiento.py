"""Endurecimiento tras Fase 2: semilla, telemetría LLM, selfcheck y esquema.

Misma semilla + backend falso + modo síncrono → mismo resumen en cualquier
proceso. La cola se cierra sin dejar hilo `tribal-llm` ni peticiones en vuelo,
y `report telemetry` publica los contadores del LLM por muestra.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, cast

import pytest

from tribal.cli import main
from tribal.llm.cliente import ClienteLLM, backend_stub
from tribal.llm.cola import NOMBRE_HILO, ColaLLM, Peticion
from tribal.llm.esquema import ErrorValidacion, validar
from tribal.sim import crear, run_muestreado

RAIZ = Path(__file__).resolve().parents[1]
SEMILLAS = tuple(range(1, 11))
TICKS = 300


def _correr(seed: int) -> str:
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
            str(TICKS),
            "--seed",
            str(seed),
        ],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    )
    return resultado.stdout


@pytest.mark.parametrize("seed", SEMILLAS)
def test_stub_sincrono_reproduce_el_resumen_entre_procesos(seed: int) -> None:
    primera = _correr(seed)
    segunda = _correr(seed)

    assert primera == segunda
    resumen = json.loads(primera)
    assert resumen["seed"] == seed
    assert resumen["llm"]["peticiones"] > 0
    assert resumen["llm"]["en_vuelo"] == 0


def test_cola_asincrona_se_cierra_sin_hilo_ni_peticiones_en_vuelo() -> None:
    cola = ColaLLM(ClienteLLM(transporte=backend_stub()))
    simulacion = crear(7, 12, cola=cola)
    try:
        for _ in range(TICKS):
            simulacion.step()
    finally:
        cerrada = cola.cerrar()

    assert cerrada is True
    assert cola.estadisticas["enviadas"] > 0  # el hilo llegó a arrancar
    assert cola.estadisticas["en_vuelo"] == 0
    assert all(hilo.name != NOMBRE_HILO for hilo in threading.enumerate())


def _lento(segundos: float) -> Any:
    """Transporte que duerme `segundos` y devuelve una decisión válida."""

    def transporte(
        _metodo: str,
        _url: str,
        _cuerpo: dict[str, object] | None,
        _timeout: float,
    ) -> tuple[int, bytes]:
        time.sleep(segundos)
        contenido = {"accion": "beber", "objetivo": "", "razon": "test", "dialogo": ""}
        sobre = {"message": {"role": "assistant", "content": json.dumps(contenido)}}
        return 200, json.dumps(sobre).encode()

    return transporte


def test_latencia_media_mide_el_tiempo_del_transporte() -> None:
    """Un transporte de 40 ms no puede publicar 0 ms: la media es real."""
    cola = ColaLLM(ClienteLLM(transporte=_lento(0.04)), sincrona=True)
    peticion = Peticion(
        id=1,
        tick=0,
        individuo_id=1,
        contexto={},
        candidatas=("beber", "comer"),
        valida_hasta=180,
    )
    assert cola.encolar(peticion) is True

    respuestas = cola.drenar(tick_actual=0)
    cola.cerrar()

    assert len(respuestas) == 1
    assert respuestas[0].decision is not None
    assert cola.latencia_ms_media >= 20.0


def test_run_muestreado_cierra_la_cola_asincrona() -> None:
    """La telemetría con cola real vuelve sin hilo `tribal-llm` ni en vuelo."""
    cola = ColaLLM(ClienteLLM(transporte=backend_stub()))
    _, muestras = run_muestreado(TICKS, 3, 100, cola=cola)

    assert len(muestras) == 3
    assert cola.estadisticas["en_vuelo"] == 0
    assert all(hilo.name != NOMBRE_HILO for hilo in threading.enumerate())


def _informe(capsys: pytest.CaptureFixture[str], *extra: str) -> dict[str, Any]:
    assert main(["report", "telemetry", "--json", *extra]) == 0
    return cast(dict[str, Any], json.loads(capsys.readouterr().out))


def test_telemetria_con_llm_publica_los_contadores_por_muestra(
    capsys: pytest.CaptureFixture[str],
) -> None:
    informe = _informe(
        capsys,
        "--seed",
        "3",
        "--ticks",
        "300",
        "--intervalo",
        "100",
        "--llm",
        "stub",
        "--llm-sincrono",
    )

    assert informe["llm"] == "stub"
    assert len(informe["muestras"]) == 3
    for muestra in informe["muestras"]:
        assert set(muestra["llm"]) == {
            "peticiones",
            "aplicadas",
            "descartadas",
            "fallos",
            "latencia_ms_media",
        }
        assert muestra["llm"]["peticiones"] >= 0
        assert isinstance(muestra["llm"]["latencia_ms_media"], float)
    assert informe["muestras"][-1]["llm"]["peticiones"] > 0


def test_telemetria_sin_llm_no_cambia_las_muestras(
    capsys: pytest.CaptureFixture[str],
) -> None:
    informe = _informe(capsys, "--ticks", "120", "--intervalo", "60")

    assert informe["llm"] == "off"
    assert all("llm" not in muestra for muestra in informe["muestras"])


def test_telemetria_rechaza_sincrono_con_http(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(
            [
                "report",
                "telemetry",
                "--json",
                "--llm",
                "http",
                "--llm-sincrono",
                "--ticks",
                "10",
            ]
        )
        == 2
    )
    assert "--llm-sincrono" in capsys.readouterr().err


class _Tags:
    """Respuesta mínima de `/api/tags` para el transporte real sin socket."""

    status = 200

    def __init__(self, modelos: tuple[str, ...]) -> None:
        self._cuerpo = json.dumps({"models": [{"name": nombre} for nombre in modelos]}).encode()

    def __enter__(self) -> _Tags:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._cuerpo


def _urlopen_con(modelos: tuple[str, ...]) -> Any:
    def urlopen(*_args: Any, **_kwargs: Any) -> _Tags:
        return _Tags(modelos)

    return urlopen


def _urlopen_caido(*_args: Any, **_kwargs: Any) -> Any:
    raise urllib.error.URLError("connection refused")


class _TagsCrudo:
    """`/api/tags` con un cuerpo arbitrario: cubre los cuerpos rotos."""

    status = 200

    def __init__(self, cuerpo: bytes) -> None:
        self._cuerpo = cuerpo

    def __enter__(self) -> _TagsCrudo:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._cuerpo


@pytest.mark.parametrize(
    "cuerpo",
    [
        b"{no es json",
        b'{"models": []}',
        b'{"models": "tribal-llm"}',
        b"{}",
    ],
)
def test_selfcheck_sobrevive_a_un_cuerpo_de_tags_roto(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    cuerpo: bytes,
) -> None:
    """Un `/api/tags` raro no rompe selfcheck: modelo_presente queda en False."""
    monkeypatch.setattr(urllib.request, "urlopen", lambda *_a, **_k: _TagsCrudo(cuerpo))

    assert main(["llm", "selfcheck", "--json"]) == 0
    informe = json.loads(capsys.readouterr().out)
    assert informe["disponible"] is True
    assert informe["modelo_presente"] is False


@pytest.mark.parametrize(
    ("modelos", "presente"),
    [
        (("tribal-llm:latest",), True),
        (("qwen2.5:3b-instruct-q8_0", "otro:1b"), False),
        ((), False),
    ],
)
def test_selfcheck_reporta_si_el_modelo_esta_en_tags(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    modelos: tuple[str, ...],
    presente: bool,
) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_con(modelos))

    assert main(["llm", "selfcheck", "--json"]) == 0
    informe = json.loads(capsys.readouterr().out)
    assert informe["disponible"] is True
    assert informe["modelo_presente"] is presente


def test_selfcheck_sin_servicio_no_rompe_y_no_afirma_el_modelo(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_caido)

    assert main(["llm", "selfcheck", "--json"]) == 0
    informe = json.loads(capsys.readouterr().out)
    assert informe["disponible"] is False
    assert informe["modelo_presente"] is None


def test_validar_rechaza_campos_extra_que_el_esquema_prohibe() -> None:
    datos = {
        "accion": "beber",
        "objetivo": "la orilla",
        "razon": "la sed aprieta",
        "dialogo": "",
        "inventado": "no está en el esquema",
    }
    error = validar(datos)
    assert isinstance(error, ErrorValidacion)
    assert "inventado" in error.motivo
