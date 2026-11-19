"""Saliencia y pensamiento selectivo (concepto §10b).

La saliencia es peso narrativo **ganado**: sube por hitos del motor, decae por
tick y no tiene nada que ver con el temperamento (`divergencia`, §9b). Decide
quién piensa cuando el presupuesto de LLM no llega a todos los dilemas.
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
import time
from typing import Any

import pytest

from tribal.agents import saliencia
from tribal.cli import main
from tribal.config import SimConfig
from tribal.core.acciones import Accion
from tribal.core.genoma import Genoma
from tribal.core.habilidades import Habilidades
from tribal.core.modelos import Individuo, Mundo, Necesidades, TipoTile
from tribal.llm.cliente import ClienteLLM, Transporte, backend_stub
from tribal.llm.cola import ColaLLM
from tribal.sim import Simulacion


def _mundo(*individuos: Individuo) -> Mundo:
    """Seis por seis de hierba, sin recursos: el dilema no se resuelve solo."""
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
    divergencia: float = 0.5,
    energia: float = 100.0,
    sed: float = 0.0,
    salud: float = 100.0,
) -> Individuo:
    return Individuo(
        id=id_,
        sexo="m",
        genoma=Genoma(divergencia=divergencia),
        necesidades=Necesidades(energia=energia, sed=sed, salud=salud),
        x=1.0,
        y=1.0,
    )


def _dilematico(id_: int) -> Individuo:
    """Sed y energía en conflicto, salud crítica: hay decisión que pedir."""
    return _individuo(id_, energia=40.0, sed=70.0, salud=10.0)


def _sincrona() -> ColaLLM:
    return ColaLLM(ClienteLLM(transporte=backend_stub()), sincrona=True)


def _lento(segundos: float) -> Transporte:
    """Transporte que tarda: mantiene peticiones en vuelo de verdad."""

    def transporte(
        _metodo: str,
        _url: str,
        _cuerpo: dict[str, Any] | None,
        _timeout: float,
    ) -> tuple[int, bytes]:
        time.sleep(segundos)
        sobre = {
            "message": {
                "role": "assistant",
                "content": json.dumps({"accion": "descansar", "razon": "test"}),
            }
        }
        return 200, json.dumps(sobre).encode()

    return transporte


def test_los_hitos_suben_y_el_tiempo_baja_la_saliencia() -> None:
    individuo = _individuo(1)
    for motivo, peso in saliencia.SUBIDA.items():
        antes = individuo.saliencia
        saliencia.subir(individuo, motivo)
        assert individuo.saliencia == pytest.approx(antes + peso)

    for _ in range(100):
        saliencia.subir(individuo, "combinacion")
    assert individuo.saliencia == pytest.approx(saliencia.SALIENCIA_MAX)

    for _ in range(500):
        saliencia.decaer(individuo)
    esperado = saliencia.SALIENCIA_MAX * saliencia.DECAIMIENTO**500
    assert individuo.saliencia == pytest.approx(esperado)
    assert individuo.saliencia < saliencia.SALIENCIA_MAX

    with pytest.raises(ValueError):
        saliencia.subir(individuo, "motivo_inventado")


def test_el_primero_en_una_rama_del_arbol_gana_saliencia() -> None:
    autor = _individuo(1)
    testigo = _individuo(2)
    simulacion = Simulacion(_mundo(autor, testigo), SimConfig(seed=0, individuos=2))

    assert simulacion._practicar(autor, "frotar_madera", descubrir=True) is True
    assert simulacion.grafo.activo("observar_rayo")  # primera chispa de la rama
    assert autor.saliencia == pytest.approx(saliencia.SUBIDA["primer_nodo"])
    assert testigo.saliencia == 0.0


def test_descubrir_una_combinacion_sube_la_saliencia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    individuo = _individuo(1, divergencia=0.9, energia=80.0, sed=0.0)
    simulacion = Simulacion(_mundo(individuo), SimConfig(seed=0, individuos=1, crisis=True))
    for nodo_id in ("guijarro", "lasca", "bifaz"):
        simulacion.grafo.descubrir(nodo_id, autor=1, tick=1)
    monkeypatch.setattr("tribal.sim.PROB_INTENTO_DIVERGENTE", 100.0)
    monkeypatch.setattr("tribal.sim.PROB_COMPLETAR_COMBINACION", 1.0)

    assert simulacion._intentar_combinacion(individuo) is True
    assert individuo.saliencia == pytest.approx(saliencia.SUBIDA["combinacion"])


def test_la_primera_tradicion_sube_la_saliencia_de_su_autor() -> None:
    autor = _individuo(1)
    simulacion = Simulacion(_mundo(autor), SimConfig(seed=0, individuos=1, depredadores=0))
    simulacion.grafo.descubrir("guijarro", autor=1, tick=0)
    simulacion.grafo.imitadores["guijarro"] = {2, 3, 4}
    simulacion.grafo.ultimo_imitador["guijarro"] = autor.id

    simulacion.step()

    assert simulacion.tradiciones == 1
    assert autor.saliencia == pytest.approx(saliencia.SUBIDA["tradicion"])


def test_ensenar_una_habilidad_sube_la_saliencia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    maestro = _individuo(1)
    maestro.edad = 400  # adulto: la enseñanza exige madurez
    maestro.habilidades = Habilidades({"recolectar", "fabricar"})
    aprendiz = _individuo(2)
    aprendiz.habilidades = Habilidades({"recolectar"})

    def elegir(individuo: Individuo, _mundo: Mundo) -> Accion:
        return Accion("ensenar", objetivo=aprendiz.id) if individuo.id == 1 else Accion("descansar")

    monkeypatch.setattr("tribal.sim.instinto.elegir", elegir)
    monkeypatch.setattr("tribal.core.acciones.PROB_ENSENANZA", 100.0)
    simulacion = Simulacion(
        _mundo(maestro, aprendiz), SimConfig(seed=0, individuos=2, depredadores=0)
    )

    simulacion.step()

    assert aprendiz.habilidades.sabe("fabricar")
    assert maestro.saliencia >= saliencia.SUBIDA["ensenanza"]
    assert aprendiz.saliencia == 0.0


def test_cuidar_a_un_herido_sube_la_saliencia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cuidador = _individuo(1)
    herido = _individuo(2, salud=10.0)

    def elegir(individuo: Individuo, _mundo: Mundo) -> Accion:
        return Accion("cuidar", objetivo=herido.id) if individuo.id == 1 else Accion("descansar")

    monkeypatch.setattr("tribal.sim.instinto.elegir", elegir)
    simulacion = Simulacion(
        _mundo(cuidador, herido), SimConfig(seed=0, individuos=2, depredadores=0)
    )

    simulacion.step()

    assert cuidador.saliencia >= saliencia.SUBIDA["rescate"]
    assert herido.saliencia == 0.0


def test_la_saliencia_no_depende_de_la_divergencia() -> None:
    divergente = _individuo(1, divergencia=0.95)
    conformista = _individuo(2, divergencia=0.05)
    assert divergente.saliencia == conformista.saliencia == 0.0

    for individuo in (divergente, conformista):
        simulacion = Simulacion(_mundo(individuo), SimConfig(seed=0, individuos=1))
        assert simulacion._practicar(individuo, "frotar_madera", descubrir=True) is True

    assert divergente.saliencia == conformista.saliencia > 0.0


def test_la_saliencia_manda_frente_al_orden_de_la_lista() -> None:
    """El saliente tiene id mayor: sin el sort, pensaría el primero de la lista."""
    seguidores = [_dilematico(1), _dilematico(2)]
    lider = _dilematico(3)
    for _ in range(10):
        saliencia.subir(lider, "combinacion")
    simulacion = Simulacion(
        _mundo(*seguidores, lider),
        SimConfig(seed=0, individuos=3, depredadores=0, max_pensando=1),
        cola=_sincrona(),
    )

    for _ in range(40):
        simulacion.step()

    pensamientos = simulacion.resumen()["saliencia"]["pensamientos"]
    assert pensamientos[lider.id] == 40
    assert pensamientos.get(1, 0) == 0
    assert pensamientos.get(2, 0) == 0


def test_el_motor_decae_la_saliencia_cada_tick() -> None:
    """Sin hitos, N ticks de `step()` dejan `base * DECAIMIENTO**N`."""
    individuo = _individuo(1)
    simulacion = Simulacion(_mundo(individuo), SimConfig(seed=0, individuos=1, depredadores=0))
    base = 5.0
    individuo.saliencia = base
    ticks = 200

    for _ in range(ticks):
        simulacion.step()

    assert individuo.saliencia == pytest.approx(base * saliencia.DECAIMIENTO**ticks)


def test_el_hito_de_crisis_llega_a_los_600_ticks_y_se_reinicia_al_salir() -> None:
    individuo = _individuo(1)
    simulacion = Simulacion(_mundo(individuo), SimConfig(seed=0, individuos=1, depredadores=0))

    for _ in range(saliencia.TICKS_CRISIS - 1):
        simulacion._hito_crisis(True)
    assert individuo.saliencia == 0.0

    simulacion._hito_crisis(True)
    assert individuo.saliencia == pytest.approx(saliencia.SUBIDA["crisis"])

    # Salir de la crisis reinicia el contador: otros 599 seguidos no bastan.
    for _ in range(saliencia.TICKS_CRISIS // 2):
        simulacion._hito_crisis(True)
    simulacion._hito_crisis(False)
    for _ in range(saliencia.TICKS_CRISIS - 1):
        simulacion._hito_crisis(True)
    assert individuo.saliencia == pytest.approx(saliencia.SUBIDA["crisis"])

    simulacion._hito_crisis(True)
    assert individuo.saliencia == pytest.approx(2 * saliencia.SUBIDA["crisis"])


def test_step_aplica_el_hito_de_crisis() -> None:
    """La llamada del tick existe: 599 pasos no pagan y el 600 sí."""
    individuo = _individuo(1)
    simulacion = Simulacion(
        _mundo(individuo),
        SimConfig(seed=0, individuos=1, depredadores=0, crisis=True),
    )

    for _ in range(saliencia.TICKS_CRISIS - 1):
        simulacion.step()
    assert individuo.saliencia == 0.0

    simulacion.step()
    assert individuo.saliencia == pytest.approx(saliencia.SUBIDA["crisis"])


def test_con_mas_hitos_piensa_mas_en_la_misma_corrida() -> None:
    lider = _dilematico(1)
    for _ in range(10):
        saliencia.subir(lider, "combinacion")
    seguidores = [_dilematico(2), _dilematico(3)]
    simulacion = Simulacion(
        _mundo(lider, *seguidores),
        SimConfig(seed=0, individuos=3, depredadores=0, max_pensando=1),
        cola=_sincrona(),
    )

    for _ in range(60):
        simulacion.step()

    pensamientos = simulacion.resumen()["saliencia"]["pensamientos"]
    assert pensamientos[lider.id] == 60
    assert all(pensamientos.get(seguidor.id, 0) == 0 for seguidor in seguidores)
    assert simulacion.resumen()["saliencia"]["top"][0][0] == lider.id
    assert simulacion._max_pensando_visto == 1


def test_nunca_piensan_mas_de_max_pensando_a_la_vez() -> None:
    individuos = [_dilematico(1), _dilematico(2), _dilematico(3)]
    simulacion = Simulacion(
        _mundo(*individuos),
        SimConfig(seed=0, individuos=3, depredadores=0, max_pensando=2),
        cola=_sincrona(),
    )

    for _ in range(40):
        simulacion.step()

    assert simulacion._max_pensando_visto == 2
    assert simulacion.resumen()["saliencia"]["max_pensando"] == 2
    # Cada petición aceptada cuenta una vez y como mucho para un individuo.
    assert sum(simulacion._pensamientos.values()) == 40 * 2


def test_nunca_hay_mas_de_max_en_vuelo_peticiones_a_la_vez() -> None:
    cola = ColaLLM(ClienteLLM(transporte=_lento(0.01)), max_en_vuelo=2)
    simulacion = Simulacion(
        _mundo(_dilematico(1), _dilematico(2), _dilematico(3)),
        SimConfig(seed=0, individuos=3, depredadores=0, max_pensando=4),
        cola=cola,
    )

    visto = 0
    try:
        for _ in range(30):
            simulacion.step()
            visto = max(visto, cola.estadisticas["en_vuelo"])
        assert 1 <= visto <= 2
        assert simulacion._max_en_vuelo_visto <= 2
        assert simulacion._max_pensando_visto <= 4
    finally:
        cola.cerrar()


def test_cli_stub_publica_top_de_saliencia_y_pensamientos(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["run", "--headless", "--json", "--llm", "stub", "--ticks", "1200"]) == 0
    datos = json.loads(capsys.readouterr().out)

    bloque = datos["saliencia"]
    assert set(bloque) == {"top", "pensamientos", "max_pensando", "max_en_vuelo"}
    assert bloque["pensamientos"]
    assert bloque["top"]
    assert len(bloque["top"]) <= 3
    valores = [valor for _, valor in bloque["top"]]
    assert valores == sorted(valores, reverse=True)
    assert sum(bloque["pensamientos"].values()) == datos["llm"]["peticiones"]
    assert bloque["max_pensando"] <= datos["config"]["max_pensando"]
    assert bloque["max_en_vuelo"] <= 4


def test_stub_sincrono_es_determinista_y_publica_saliencia() -> None:
    primera = _correr_stub()
    segunda = _correr_stub()

    assert primera == segunda
    datos = json.loads(primera)
    assert datos["saliencia"]["max_pensando"] <= datos["config"]["max_pensando"]
    assert sum(datos["saliencia"]["pensamientos"].values()) == datos["llm"]["peticiones"]


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
