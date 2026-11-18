"""
Parámetros de una partida, serializables a JSON.

La semilla sola no reproduce una partida: hay que saber también con cuánta
gente, en qué mapa y con qué tasas de desgaste se jugó. `SimConfig` reúne todo
eso en un objeto inmutable y un fichero JSON commiteable, para que una partida
se pueda repetir y comparar variantes cambiando un solo parámetro.

Los defaults son los de la Fase 0: un `SimConfig()` equivale a la partida que
se jugaba antes de existir este módulo.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from tribal.core.modelos import ALTO_TILES, ANCHO_TILES

#: Rango jugable de Fase 0: por debajo no hay tribu, por encima no hay frame.
MIN_INDIVIDUOS = 8
MAX_INDIVIDUOS = 15

#: Mínimo real de `_mancha`: con radio 2 pide `randint(4, lado - 5)`, que solo
#: tiene rango no vacío a partir de 9 tiles. Por debajo, el mapa no se genera.
MIN_LADO = 9

#: Campos que el motor indexa o usa como cuenta: enteros, y `bool` no vale
#: (`True` es un `int` para Python, pero un JSON así casi siempre es un error).
CAMPOS_ENTEROS = ("seed", "individuos", "ancho", "alto", "depredadores", "cooldown_reproduccion")
#: Campos que el motor multiplica: número real, nunca una cadena.
CAMPOS_TASA = ("tasa_sed", "tasa_energia", "tasa_salud")

#: Tasas de desgaste por tick. Duplican los defaults de `tribal.agents.necesidades`
#: a propósito: `core` no puede importar `agents`, así que la dirección de la
#: flecha prohíbe tomarlos de allí. Un test comprueba que no se desincronizan.
TASA_SED = 0.16
TASA_ENERGIA = 0.15
TASA_SALUD = 0.6


@dataclass(frozen=True, slots=True)
class SimConfig:
    """Configuración completa de una partida. Inmutable y serializable a JSON."""

    seed: int = 42
    individuos: int = 12
    ancho: int = ANCHO_TILES
    alto: int = ALTO_TILES
    tasa_sed: float = TASA_SED
    tasa_energia: float = TASA_ENERGIA
    tasa_salud: float = TASA_SALUD
    #: Ticks de espera entre crías de un mismo individuo.
    cooldown_reproduccion: int = 600
    #: Cuántos depredadores pueblan el mapa (0 = ninguno) y si están activos.
    depredadores: int = 1
    depredador_activo: bool = True

    @classmethod
    def desde_json(cls, path: str | Path) -> SimConfig:
        """Lee una config de `path` y la valida. `ValueError` si no sirve."""
        with open(path, encoding="utf-8") as fichero:
            datos = json.load(fichero)
        if not isinstance(datos, dict):
            raise ValueError(f"{path}: se esperaba un objeto JSON con los parámetros de la partida")

        desconocidas = sorted(set(datos) - {campo.name for campo in fields(cls)})
        if desconocidas:
            raise ValueError(f"{path}: claves desconocidas: {', '.join(desconocidas)}")

        config = cls(**datos)
        validar(config, origen=str(path))
        return config

    def a_json(self) -> dict[str, int | float]:
        """Los parámetros como dict serializable, en el mismo formato que lee `desde_json`."""
        return asdict(self)


def validar(config: SimConfig, origen: str = "config") -> None:
    """Comprueba tipos y rangos; el motor no puede defenderlos por sí solo.

    Todo error nombra la clave y el valor recibido: un JSON mal escrito tiene
    que producir un mensaje útil, no una traza desde el fondo del motor.
    """
    for nombre in CAMPOS_ENTEROS:
        valor = getattr(config, nombre)
        if isinstance(valor, bool) or not isinstance(valor, int):
            raise ValueError(f"{origen}: {nombre} debe ser un entero (recibido {valor!r})")
    for nombre in CAMPOS_TASA:
        valor = getattr(config, nombre)
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise ValueError(f"{origen}: {nombre} debe ser un número (recibido {valor!r})")
        if valor <= 0:
            raise ValueError(f"{origen}: {nombre} debe ser mayor que 0 (recibido {valor!r})")

    if not MIN_INDIVIDUOS <= config.individuos <= MAX_INDIVIDUOS:
        raise ValueError(
            f"{origen}: individuos debe estar entre {MIN_INDIVIDUOS} y {MAX_INDIVIDUOS} "
            f"(recibido {config.individuos})"
        )
    if config.depredadores < 0:
        raise ValueError(
            f"{origen}: depredadores no puede ser negativo (recibido {config.depredadores})"
        )
    if config.cooldown_reproduccion <= 0:
        raise ValueError(
            f"{origen}: cooldown_reproduccion debe ser mayor que 0 "
            f"(recibido {config.cooldown_reproduccion})"
        )
    if not isinstance(config.depredador_activo, bool):
        raise ValueError(
            f"{origen}: depredador_activo debe ser true o false "
            f"(recibido {config.depredador_activo!r})"
        )
    if config.ancho < MIN_LADO or config.alto < MIN_LADO:
        raise ValueError(
            f"{origen}: ancho y alto deben ser al menos {MIN_LADO} tiles "
            f"(recibido {config.ancho}x{config.alto})"
        )
