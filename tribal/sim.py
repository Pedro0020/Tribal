"""
La simulación: reloj, población y resumen de una partida.

Este módulo es el pegamento de la Fase 0 y no importa Pygame. `run()` con
`headless=False` importa `tribal.ui.app` en ese momento y solo entonces, así
que el motor se puede ejercitar y medir sin abrir ventana ni cargar SDL.
"""

from __future__ import annotations

import math
import time
from dataclasses import replace
from typing import Any

from tribal.agents import instinto, necesidades
from tribal.config import SimConfig
from tribal.core import acciones, recursos
from tribal.core import depredador as modulo_depredador
from tribal.core import genoma as modulo_genoma
from tribal.core import mundo as modulo_mundo
from tribal.core.habilidades import Habilidades, Rama
from tribal.core.modelos import (
    LONGEVIDAD_TICKS,
    Individuo,
    Mundo,
    Necesidades,
    TipoTile,
)
from tribal.culture.grafo import Grafo

#: Presupuesto de frame a 60 fps.
MS_FRAME = 16.67
#: Energía mínima de los dos progenitores para tener cría, y distancia máxima entre ellos.
UMBRAL_REPRODUCCION = 65.0
DISTANCIA_PAREJA = 2.0
#: Energía con la que nace una cría y desviación máxima del genoma heredado.
ENERGIA_CRIA = 80.0
#: Se reexporta desde `tribal.core.genoma`; los tests de F0 fijan aquí el límite.
MUTACION = modulo_genoma.MUTACION
#: Radio (en tiles) dentro del cual se considera que alguien está junto al agua.
RADIO_AGUA = 2.0
#: Qué práctica, con qué habilidad, hace avanzar qué rama del árbol (F1-002).
#: `recolectar` es la habilidad con la que arranca la tribu, así que la lítica
#: progresa en cuanto alguien come; beber, descansar y huir no dejan cultura.
#: Fuego, lenguaje y roles esperan su práctica: en F1 el árbol es andamiaje y
#: solo lo recorre lo que la tribu ya sabía hacer antes de tenerlo.
PRACTICAS: dict[str, tuple[str, Rama]] = {
    "comer": ("recolectar", "litica"),
}


class Simulacion:
    """Estado de una partida: mundo + contadores que no viven en el mundo."""

    def __init__(self, mundo: Mundo, config: SimConfig | None = None) -> None:
        self.mundo = mundo
        self.config = config or SimConfig(
            seed=mundo.seed,
            individuos=len(mundo.individuos),
            ancho=mundo.ancho,
            alto=mundo.alto,
        )
        self.poblacion_inicial = len(mundo.individuos)
        self.muertes = 0
        self.nacimientos = 0
        self.agrupamiento_max = 0
        self.huidas = 0
        self._movidos = 0
        self._ms_acumulados = 0.0
        #: Lo que la tribu ha descubierto. Vive aquí y no en el mundo.
        self.grafo = Grafo()
        self._agua_tiles = {
            (x, y)
            for y, fila in enumerate(mundo.tiles)
            for x, tipo in enumerate(fila)
            if tipo == TipoTile.AGUA
        }

    def step(self) -> None:
        """Un tick: reloj, homeostasis, depredador y muertes, decisiones y crías.

        El orden importa: la homeostasis corre primero y luego el depredador
        muerde; la muerte se comprueba al final de esa secuencia. Si se
        comprobara antes del mordisco, la recuperación de salud del tick
        siguiente devolvería la vida a una presa que se quedó a 0.
        """
        inicio = time.perf_counter()

        self.mundo.tick += 1
        recursos.regenerar(self.mundo)

        for individuo in self.mundo.individuos:
            necesidades.evolucionar(
                individuo.necesidades,
                individuo.genoma,
                self.config.tasa_sed,
                self.config.tasa_energia,
                self.config.tasa_salud,
            )
            individuo.edad += 1
            if individuo.cooldown_reproduccion > 0:
                individuo.cooldown_reproduccion -= 1

        modulo_depredador.mover(self.mundo)
        self._enterrar()

        descubierto = False
        for individuo in self.mundo.individuos:
            ya_se_movio = individuo.movido
            accion = instinto.elegir(individuo, self.mundo)
            huyendo_antes = individuo.huyendo
            individuo.huyendo = accion.nombre == "huir"
            if individuo.huyendo and not huyendo_antes:
                self.huidas += 1
            aplicada = acciones.aplicar(individuo, self.mundo, accion)
            # Una enseñanza que no prende no debe clavar al individuo: deambula.
            if not aplicada and accion.nombre == "ensenar":
                acciones.aplicar(individuo, self.mundo, instinto.deambular(individuo, self.mundo))
            if individuo.movido and not ya_se_movio:
                self._movidos += 1
            # Un nodo nuevo como mucho por tick: el árbol avanza al ritmo de la
            # tribu, no de golpe en el primer tick en que alguien come.
            if aplicada and not descubierto:
                descubierto = self._practicar(individuo, accion.nombre)

        self._reproducir()
        self.agrupamiento_max = max(self.agrupamiento_max, self._junto_al_agua())

        self._ms_acumulados += (time.perf_counter() - inicio) * 1000.0

    def _enterrar(self) -> None:
        """Retira a quien se quedó sin salud o sin edad. Un contador por individuo."""
        vivos = []
        for individuo in self.mundo.individuos:
            if individuo.necesidades.salud <= 0.0 or individuo.edad >= _longevidad(individuo):
                individuo.vivo = False
                self.muertes += 1
            else:
                vivos.append(individuo)
        self.mundo.individuos = vivos

    def _reproducir(self) -> None:
        """Una cría por pareja disponible y tick; el cooldown evita la explosión."""
        candidatos = [
            individuo for individuo in self.mundo.individuos if _puede_reproducir(individuo)
        ]
        madres = [individuo for individuo in candidatos if individuo.sexo == "f"]
        padres = [individuo for individuo in candidatos if individuo.sexo == "m"]
        for madre in madres:
            if madre.cooldown_reproduccion != 0:
                continue
            for padre in padres:
                if padre.cooldown_reproduccion != 0:
                    continue
                if recursos.distancia(madre.x, madre.y, padre.x, padre.y) > DISTANCIA_PAREJA:
                    continue
                self._nacer(madre, padre)
                break

    def _nacer(self, madre: Individuo, padre: Individuo) -> None:
        x, y = _posicion_cria(self.mundo, madre)
        hijo = Individuo(
            id=max(individuo.id for individuo in self.mundo.individuos) + 1,
            sexo="f" if self.nacimientos % 2 == 0 else "m",
            genoma=modulo_genoma.heredar(madre.genoma, padre.genoma, self.mundo.azar),
            necesidades=Necesidades(energia=ENERGIA_CRIA),
            x=x,
            y=y,
            # Las habilidades no se heredan: la cría solo trae lo de la tribu.
            habilidades=Habilidades.iniciales(),
        )
        madre.cooldown_reproduccion = self.config.cooldown_reproduccion
        padre.cooldown_reproduccion = self.config.cooldown_reproduccion
        self.mundo.individuos.append(hijo)
        self.nacimientos += 1

    def _junto_al_agua(self) -> int:
        """Cuántos individuos están a `RADIO_AGUA` tiles o menos de un tile de agua."""
        if not self._agua_tiles:
            return 0
        return sum(
            1 for individuo in self.mundo.individuos if _cerca_de_agua(individuo, self._agua_tiles)
        )

    def _practicar(self, individuo: Individuo, accion: str) -> bool:
        """Aplica la práctica de `accion`: True si descubrió un nodo del árbol.

        Solo avanza quien **sabe** la habilidad de la práctica (concepto §5: la
        cultura sale de lo que ya se sabe hacer), y el nodo nace con su origen
        escrito por `Grafo.descubrir`, que es quien valida los prerrequisitos.
        """
        practica = PRACTICAS.get(accion)
        if practica is None:
            return False
        habilidad, rama = practica
        if not individuo.habilidades.sabe(habilidad):
            return False
        return self.grafo.avanzar(rama, autor=individuo.id, tick=self.mundo.tick) is not None

    @property
    def poblacion(self) -> int:
        return len(self.mundo.individuos)

    @property
    def ms_tick_medio(self) -> float:
        return self._ms_acumulados / self.mundo.tick if self.mundo.tick else 0.0

    def resumen(self) -> dict[str, Any]:
        """Dict serializable y determinista: no incluye tiempos de reloj de pared."""
        vivos = self.mundo.individuos
        media_energia = (
            sum(individuo.necesidades.energia for individuo in vivos) / len(vivos) if vivos else 0.0
        )
        media_sed = (
            sum(individuo.necesidades.sed for individuo in vivos) / len(vivos) if vivos else 0.0
        )
        media_genes = {
            rasgo: round(
                sum(getattr(individuo.genoma, rasgo) for individuo in vivos) / len(vivos), 3
            )
            if vivos
            else 0.0
            for rasgo in modulo_genoma.RASGOS
        }
        habilidades = {individuo.id: sorted(individuo.habilidades.conocidas) for individuo in vivos}
        return {
            "seed": self.mundo.seed,
            "ticks": self.mundo.tick,
            "poblacion_inicial": self.poblacion_inicial,
            "poblacion_final": len(vivos),
            "nacimientos": self.nacimientos,
            "muertes": self.muertes,
            "media_energia": round(media_energia, 2),
            "media_sed": round(media_sed, 2),
            "media_genes": media_genes,
            "habilidades_distintas": len({h for skills in habilidades.values() for h in skills}),
            "habilidades": habilidades,
            "individuos_movidos": self._movidos,
            "depredador": {
                "activos": len(self.mundo.depredadores),
                "ataques": sum(depredador.ataques for depredador in self.mundo.depredadores),
                "muertes": sum(depredador.muertes for depredador in self.mundo.depredadores),
            },
            "agrupamiento_max": self.agrupamiento_max,
            "huidas": self.huidas,
            **self.grafo.a_json(),
            "config": self.config.a_json(),
        }


def crear(seed: int, individuos: int = 12, config: SimConfig | None = None) -> Simulacion:
    """Partida nueva. `seed` e `individuos` mandan sobre lo que diga `config`."""
    if config is None:
        config = SimConfig(seed=seed, individuos=individuos)
    else:
        config = replace(config, seed=seed, individuos=individuos)
    return Simulacion(modulo_mundo.crear(seed, individuos, config=config), config)


def run(
    ticks: int,
    seed: int,
    headless: bool,
    individuos: int = 12,
    config: SimConfig | None = None,
) -> Simulacion:
    """Corre la partida `ticks` ticks (`0` = sin límite) y devuelve la simulación.

    En modo ventana el límite lo pone el usuario con ESC o cerrando la ventana;
    `ticks` sigue sirviendo como tope opcional.
    """
    simulacion = crear(seed, individuos, config)
    if headless:
        for _ in range(ticks):
            simulacion.step()
        return simulacion

    from tribal.ui import app  # import perezoso: Pygame no entra en el motor

    app.bucle(simulacion, ticks)
    return simulacion


def _longevidad(individuo: Individuo) -> int:
    """Ticks que vive: la base por el multiplicador heredado."""
    return int(LONGEVIDAD_TICKS * individuo.genoma.longevidad)


def _puede_reproducir(individuo: Individuo) -> bool:
    return (
        individuo.edad >= individuo.madurez
        and individuo.cooldown_reproduccion == 0
        and individuo.necesidades.energia > UMBRAL_REPRODUCCION
    )


def _posicion_cria(mundo: Mundo, madre: Individuo) -> tuple[float, float]:
    """Al lado de la madre; si está rodeada de agua, en su misma casilla."""
    for dx, dy in ((0.6, 0.0), (-0.6, 0.0), (0.0, 0.6), (0.0, -0.6)):
        if mundo.pisable(madre.x + dx, madre.y + dy):
            return madre.x + dx, madre.y + dy
    return madre.x, madre.y


def _cerca_de_agua(individuo: Individuo, agua: set[tuple[int, int]]) -> bool:
    """True si hay un tile de agua a `RADIO_AGUA` tiles o menos."""
    tile_x = int(individuo.x)
    tile_y = int(individuo.y)
    return any(
        (x, y) in agua and math.hypot(x + 0.5 - individuo.x, y + 0.5 - individuo.y) <= RADIO_AGUA
        for x in range(tile_x - 2, tile_x + 3)
        for y in range(tile_y - 2, tile_y + 3)
    )
