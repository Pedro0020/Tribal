"""
El diario de la tribu: tick, tipo, texto e individuo de cada hito (concepto §10).

El motor escribe lo que pasó y el LLM solo pone la frase. Por eso la entrada se
registra en el instante del hito y la narración llega después: si el modelo está
apagado, falla o no hay hueco en la cola, el diario conserva el hecho con
`texto=""` y `narrada=False`. Cuando llega, el texto se guarda **tal cual** lo
devolvió el modelo: reescribirlo sería narrar dos veces.

Una entrada `dialogo` es distinta: su texto no lo inventa el cronista, es lo que
dijo el individuo en una decisión del LLM, y por eso se registra ya con texto y
con `narrada=False`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, get_args

#: Hitos que el motor reconoce. Un tipo fuera de esta lista es un error de código.
TipoEntrada = Literal[
    "primer_fuego",
    "primera_caza_grupo",
    "primera_palabra",
    "primer_rito",
    "muerte_ancestro",
    "primera_tradicion",
    "dialogo",
]
TIPOS: tuple[str, ...] = get_args(TipoEntrada)


@dataclass(slots=True)
class Entrada:
    """Un hecho del diario. `narrada` dice si la frase la puso el LLM.

    `individuo_id` es el sujeto del hecho y `narrador_id` quien lo cuenta: la
    saliencia decide el segundo (concepto §10b), y solo las entradas con
    `narrador_id` cuentan para la concentración narrativa.
    """

    tick: int
    tipo: str
    texto: str = ""
    individuo_id: int | None = None
    narrador_id: int | None = None
    narrada: bool = False

    def a_json(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "tipo": self.tipo,
            "texto": self.texto,
            "individuo_id": self.individuo_id,
            "narrador_id": self.narrador_id,
            "narrada": self.narrada,
        }


class Diario:
    """Lista append-only de entradas, en orden de tick (el motor va hacia atrás)."""

    def __init__(self) -> None:
        self.entradas: list[Entrada] = []

    def registrar(
        self,
        tick: int,
        tipo: str,
        *,
        individuo_id: int | None = None,
        narrador_id: int | None = None,
        texto: str = "",
    ) -> int:
        """Anota la entrada y devuelve su índice, que es lo que luego se narra."""
        if tipo not in TIPOS:
            raise ValueError(f"tipo de entrada desconocido: {tipo!r}")
        self.entradas.append(
            Entrada(
                tick=tick,
                tipo=tipo,
                texto=texto,
                individuo_id=individuo_id,
                narrador_id=narrador_id,
            )
        )
        return len(self.entradas) - 1

    def narrar(self, indice: int, texto: str) -> bool:
        """Guarda la frase del LLM sin tocarla. Vacía o fuera de rango: no-op."""
        if not 0 <= indice < len(self.entradas) or not texto:
            return False
        entrada = self.entradas[indice]
        entrada.texto = texto
        entrada.narrada = True
        return True

    def ultimas(self, n: int) -> list[Entrada]:
        """Las `n` más recientes, **en orden de tick**, no de llegada.

        El append no garantiza orden: una decisión asíncrona que llega tarde
        anota un diálogo de un tick anterior al último hito. Ordenar aquí —y no
        confiar en el orden de inserción— mantiene cronológico el diario, y el
        `sort` es estable: a igual tick, se respeta el orden de llegada.
        """
        if n <= 0:
            return []
        return sorted(self.entradas, key=lambda entrada: entrada.tick)[-n:]

    def cuenta(self, tipo: str) -> int:
        return sum(1 for entrada in self.entradas if entrada.tipo == tipo)

    def a_json(self) -> dict[str, Any]:
        """Recuento serializable para `resumen()`; las entradas van aparte."""
        return {
            "entradas": len(self.entradas),
            "narradas": sum(1 for entrada in self.entradas if entrada.narrada),
            "dialogos": self.cuenta("dialogo"),
        }
