"""Embeddings en CPU, índice de recuerdos y guardas de hilo."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import pytest

from tribal.llm.cliente import ClienteLLM, backend_stub
from tribal.llm.cola import ColaLLM, Peticion
from tribal.llm.embeddings import (
    EmbedderHashing,
    EmbedderOllama,
    IndiceRecuerdos,
    embedder_por_defecto,
)
from tribal.sim import crear

RAIZ = Path(__file__).resolve().parents[1]


class ColaGrabada(ColaLLM):
    """Cola síncrona que guarda las peticiones para inspeccionar su contexto."""

    def __init__(self, cliente: ClienteLLM) -> None:
        super().__init__(cliente, sincrona=True)
        self.peticiones: list[Peticion] = []

    def encolar(self, peticion: Peticion) -> bool:
        self.peticiones.append(peticion)
        return super().encolar(peticion)


#: Un token distintivo por recuerdo: la consulta es ese token.
RECUERDOS = {
    "fuego": "fuego fuego fuego frotar madera chispa hoguera",
    "agua": "agua agua agua rio beber sed",
    "caza": "caza caza caza lanza presa carne",
    "litica": "litica litica litica tallar piedra filo",
    "lenguaje": "lenguaje lenguaje lenguaje hablar palabra nombre",
    "roles": "roles roles roles ensenar cuidar anciano",
    "simbolico": "simbolico simbolico simbolico pintar ocre rito",
    "tradicion": "tradicion tradicion tradicion imitar copiar costumbre",
    "mito": "mito mito mito leyenda antepasado espiritu",
    "depredador": "depredador depredador depredador huir morder amenaza",
}


def _indice() -> IndiceRecuerdos:
    indice = IndiceRecuerdos(EmbedderHashing())
    for recuerdo_id, texto in RECUERDOS.items():
        indice.agregar(recuerdo_id, texto)
    return indice


def test_top_1_relevante_en_diez_consultas() -> None:
    indice = _indice()
    for recuerdo_id in RECUERDOS:
        top = indice.buscar(recuerdo_id, k=3)
        assert top[0].id == recuerdo_id
        assert top[0].score > top[-1].score


def test_hashing_es_determinista_entre_procesos() -> None:
    primera = _embeddings_en_subproceso("1")
    segunda = _embeddings_en_subproceso("2")
    assert primera == segunda

    datos = json.loads(primera)
    assert datos["top"] == "fuego"
    assert len(datos["vector"]) == 256


def test_orden_estable_con_empates() -> None:
    indice = IndiceRecuerdos(EmbedderHashing())
    indice.agregar("zeta", "fuego frotar madera")
    indice.agregar("alfa", "fuego frotar madera")

    top = indice.buscar("fuego", k=2)
    assert [recuerdo.id for recuerdo in top] == ["alfa", "zeta"]
    assert top[0].score == pytest.approx(top[1].score)


def test_orden_estable_no_depende_del_orden_de_insercion() -> None:
    indice = IndiceRecuerdos(EmbedderHashing())
    indice.agregar("alfa", "fuego frotar madera")
    indice.agregar("zeta", "fuego frotar madera")

    assert [recuerdo.id for recuerdo in indice.buscar("fuego")] == ["alfa", "zeta"]


def test_usa_gpu_siempre_false() -> None:
    assert EmbedderHashing().usa_gpu is False
    assert EmbedderOllama().usa_gpu is False
    assert embedder_por_defecto().usa_gpu is False


def test_render_no_usa_la_recuperacion() -> None:
    fuente = (RAIZ / "tribal" / "ui" / "render.py").read_text(encoding="utf-8")
    assert "tribal.llm" not in fuente
    assert "IndiceRecuerdos" not in fuente
    assert "embeddings" not in fuente
    assert "recuperar_memoria" not in fuente


def test_recuperar_desde_la_pila_de_render_lanza() -> None:
    indice = _indice()
    espacio = {"__name__": "tribal.ui.render", "indice": indice}
    exec("def consultar():\n    return indice.buscar('fuego')\n", espacio)

    consultar: Any = espacio["consultar"]
    with pytest.raises(RuntimeError, match="render"):
        consultar()


def test_recuperar_desde_el_hilo_del_llm_lanza() -> None:
    indice = _indice()
    visto: dict[str, str] = {}

    def consultar() -> None:
        try:
            indice.buscar("fuego")
        except RuntimeError as exc:
            visto["error"] = str(exc)

    hilo = threading.Thread(target=consultar, name="tribal-llm")
    hilo.start()
    hilo.join()

    assert "LLM" in visto["error"]


def test_ollama_sin_servicio_no_revienta() -> None:
    def caido(*_args: object, **_kwargs: object) -> tuple[int, bytes]:
        raise ConnectionRefusedError("connection refused")

    embedder = EmbedderOllama(transporte=caido)
    vector = embedder.emb("fuego")

    assert len(vector) == embedder.dim
    assert all(valor == 0.0 for valor in vector)
    assert embedder.ultimo_error is not None
    assert "transporte" in embedder.ultimo_error


def test_ollama_parsea_y_normaliza() -> None:
    def ok(
        metodo: str, url: str, cuerpo: dict[str, object] | None, _timeout: float
    ) -> tuple[int, bytes]:
        assert metodo == "POST"
        assert url.endswith("/api/embed")
        assert cuerpo is not None and cuerpo["input"] == "fuego"
        return 200, json.dumps({"embeddings": [[3.0, 4.0]]}).encode("utf-8")

    embedder = EmbedderOllama(transporte=ok)
    assert embedder.emb("fuego") == pytest.approx((0.6, 0.8))
    assert embedder.dim == 2
    assert embedder.ultimo_error is None


def test_resumen_sin_llm_declara_memoria_vacia() -> None:
    simulacion = crear(42, 10)
    for _ in range(5):
        simulacion.step()

    assert simulacion.resumen()["memoria"] == {"recuerdos": 0, "recuperaciones": 0}


def test_coseno_con_dimensiones_distintas_lanza() -> None:
    indice = IndiceRecuerdos(EmbedderHashing(dim=4))
    indice.agregar("fuego", "fuego frotar madera")
    indice.embedder = EmbedderHashing(dim=8)

    with pytest.raises(ValueError):
        indice.buscar("fuego")


def test_integracion_indexa_hitos_y_llena_el_contexto() -> None:
    cola = ColaGrabada(ClienteLLM(transporte=backend_stub()))
    simulacion = crear(42, 12, cola=cola)

    hitos: list[int] = []
    for _ in range(2):
        for _ in range(50):
            simulacion.step()
        hitos.append(simulacion.resumen()["memoria"]["recuerdos"])
    for _ in range(200):
        simulacion.step()

    memoria = simulacion.resumen()["memoria"]
    assert memoria["recuerdos"] > 0
    assert memoria["recuperaciones"] > 0
    assert hitos[0] > 0
    assert hitos[1] > hitos[0]
    assert memoria["recuerdos"] >= hitos[1]

    indice = simulacion.recuerdos
    assert indice is not None
    ids_indice = {recuerdo.id for recuerdo in indice.buscar("", k=len(indice))}
    assert any(str(recuerdo_id).startswith("tradicion_") for recuerdo_id in ids_indice)

    assert cola.peticiones
    for peticion in cola.peticiones:
        contexto = peticion.contexto
        assert not isinstance(contexto, str)
        items = contexto["memoria"]
        assert isinstance(items, list) and items
        scores: list[float] = []
        for item in items:
            assert set(item) == {"id", "texto", "score"}
            assert item["id"] in ids_indice
            assert isinstance(item["texto"], str) and item["texto"]
            scores.append(item["score"])
        assert scores == sorted(scores, reverse=True)


def _embeddings_en_subproceso(semilla_hash: str) -> str:
    codigo = (
        "import json\n"
        "from tribal.llm.embeddings import EmbedderHashing, IndiceRecuerdos\n"
        "e = EmbedderHashing()\n"
        "i = IndiceRecuerdos(e)\n"
        "i.agregar('fuego', 'fuego frotar madera chispa')\n"
        "i.agregar('agua', 'agua rio beber')\n"
        "i.agregar('caza', 'caza lanza presa')\n"
        "print(json.dumps({'vector': e.emb('fuego madera'), "
        "'top': i.buscar('madera fuego', k=1)[0].id}))\n"
    )
    entorno = {**os.environ, "PYTHONHASHSEED": semilla_hash}
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=RAIZ,
        env=entorno,
        capture_output=True,
        text=True,
        check=True,
    )
    return resultado.stdout.strip()
