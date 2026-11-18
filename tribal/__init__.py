"""
tribal — paquete del proyecto.

Aquí vive el código del producto: motor de reglas, agentes simulados, capa
LLM y cultura. El arnés (`agents/`, `harness/`, `init.sh`) no depende de lo
que haya aquí dentro más allá de dos cosas:

- que el paquete exista y sea importable (lo comprueba `./init.sh`),
- que su nombre coincida con `project_slug` en `project.yml`.

La arquitectura de estas piezas está en `vault/01_PROYECTO/arquitectura.md`.
"""

from importlib.metadata import PackageNotFoundError, version

#: Fuente única de la versión: los metadatos del paquete instalado
#: (`pyproject.toml` → `uv sync`). `documentation_agent.bump_version` reescribe
#: pyproject y, tras `uv sync`, esto lo sigue solo. Antes había un literal aquí
#: que nadie actualizaba (0.1.1 frente a 0.1.4 en pyproject).
try:
    __version__ = version("tribal")
except PackageNotFoundError:  # sin instalar (repo recién clonado)
    __version__ = "0.0.0"
