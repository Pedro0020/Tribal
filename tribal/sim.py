"""
La simulación: reloj, población y resumen de una partida.

Este módulo es el pegamento de la Fase 0 y no importa Pygame. `run()` con
`headless=False` importa `tribal.ui.app` en ese momento y solo entonces, así
que el motor se puede ejercitar y medir sin abrir ventana ni cargar SDL.
"""

from __future__ import annotations

import time

from tribal.agents import instinto, necesidades
from tribal.core import acciones, recursos
from tribal.core import mundo as modulo_mundo
from tribal.core.modelos import Mundo

#: Presupuesto de frame a 60 fps.
MS_FRAME = 16.67


class Simulacion:
    """Estado de una partida: mundo + contadores que no viven en el mundo."""

    def __init__(self, mundo: Mundo) -> None:
        self.mundo = mundo
        self.poblacion_inicial = len(mundo.individuos)
        self.muertes = 0
        self.nacimientos = 0
        self._movidos = 0
        self._ms_acumulados = 0.0

    def step(self) -> None:
        """Un tick: reloj, homeostasis, muertes, decisiones y acciones."""
        inicio = time.perf_counter()

        self.mundo.tick += 1
        recursos.regenerar(self.mundo)

        for individuo in self.mundo.individuos:
            necesidades.evolucionar(individuo.necesidades, individuo.genoma)

        vivos = []
        for individuo in self.mundo.individuos:
            if individuo.necesidades.salud <= 0.0:
                individuo.vivo = False
                self.muertes += 1
            else:
                vivos.append(individuo)
        self.mundo.individuos = vivos

        for individuo in self.mundo.individuos:
            ya_se_movio = individuo.movido
            accion = instinto.elegir(individuo, self.mundo)
            acciones.aplicar(individuo, self.mundo, accion)
            if individuo.movido and not ya_se_movio:
                self._movidos += 1

        self._ms_acumulados += (time.perf_counter() - inicio) * 1000.0

    @property
    def poblacion(self) -> int:
        return len(self.mundo.individuos)

    @property
    def ms_tick_medio(self) -> float:
        return self._ms_acumulados / self.mundo.tick if self.mundo.tick else 0.0

    def resumen(self) -> dict[str, int | float]:
        """Dict serializable y determinista: no incluye tiempos de reloj de pared."""
        vivos = self.mundo.individuos
        media_energia = (
            sum(individuo.necesidades.energia for individuo in vivos) / len(vivos) if vivos else 0.0
        )
        media_sed = (
            sum(individuo.necesidades.sed for individuo in vivos) / len(vivos) if vivos else 0.0
        )
        return {
            "seed": self.mundo.seed,
            "ticks": self.mundo.tick,
            "poblacion_inicial": self.poblacion_inicial,
            "poblacion_final": len(vivos),
            "nacimientos": self.nacimientos,
            "muertes": self.muertes,
            "media_energia": round(media_energia, 2),
            "media_sed": round(media_sed, 2),
            "individuos_movidos": self._movidos,
        }


def crear(seed: int, individuos: int = 12) -> Simulacion:
    return Simulacion(modulo_mundo.crear(seed, individuos))


def run(ticks: int, seed: int, headless: bool, individuos: int = 12) -> Simulacion:
    """Corre la partida `ticks` ticks (`0` = sin límite) y devuelve la simulación.

    En modo ventana el límite lo pone el usuario con ESC o cerrando la ventana;
    `ticks` sigue sirviendo como tope opcional.
    """
    simulacion = crear(seed, individuos)
    if headless:
        for _ in range(ticks):
            simulacion.step()
        return simulacion

    from tribal.ui import app  # import perezoso: Pygame no entra en el motor

    app.bucle(simulacion, ticks)
    return simulacion
