"""
Cliente HTTP de Ollama para la capa LLM.

Habla con `127.0.0.1:11434/api/chat` usando `model: tribal-llm`, el esquema
JSON de `esquema.py` en el campo `format`, temperatura baja y timeout corto.
El transporte se inyecta para que los tests no abran red: `backend_falso`
devuelve respuestas en cola de forma determinista.

Ningún fallo sube al bucle: una conexión rechazada o un timeout se convierten
en `degradado` y un JSON inválido en `error`. El motor sigue por instinto.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from tribal.llm.esquema import (
    EJEMPLOS,
    ESQUEMA_RESPUESTA,
    Decision,
    ErrorValidacion,
    construir_prompt,
    validar,
)

ENDPOINT_POR_DEFECTO = "http://127.0.0.1:11434"
MODELO_POR_DEFECTO = "tribal-llm"
#: Timeout corto: si no llega, el individuo sigue por instinto (stack §8).
TIMEOUT_POR_DEFECTO = 3.0
TEMPERATURA = 0.3
#: Tokens por decisión, sobre JSON incluido. Una elección + razón + diálogo.
MAX_TOKENS = 64

#: (método, url, cuerpo, timeout) -> (estado HTTP, cuerpo bruto).
Transporte = Callable[[str, str, dict[str, Any] | None, float], tuple[int, bytes]]

Estado = Literal["ok", "degradado", "error"]


@dataclass(frozen=True, slots=True)
class Resultado:
    """Lo que devuelve `decidir`: una decisión o el motivo por el que no la hay."""

    estado: Estado
    decision: Decision | None = None
    motivo: str | None = None


@dataclass(frozen=True, slots=True)
class Servicio:
    """Estado del servicio para `llm selfcheck`."""

    disponible: bool
    latencia_ms: float | None = None
    error: str | None = None


class ClienteLLM:
    """Cliente síncrono de Ollama con transporte inyectable."""

    def __init__(
        self,
        endpoint: str = ENDPOINT_POR_DEFECTO,
        modelo: str = MODELO_POR_DEFECTO,
        timeout: float = TIMEOUT_POR_DEFECTO,
        *,
        transporte: Transporte | None = None,
        ejemplos: Sequence[Mapping[str, Any]] | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.modelo = modelo
        self.timeout = timeout
        self._transporte = transporte or _transporte_http
        self._ejemplos: Sequence[Mapping[str, Any]] = (
            EJEMPLOS if ejemplos is None else tuple(ejemplos)
        )

    def disponible(self) -> Servicio:
        """GET `/api/tags`: ¿está Ollama levantado? Nunca lanza."""
        inicio = time.perf_counter()
        try:
            estado, _ = self._transporte("GET", f"{self.endpoint}/api/tags", None, self.timeout)
        except Exception as exc:  # servicio caído, DNS, timeout: no es excepción del bucle
            return Servicio(False, error=f"servicio caído: {exc}")
        latencia = round((time.perf_counter() - inicio) * 1000, 1)
        if estado != 200:
            return Servicio(False, latencia, f"http {estado}")
        return Servicio(True, latencia)

    def decidir(
        self,
        contexto: Mapping[str, Any] | str,
        candidatas: Sequence[str],
    ) -> Resultado:
        """Pide una elección entre `candidatas`; nunca lanza."""
        candidatas = tuple(candidatas)
        if not candidatas:
            return Resultado("error", motivo="sin acciones candidatas")

        cuerpo: dict[str, Any] = {
            "model": self.modelo,
            "messages": construir_prompt(contexto, candidatas, self._ejemplos),
            "format": ESQUEMA_RESPUESTA,
            "stream": False,
            "options": {"temperature": TEMPERATURA, "num_predict": MAX_TOKENS},
        }
        try:
            estado, bruto = self._transporte(
                "POST", f"{self.endpoint}/api/chat", cuerpo, self.timeout
            )
        except Exception as exc:  # conexión rechazada, timeout, transporte roto
            return Resultado("degradado", motivo=f"transporte: {exc}")

        if estado != 200:
            return Resultado("degradado", motivo=f"http {estado}")

        valido = _contenido(bruto)
        if isinstance(valido, ErrorValidacion):
            return Resultado("error", motivo=valido.motivo)
        if valido.accion not in candidatas:
            return Resultado("error", motivo=f"accion fuera de candidatas: {valido.accion}")
        return Resultado("ok", decision=valido)


def backend_falso(respuestas: Iterable[Any]) -> Transporte:
    """Transporte determinista para tests: consume `respuestas` en orden.

    Cada elemento puede ser un cuerpo JSON (dict/list/str), una tupla
    `(estado, cuerpo)` o una excepción que el cliente debe degradar.
    """
    cola = list(respuestas)

    def transporte(
        _metodo: str,
        _url: str,
        _cuerpo: dict[str, Any] | None,
        _timeout: float,
    ) -> tuple[int, bytes]:
        if not cola:
            raise AssertionError("backend_falso: no quedan respuestas")
        respuesta = cola.pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        if isinstance(respuesta, tuple) and len(respuesta) == 2:
            estado, bruto = respuesta
            return int(estado), _bytes(bruto)
        return 200, _bytes(respuesta)

    return transporte


def _transporte_http(
    metodo: str,
    url: str,
    cuerpo: dict[str, Any] | None,
    timeout: float,
) -> tuple[int, bytes]:
    """Transporte real con la stdlib: sin dependencias nuevas."""
    datos = None if cuerpo is None else json.dumps(cuerpo).encode("utf-8")
    peticion = urllib.request.Request(url, data=datos, method=metodo)
    peticion.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
            return int(respuesta.status), respuesta.read()
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read()


def _bytes(respuesta: Any) -> bytes:
    if isinstance(respuesta, bytes):
        return respuesta
    if isinstance(respuesta, str):
        return respuesta.encode("utf-8")
    return json.dumps(respuesta).encode("utf-8")


def _contenido(bruto: bytes) -> Decision | ErrorValidacion:
    """Desenvuelve el sobre de `/api/chat` y valida el JSON del mensaje."""
    try:
        sobre = json.loads(bruto)
    except (TypeError, ValueError):
        return ErrorValidacion("la respuesta HTTP no es JSON")
    if not isinstance(sobre, Mapping):
        return ErrorValidacion("la respuesta HTTP no es un objeto")
    mensaje = sobre.get("message")
    if not isinstance(mensaje, Mapping):
        return ErrorValidacion("la respuesta no trae 'message'")
    contenido = mensaje.get("content")
    if not isinstance(contenido, str):
        return ErrorValidacion("el mensaje no trae 'content'")
    try:
        datos = json.loads(contenido)
    except ValueError:
        return ErrorValidacion("el contenido no es JSON")
    return validar(datos)
