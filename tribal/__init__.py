"""
tribal — paquete del proyecto.

Aquí vive el código del producto: motor de reglas, agentes simulados, capa
LLM y cultura. El arnés (`agents/`, `harness/`, `init.sh`) no depende de lo
que haya aquí dentro más allá de dos cosas:

- que el paquete exista y sea importable (lo comprueba `./init.sh`),
- que su nombre coincida con `project_slug` en `project.yml`.

La arquitectura de estas piezas está en `vault/01_PROYECTO/arquitectura.md`.
"""

__version__ = "0.1.1"
