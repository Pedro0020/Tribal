"""
Cola asíncrona de inferencia: el bucle encola y recoge, nunca espera.

Un único hilo daemon (`tribal-llm`) consume de una `queue.Queue` acotada, llama
al cliente —que ya no lanza— y deposita la respuesta en otra cola acotada. El
hilo del bucle solo hace `put_nowait`/`get_nowait`: el LLM **nunca** se llama
desde el hilo de render (arquitectura §3, stack §8).

El presupuesto son dos cosas a la vez: como mucho `max_en_vuelo` peticiones
aceptadas sin respuesta (si está lleno, `encolar` devuelve `False` y el
individuo sigue por instinto) y una sola inferencia a la vez, porque el hilo
es único. La ventana de validez la aplica `drenar(tick_actual)`: un resultado
que llega después de `tick + ventana` se descarta y cuenta como descartado.

El orden de aplicación no depende de la carrera: `drenar` devuelve las
respuestas ordenadas por `(tick, id)`.
"""

from __future__ import annotations

import contextlib
import queue
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from tribal.llm.cliente import ClienteLLM
from tribal.llm.decision import decidir_con_candidatas
from tribal.llm.esquema import Decision

#: Ticks que sigue siendo válida una decisión: 180 ticks ≈ 3 s a 60 fps (§3).
VENTANA_POR_DEFECTO = 180
#: Peticiones aceptadas sin respuesta antes de que `encolar` diga que no.
MAX_EN_VUELO_POR_DEFECTO = 4
#: Nombre del hilo, para poder comprobar en los tests que no queda ninguno vivo.
NOMBRE_HILO = "tribal-llm"


@dataclass(frozen=True, slots=True)
class Peticion:
    """Lo que viaja al hilo del LLM: datos planos, nunca objetos vivos del mundo."""

    id: int
    tick: int
    individuo_id: int
    contexto: Mapping[str, Any] | str
    candidatas: tuple[str, ...]
    valida_hasta: int


@dataclass(frozen=True, slots=True)
class Respuesta:
    """Lo que vuelve del hilo del LLM. `tick` es el de la petición de origen."""

    id: int
    individuo_id: int
    decision: Decision | None
    error: str | None
    tick: int
    corregida: bool = False


@dataclass(frozen=True, slots=True)
class PeticionNarracion:
    """Un hito para el cronista. No decide nada y no caduca: se narra lo que pasó."""

    entrada: int
    tick: int
    hito: str
    contexto: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class TextoNarrado:
    """La frase que devolvió el hilo para la entrada `entrada`."""

    entrada: int
    texto: str


class ColaLLM:
    """Hilo dedicado + dos colas acotadas. `sincrona` existe para los tests."""

    def __init__(
        self,
        cliente: ClienteLLM,
        max_en_vuelo: int = MAX_EN_VUELO_POR_DEFECTO,
        ventana: int = VENTANA_POR_DEFECTO,
        *,
        sincrona: bool = False,
    ) -> None:
        if max_en_vuelo < 1:
            raise ValueError(f"max_en_vuelo debe ser mayor que 0 (recibido {max_en_vuelo})")
        if ventana < 0:
            raise ValueError(f"ventana no puede ser negativa (recibido {ventana})")
        self.cliente = cliente
        self.max_en_vuelo = max_en_vuelo
        self.ventana = ventana
        self.sincrona = sincrona
        self._peticiones: queue.Queue[Peticion | PeticionNarracion | None] = queue.Queue(
            maxsize=max_en_vuelo
        )
        self._resultados: queue.Queue[Respuesta] = queue.Queue(maxsize=max_en_vuelo * 2)
        self._textos: queue.Queue[TextoNarrado] = queue.Queue(maxsize=max_en_vuelo * 2)
        self._cerrojo = threading.Lock()
        self._hilo: threading.Thread | None = None
        self._cerrada = False
        self._en_vuelo = 0
        self._enviadas = 0
        self._aplicadas = 0
        self._descartadas = 0
        self._fallos = 0
        self._corregidas = 0
        #: En modo síncrono no hay hilo: las respuestas esperan aquí.
        self._sincronas: list[Respuesta] = []
        self._textos_sincronos: list[TextoNarrado] = []

    def encolar(self, peticion: Peticion) -> bool:
        """Acepta la petición si hay hueco. Nunca bloquea; `False` si está lleno."""
        if self._cerrada:
            return False
        if self.sincrona:
            respuesta = self._resolver(peticion)
            self._sincronas.append(respuesta)
            with self._cerrojo:
                self._enviadas += 1
            return True

        self._arrancar()
        with self._cerrojo:
            if self._en_vuelo >= self.max_en_vuelo:
                return False
            self._en_vuelo += 1
            self._enviadas += 1
        try:
            self._peticiones.put_nowait(peticion)
        except queue.Full:  # el contador y la cola discrepan: no se acepta
            with self._cerrojo:
                self._en_vuelo -= 1
                self._enviadas -= 1
            return False
        return True

    def drenar(self, tick_actual: int | None = None) -> list[Respuesta]:
        """Recoge lo que haya, sin bloquear.

        Con `tick_actual`, lo que llegó fuera de su ventana se descarta, se
        cuenta y no se devuelve. Sin él se devuelve todo: es la lectura cruda.
        """
        if self.sincrona:
            pendientes = self._sincronas
            self._sincronas = []
        else:
            pendientes = []
            while True:
                try:
                    pendientes.append(self._resultados.get_nowait())
                except queue.Empty:
                    break

        respuestas: list[Respuesta] = []
        for respuesta in sorted(pendientes, key=lambda item: (item.tick, item.id)):
            with self._cerrojo:
                if tick_actual is not None and tick_actual > respuesta.tick + self.ventana:
                    self._descartadas += 1
                    continue
                if respuesta.decision is None:
                    self._fallos += 1
                elif respuesta.corregida:
                    # Solo cuentan las correcciones que no se descartan por tardías.
                    self._corregidas += 1
            respuestas.append(respuesta)
        return respuestas

    def narrar(self, peticion: PeticionNarracion) -> bool:
        """Encola una narración sin bloquear. `False` si no cabe o está cerrada.

        Comparte el presupuesto en vuelo con las decisiones: si no hay hueco, el
        hito se queda sin frase y no pasa nada, porque el diario ya lo tiene.
        """
        if self._cerrada:
            return False
        if self.sincrona:
            self._textos_sincronos.append(self._resolver_narracion(peticion))
            return True

        self._arrancar()
        with self._cerrojo:
            if self._en_vuelo >= self.max_en_vuelo:
                return False
            self._en_vuelo += 1
        try:
            self._peticiones.put_nowait(peticion)
        except queue.Full:  # el contador y la cola discrepan: no se acepta
            with self._cerrojo:
                self._en_vuelo -= 1
            return False
        return True

    def drenar_textos(self) -> list[TextoNarrado]:
        """Narraciones ya resueltas, sin bloquear; las vacías no se devuelven."""
        if self.sincrona:
            pendientes, self._textos_sincronos = self._textos_sincronos, []
        else:
            pendientes = []
            while True:
                try:
                    pendientes.append(self._textos.get_nowait())
                except queue.Empty:
                    break
        return [texto for texto in pendientes if texto.texto]

    def registrar_aplicada(self) -> None:
        """El bucle aplicó la decisión; solo la cola lleva la cuenta."""
        with self._cerrojo:
            self._aplicadas += 1

    @property
    def estadisticas(self) -> dict[str, int]:
        """Enviadas, aplicadas, descartadas, fallos y en vuelo (0 tras `cerrar`)."""
        with self._cerrojo:
            return {
                "enviadas": self._enviadas,
                "aplicadas": self._aplicadas,
                "descartadas": self._descartadas,
                "fallos": self._fallos,
                "corregidas": self._corregidas,
                "en_vuelo": self._en_vuelo,
            }

    def cerrar(self) -> bool:
        """Para el hilo y lo une. Idempotente. True si no queda hilo vivo.

        Deja de aceptar, vacía las peticiones que aún no habían empezado
        (cuentan como descartadas), pone el centinela al final y espera a que
        el worker salga. El peor caso es una inferencia por cada petición ya
        aceptada: `en_vuelo * (timeout + 1)`, no el de la cola entera. Si el
        transporte se pasa de ese plazo, el hilo es daemon: se devuelve `False`
        para que el llamante pueda avisar, pero `en_vuelo` queda a 0 porque esa
        petición ya no se va a aplicar.
        """
        with self._cerrojo:
            if self._cerrada:
                self._descartar_textos()
                return self._hilo is None or not self._hilo.is_alive()
            self._cerrada = True

        hilo = self._hilo
        if hilo is None:  # modo síncrono o cola nunca usada
            self._descartar_resultados()
            self._descartar_en_vuelo()
            self._descartar_textos()
            return True

        # Lo aceptado y no empezado no se va a inferir: se descarta sin gastar
        # una llamada al cliente. Así el cierre espera como mucho *una* cola de
        # inferencias, no toda la cola de peticiones.
        while True:
            try:
                self._peticiones.get_nowait()
            except queue.Empty:
                break
            with self._cerrojo:
                self._en_vuelo = max(0, self._en_vuelo - 1)
                self._descartadas += 1

        # No debería llenarse: la cola se vació justo antes.
        with contextlib.suppress(queue.Full):
            self._peticiones.put(None, timeout=self.cliente.timeout + 1.0)
        plazo = time.perf_counter() + self._en_vuelo * (self.cliente.timeout + 1.0) + 1.0
        while hilo.is_alive() and time.perf_counter() < plazo:
            hilo.join(timeout=0.05)

        self._descartar_resultados()
        self._descartar_en_vuelo()
        self._descartar_textos()
        return not hilo.is_alive()

    def _descartar_resultados(self) -> None:
        """Vacía la cola de resultados: un error es fallo, una decisión descarte."""
        while True:
            try:
                respuesta = self._resultados.get_nowait()
            except queue.Empty:
                break
            with self._cerrojo:
                if respuesta.decision is None:
                    self._fallos += 1
                else:
                    self._descartadas += 1
        # En modo síncrono las respuestas esperan en una lista, no en la cola.
        pendientes, self._sincronas = self._sincronas, []
        with self._cerrojo:
            for respuesta in pendientes:
                if respuesta.decision is None:
                    self._fallos += 1
                else:
                    self._descartadas += 1

    def _descartar_en_vuelo(self) -> None:
        """Lo aceptado que no llegó a respuesta también es un descarte."""
        with self._cerrojo:
            self._descartadas += self._en_vuelo
            self._en_vuelo = 0

    def _arrancar(self) -> None:
        """Arranca el hilo en la primera petición: sin peticiones, sin hilo."""
        with self._cerrojo:
            if self._hilo is not None:
                return
            self._hilo = threading.Thread(target=self._bucle, name=NOMBRE_HILO, daemon=True)
            self._hilo.start()

    def _bucle(self) -> None:
        while True:
            trabajo = self._peticiones.get()
            if trabajo is None:
                return
            if isinstance(trabajo, PeticionNarracion):
                try:
                    texto = self._resolver_narracion(trabajo)
                except Exception:  # el worker no puede morir: dejaría cola sin consumidor
                    texto = TextoNarrado(trabajo.entrada, "")
                self._guardar_texto(texto)
                with self._cerrojo:
                    # `cerrar` puede haber puesto el contador a 0 mientras tanto.
                    self._en_vuelo = max(0, self._en_vuelo - 1)
                continue
            peticion = trabajo
            try:
                respuesta = self._resolver(peticion)
            except Exception as exc:  # el worker no puede morir: dejaría cola sin consumidor
                respuesta = Respuesta(
                    id=peticion.id,
                    individuo_id=peticion.individuo_id,
                    decision=None,
                    error=f"excepción: {exc}",
                    tick=peticion.tick,
                )
            try:
                self._resultados.put_nowait(respuesta)
            except queue.Full:  # no debería: `drenar` corre cada tick
                with self._cerrojo:
                    self._fallos += 1
            with self._cerrojo:
                # `cerrar` puede haber puesto el contador a 0 mientras esta
                # inferencia seguía viva: nunca se baja de cero.
                self._en_vuelo = max(0, self._en_vuelo - 1)

    def _resolver(self, peticion: Peticion) -> Respuesta:
        eleccion = decidir_con_candidatas(self.cliente, peticion.contexto, peticion.candidatas)
        return Respuesta(
            id=peticion.id,
            individuo_id=peticion.individuo_id,
            decision=eleccion.decision,
            error=None if eleccion.decision is not None else (eleccion.motivo or "sin decision"),
            tick=peticion.tick,
            corregida=eleccion.corregida,
        )

    def _resolver_narracion(self, peticion: PeticionNarracion) -> TextoNarrado:
        resultado = self.cliente.narrar(peticion.hito, peticion.contexto)
        return TextoNarrado(peticion.entrada, resultado.texto)

    def _guardar_texto(self, texto: TextoNarrado) -> None:
        """Deposita la frase; si no cabe, el diario conserva el hito sin narrar."""
        with contextlib.suppress(queue.Full):
            self._textos.put_nowait(texto)

    def _descartar_textos(self) -> None:
        """Vacía lo narrado y no leído: al cerrar nadie va a aplicarlo."""
        while True:
            try:
                self._textos.get_nowait()
            except queue.Empty:
                break
        self._textos_sincronos = []
