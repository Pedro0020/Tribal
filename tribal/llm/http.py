"""
Transporte HTTP de la capa LLM, compartido por el cliente y los embeddings.

La stdlib basta: `urllib.request` para el POST/GET y `urllib.error.HTTPError`
para devolver el cuerpo del error en vez de lanzarlo. Cliente y embeddings
inyectan un transporte falso en los tests; el real vive aquí para no tener dos
copias de la misma función.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

#: (método, url, cuerpo, timeout) -> (estado HTTP, cuerpo bruto).
Transporte = Callable[[str, str, dict[str, Any] | None, float], tuple[int, bytes]]


def transporte_http(
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
