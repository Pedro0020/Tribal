"""
Embeddings y recuperación de recuerdos, en CPU.

Dos backends detrás de la misma interfaz (`Embedder`):

- `EmbedderHashing`: bag-of-words con hash estable (blake2b del token) y L2
  normalizado. Es el que usan los tests y el default: misma entrada → mismo
  vector en cualquier proceso, porque no toca `hash()`, que cambia con la
  semilla de Python.
- `EmbedderOllama`: `POST /api/embed` contra Ollama con un modelo de embedding
  pequeño. Sin dependencias (urllib), con transporte inyectable para que la
  suite no abra red. `usa_gpu=False` es una declaración de intención: Ollama
  decide el dispositivo, y aquí se pide CPU porque la VRAM es del LLM (stack §2
  y §7). Si el servicio no está, `emb` devuelve un vector nulo y anota el error;
  nunca lanza.

La recuperación (`IndiceRecuerdos.buscar`) es síncrona y rápida —unas decenas
de productos escalares sobre vectores de 256 floats— pero **nunca** puede correr
en el hilo de render ni en el del LLM: se llama al construir el contexto de una
petición, en el hilo del bucle. La guarda de `_comprobar_contexto` lo comprueba
por nombre de hilo y por pila de llamadas, y la suite la verifica.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import threading
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from tribal.llm.http import Transporte, transporte_http

#: Dimensión del backend determinista. 256 es suficiente para solapar tokens de
#: recuerdos cortos sin que el índice pese.
DIM_POR_DEFECTO = 256
#: Modelo de embedding pequeño; se pide en CPU para no competir con el LLM.
MODELO_EMBEDDING_POR_DEFECTO = "qwen3-embedding:0.6b"
#: Dimensión publicada hasta que el servicio responda (Qwen3-Embedding-0.6B).
DIM_OLLAMA_POR_DEFECTO = 1024
ENDPOINT_POR_DEFECTO = "http://127.0.0.1:11434"
TIMEOUT_POR_DEFECTO = 3.0
#: Hilo del LLM (`cola.NOMBRE_HILO`): la recuperación no corre ahí.
NOMBRE_HILO_LLM = "tribal-llm"
MODULO_RENDER = "tribal.ui.render"

_TOKEN = re.compile(r"\w+", re.UNICODE)


class Embedder(Protocol):
    """Lo que necesita el índice: dimensión, dispositivo declarado y vector."""

    dim: int
    usa_gpu: bool

    def emb(self, texto: str) -> tuple[float, ...]:
        """Vector de `texto`, siempre de longitud `dim`."""
        ...


class EmbedderHashing:
    """Bag-of-words con hash estable y L2 normalizado; determinista entre procesos.

    Cada token se hashea con blake2b (no `hash()`, cuya semilla cambia por
    proceso) y cae en una de las `dim` posiciones. La cuenta se normaliza, así
    que el producto escalar es directamente el coseno.
    """

    def __init__(self, dim: int = DIM_POR_DEFECTO) -> None:
        if dim < 1:
            raise ValueError(f"dim debe ser mayor que 0 (recibido {dim})")
        self.dim = dim
        #: Se declara en CPU: no hay backend que pueda pedir GPU.
        self.usa_gpu = False

    def emb(self, texto: str) -> tuple[float, ...]:
        vector = [0.0] * self.dim
        for token in _TOKEN.findall(texto.lower()):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            indice = int.from_bytes(digest[:4], "big") % self.dim
            vector[indice] += 1.0
        return _normalizar(vector)


class EmbedderOllama:
    """Embedding real vía Ollama, pedido en CPU y sin dependencias.

    `usa_gpu=False` es intención, no control: el dispositivo lo elige Ollama.
    Se documenta para que nadie lea el campo como una garantía. Un fallo de
    transporte o un HTTP distinto de 200 dejan `ultimo_error` y devuelven un
    vector nulo; el índice sigue funcionando con la memoria que ya tenga.
    """

    def __init__(
        self,
        endpoint: str = ENDPOINT_POR_DEFECTO,
        modelo: str = MODELO_EMBEDDING_POR_DEFECTO,
        timeout: float = TIMEOUT_POR_DEFECTO,
        *,
        transporte: Transporte | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.modelo = modelo
        self.timeout = timeout
        self.usa_gpu = False
        self.dim = DIM_OLLAMA_POR_DEFECTO
        #: Último fallo, para `selfcheck` o para depurar; `None` si no hubo.
        self.ultimo_error: str | None = None
        self._transporte = transporte or transporte_http

    def emb(self, texto: str) -> tuple[float, ...]:
        cuerpo = {"model": self.modelo, "input": texto}
        try:
            estado, bruto = self._transporte(
                "POST", f"{self.endpoint}/api/embed", cuerpo, self.timeout
            )
        except Exception as exc:  # servicio caído, DNS, timeout
            self.ultimo_error = f"transporte: {exc}"
            return _normalizar([0.0] * self.dim)

        if estado != 200:
            self.ultimo_error = f"http {estado}"
            return _normalizar([0.0] * self.dim)

        vector = _vector_de(bruto)
        if vector is None:
            self.ultimo_error = "respuesta sin embedding"
            return _normalizar([0.0] * self.dim)

        self.ultimo_error = None
        self.dim = len(vector)
        return _normalizar(vector)


def embedder_por_defecto() -> Embedder:
    """Backend del producto y de la suite: hashing, determinista y en CPU."""
    return EmbedderHashing()


class IndiceRecuerdos:
    """Índice en memoria: añade textos y devuelve los `k` más parecidos.

    Similitud coseno (producto escalar sobre vectores normalizados) y orden
    estable: mayor score primero y, a igualdad, id ascendente comparado como
    cadena. Volver a añadir un id lo sustituye.
    """

    def __init__(self, embedder: Embedder) -> None:
        self.embedder = embedder
        self._vectores: dict[str | int, tuple[float, ...]] = {}

    def agregar(self, id: str | int, texto: str) -> None:
        """Indexa `texto`; si el id ya existía, lo reemplaza."""
        self._vectores[id] = _normalizar(self.embedder.emb(texto))

    def buscar(self, consulta: str, k: int = 3) -> list[tuple[str | int, float]]:
        """Top-k por coseno. Nunca desde render ni desde el hilo del LLM."""
        _comprobar_contexto()
        if k <= 0:
            return []
        vector = _normalizar(self.embedder.emb(consulta))
        puntuados = [
            (recuerdo_id, _producto(vector, guardado))
            for recuerdo_id, guardado in self._vectores.items()
        ]
        puntuados.sort(key=lambda par: (-par[1], str(par[0])))
        return puntuados[:k]

    def __len__(self) -> int:
        return len(self._vectores)


def _comprobar_contexto() -> None:
    """La recuperación no corre en el hilo del LLM ni en la pila de render."""
    if threading.current_thread().name == NOMBRE_HILO_LLM:
        raise RuntimeError("la recuperacion no puede correr en el hilo del LLM")
    frame: Any = sys._getframe(1)
    while frame is not None:
        if frame.f_globals.get("__name__") == MODULO_RENDER:
            raise RuntimeError("la recuperacion no puede correr en el hilo de render")
        frame = frame.f_back


def _normalizar(vector: Sequence[float]) -> tuple[float, ...]:
    """L2: un vector nulo se queda nulo, no se divide por cero."""
    norma = math.sqrt(sum(valor * valor for valor in vector))
    if norma == 0.0:
        return tuple(vector)
    return tuple(valor / norma for valor in vector)


def _producto(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Coseno sobre vectores normalizados; dims distintas son un error claro."""
    return sum(x * y for x, y in zip(a, b, strict=True))


def _vector_de(bruto: bytes) -> list[float] | None:
    """Desenvuelve `/api/embed` (`embeddings: [[...]]`) o `/api/embeddings`."""
    try:
        datos = json.loads(bruto)
    except (TypeError, ValueError):
        return None
    if not isinstance(datos, Mapping):
        return None

    vector: Any = None
    embeddings = datos.get("embeddings")
    if isinstance(embeddings, list) and embeddings:
        vector = embeddings[0]
    if vector is None:
        vector = datos.get("embedding")
    if not isinstance(vector, list) or not vector:
        return None
    if not all(isinstance(valor, (int, float)) for valor in vector):
        return None
    return [float(valor) for valor in vector]
