"""Memoria: contenido en el contexto, escritura de lo narrado y filtro por individuo."""

from __future__ import annotations

import json

from tribal.llm.cliente import ClienteLLM, backend_falso, backend_stub
from tribal.llm.cola import ColaLLM, Peticion
from tribal.llm.embeddings import EmbedderHashing, IndiceRecuerdos
from tribal.llm.http import Transporte
from tribal.sim import crear


class ColaGrabada(ColaLLM):
    """Cola síncrona que guarda las peticiones para inspeccionar su contexto."""

    def __init__(self, cliente: ClienteLLM) -> None:
        super().__init__(cliente, sincrona=True)
        self.peticiones: list[Peticion] = []

    def encolar(self, peticion: Peticion) -> bool:
        self.peticiones.append(peticion)
        return super().encolar(peticion)


def _backend_dialogo(dialogo: str) -> Transporte:
    contenido = {"accion": "hablar", "objetivo": "", "razon": "stub", "dialogo": dialogo}
    return backend_falso([{"message": {"role": "assistant", "content": json.dumps(contenido)}}])


def test_recuperar_no_cruza_individuos() -> None:
    """A tiene un recuerdo distintivo; B no lo ve, A sí, y lo tribal es de todos."""
    indice = IndiceRecuerdos(EmbedderHashing())
    indice.agregar("propio", "fuego hoguera chispa", individuo_id=1)
    indice.agregar("ajeno", "fuego hoguera chispa", individuo_id=2)
    indice.agregar("tribal", "fuego de toda la tribu", individuo_id=None)

    ids_a = {recuerdo.id for recuerdo in indice.recuperar("fuego hoguera", 1, k=10)}
    ids_b = {recuerdo.id for recuerdo in indice.recuperar("fuego hoguera", 2, k=10)}

    assert ids_a == {"propio", "tribal"}
    assert ids_b == {"ajeno", "tribal"}
    assert "propio" not in ids_b


def test_el_contexto_lleva_el_texto_del_recuerdo() -> None:
    """La Peticion enviada trae el texto propio y no el de otro individuo."""
    cola = ColaGrabada(ClienteLLM(transporte=backend_stub()))
    simulacion = crear(42, 12, cola=cola)
    a, b = simulacion.mundo.individuos[0], simulacion.mundo.individuos[1]
    simulacion._registrar_recuerdo(
        "propio_a", "fuego propio de A chispa hoguera", individuo_id=a.id, tipo="narracion"
    )
    simulacion._registrar_recuerdo(
        "ajeno_b", "lobo gris ajeno de B aullido", individuo_id=b.id, tipo="narracion"
    )
    simulacion._registrar_recuerdo("tribu", "la tribu cruzo el rio", individuo_id=None)

    a.necesidades.salud = 10.0
    simulacion.mundo.tick = 5
    simulacion._encolar_dilema()

    propias = [peticion for peticion in cola.peticiones if peticion.individuo_id == a.id]
    assert propias
    contexto = propias[0].contexto
    assert not isinstance(contexto, str)
    memoria = contexto["memoria"]
    assert isinstance(memoria, list) and memoria
    textos = [item["texto"] for item in memoria]
    assert "fuego propio de A chispa hoguera" in textos
    assert all("lobo gris ajeno de B" not in texto for texto in textos)


def test_la_narracion_se_indexa_y_se_recupera_despues() -> None:
    """El texto del cronista entra en el índice y se recupera por similitud."""
    cola = ColaGrabada(ClienteLLM(transporte=backend_stub()))
    simulacion = crear(42, 12, cola=cola)
    for _ in range(600):
        simulacion.step()

    narradas = [entrada for entrada in simulacion.diario.entradas if entrada.narrada]
    assert narradas
    indice = simulacion.recuerdos
    assert indice is not None
    recuperables = {recuerdo.id for recuerdo in indice.buscar("", k=len(indice))}
    for entrada in narradas:
        posicion = simulacion.diario.entradas.index(entrada)
        assert f"narracion_{posicion}" in recuperables


def test_el_dialogo_se_indexa_y_se_recupera_despues() -> None:
    """Lo que dijo alguien es memoria de ese individuo en ticks posteriores."""
    cola = ColaGrabada(ClienteLLM(transporte=_backend_dialogo("la piedra del rio corta mejor")))
    simulacion = crear(42, 12, cola=cola)
    hablante, otro = simulacion.mundo.individuos[0], simulacion.mundo.individuos[1]
    simulacion.mundo.tick = 1
    assert cola.encolar(
        Peticion(
            id=1,
            tick=1,
            individuo_id=hablante.id,
            contexto={},
            candidatas=("hablar", "descansar"),
            valida_hasta=10,
        )
    )
    simulacion.mundo.tick = 40
    simulacion._drenar()

    indice = simulacion.recuerdos
    assert indice is not None
    propios = indice.recuperar("piedra rio corta", hablante.id, k=5)
    assert any(recuerdo.texto == "la piedra del rio corta mejor" for recuerdo in propios)
    assert all(recuerdo.individuo_id in (None, hablante.id) for recuerdo in propios)
    ajenos = indice.recuperar("piedra rio corta", otro.id, k=5)
    assert all("piedra del rio" not in recuerdo.texto for recuerdo in ajenos)


def test_el_indice_es_determinista_entre_corridas() -> None:
    def fotografia() -> list[tuple[object, ...]]:
        cola = ColaGrabada(ClienteLLM(transporte=backend_stub()))
        simulacion = crear(42, 12, cola=cola)
        for _ in range(300):
            simulacion.step()
        indice = simulacion.recuerdos
        assert indice is not None
        return [
            (recuerdo.id, recuerdo.texto, recuerdo.individuo_id, recuerdo.tick, recuerdo.tipo)
            for recuerdo in indice.buscar("", k=len(indice))
        ]

    assert fotografia() == fotografia()
