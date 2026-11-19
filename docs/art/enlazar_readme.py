"""Añade el enlace a docs/art en la tabla de Documentación del README.

Se ejecuta cuando se decida versionar el arte:

    uv run python docs/art/enlazar_readme.py

Es idempotente: si la fila ya está, no hace nada. Respeta el fin de línea del
README (CRLF o LF) y el UTF-8 sin BOM, para no ensuciar el diff.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
FILA_ANCLA = "| [`vault/01_PROYECTO/arquitectura.md`]"
FILA_NUEVA = (
    "| [`docs/art/README.md`](docs/art/README.md) "
    "| Kit de arte 16 px: paleta cerrada, personajes, tilesets y el mapa |"
)


def main() -> int:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "README.md"
    if not destino.is_file():
        print(f"no existe {destino}")
        return 1

    with destino.open("r", encoding="utf-8", newline="") as fh:
        texto = fh.read()
    if FILA_NUEVA in texto:
        print("la fila ya está en el README, nada que hacer")
        return 0

    fin = "\r\n" if "\r\n" in texto else "\n"
    lineas = texto.split(fin)
    for i, linea in enumerate(lineas):
        if linea.startswith(FILA_ANCLA):
            lineas.insert(i + 1, FILA_NUEVA)
            with destino.open("w", encoding="utf-8", newline="") as fh:
                fh.write(fin.join(lineas))
            print(f"fila insertada en {destino} (línea {i + 2})")
            return 0

    print("no encontré la tabla de Documentación en el README")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
