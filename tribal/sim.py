"""
La simulación: reloj, población y resumen de una partida.

Este módulo es el pegamento de la Fase 0 y no importa Pygame. `run()` con
`headless=False` importa `tribal.ui.app` en ese momento y solo entonces, así
que el motor se puede ejercitar y medir sin abrir ventana ni cargar SDL.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, replace
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
from tribal.culture import beneficios as modulo_beneficios
from tribal.culture import tradiciones
from tribal.culture.combinaciones import COMBINACIONES
from tribal.culture.grafo import Grafo

#: Presupuesto de frame a 60 fps.
MS_FRAME = 16.67
#: Energía mínima de los dos progenitores para tener cría, y distancia máxima entre ellos.
UMBRAL_REPRODUCCION = 65.0
DISTANCIA_PAREJA = 2.0
#: Energía con la que nace una cría. La paga la madre: el nacimiento no inyecta
#: energía neta en la población (concepto §13: una sequía no puede ser el
#: régimen favorable por subsidio reproductivo).
ENERGIA_CRIA = 50.0
#: Se reexporta desde `tribal.core.genoma`; los tests de F0 fijan aquí el límite.
MUTACION = modulo_genoma.MUTACION
#: Radio (en tiles) dentro del cual se considera que alguien está junto al agua.
RADIO_AGUA = 2.0


@dataclass(frozen=True, slots=True)
class Practica:
    """Qué rama hace avanzar una conducta y qué habilidad exige, si alguna.

    `habilidad` vacía significa que la condición de la práctica es la situación
    (un vecino, un bosque, un aprendiz) y la valida el propio verbo. El árbol
    sigue decidiendo el nivel: una práctica solo descubre el siguiente escalón
    si sus prerrequisitos ya están activos.
    """

    rama: Rama
    habilidad: str | None = None


#: Qué práctica hace avanzar qué rama del árbol (F1-002 y CONNECT-001).
#: Comer y tallar alimentan la lítica; frotar madera, el fuego; hablar, el
#: lenguaje; enseñar y cuidar, los roles; pintar, lo simbólico. Beber,
#: descansar, huir y moverse no dejan cultura.
PRACTICAS: dict[str, Practica] = {
    "comer": Practica("litica", "recolectar"),
    "tallar": Practica("litica"),
    "frotar_madera": Practica("fuego"),
    "hablar": Practica("lenguaje"),
    "ensenar": Practica("roles"),
    "cuidar": Practica("roles"),
    "pintar": Practica("simbolico"),
}
#: Sequía de concepto §13: el agua y las bayas reducen su capacidad de carga a
#: la mitad y regeneran al mismo ritmo relativo; la sed sube para todos. En
#: calma el factor es 1.0 y nada cambia respecto a Fase 0.
PENALIZACION_SEQUIA = 2.0
FACTOR_SED_SEQUIA = 1.25
#: Un divergente experimenta con probabilidad proporcional a lo que se desvía
#: (máximo 15 % por tick) y completa el cruce la mitad de las veces.
PROB_INTENTO_DIVERGENTE = 0.15
PROB_COMPLETAR_COMBINACION = 0.5


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
        #: Experimentos de los divergentes y cruces que llegaron a nodo (§9b).
        self.intentos_divergentes = 0
        self.combinaciones_logradas = 0
        #: Tradiciones nacidas de la imitación (nivel 2 de §8b).
        self.tradiciones = 0
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
        en_crisis = self._en_crisis()
        recursos.regenerar(self.mundo, PENALIZACION_SEQUIA if en_crisis else 1.0)

        #: Beneficios que disfruta cada vivo este tick, según lo que sabe. La
        #: crisis no cambia el temperamento de nadie: cambia la capacidad de
        #: carga del mundo y, con ella, cuánto importa saber una técnica.
        beneficios: dict[int, modulo_beneficios.Beneficios] = {}
        for individuo in self.mundo.individuos:
            efecto = modulo_beneficios.conocidos(self.grafo, individuo.habilidades.conocidas)
            beneficios[individuo.id] = efecto
            necesidades.evolucionar(
                individuo.necesidades,
                individuo.genoma,
                self.config.tasa_sed * (FACTOR_SED_SEQUIA if en_crisis else 1.0) * efecto.tasa_sed,
                self.config.tasa_energia,
                self.config.tasa_salud,
            )
            individuo.edad += 1
            if individuo.cooldown_reproduccion > 0:
                individuo.cooldown_reproduccion -= 1

        modulo_depredador.mover(self.mundo, self._factor_dano)
        self._enterrar()

        descubierto = False
        for individuo in self.mundo.individuos:
            # Experimentar consume el tick: el divergente que prueba un cruce
            # no come ni bebe en ese tick (concepto §9b).
            if self._intentar_combinacion(individuo):
                continue
            efecto = beneficios[individuo.id]
            ya_se_movio = individuo.movido
            accion = instinto.elegir(individuo, self.mundo)
            huyendo_antes = individuo.huyendo
            individuo.huyendo = accion.nombre == "huir"
            if individuo.huyendo and not huyendo_antes:
                self.huidas += 1
            aplicada = acciones.aplicar(
                individuo,
                self.mundo,
                accion,
                bonus_bayas=efecto.bayas,
                bonus_caza=efecto.caza,
            )
            # Una enseñanza que no prende no debe clavar al individuo: deambula.
            if not aplicada and accion.nombre == "ensenar":
                acciones.aplicar(
                    individuo,
                    self.mundo,
                    instinto.deambular(individuo, self.mundo),
                    bonus_bayas=efecto.bayas,
                    bonus_caza=efecto.caza,
                )
            if individuo.movido and not ya_se_movio:
                self._movidos += 1
            # Un nodo nuevo como mucho por tick: el árbol avanza al ritmo de la
            # tribu, no de golpe en el primer tick en que alguien come. Practicar
            # se cuenta siempre, descubra nodo o no: así se mide la imitación.
            if aplicada and self._practicar(individuo, accion.nombre, descubrir=not descubierto):
                descubierto = True

        if tradiciones.evaluar(self.grafo, self.mundo.tick) is not None:
            self.tradiciones += 1
        self._reproducir()
        self.agrupamiento_max = max(self.agrupamiento_max, self._junto_al_agua())

        self._ms_acumulados += (time.perf_counter() - inicio) * 1000.0

    def _factor_dano(self, presa: Individuo) -> float:
        """Cuánto le muerde el depredador: quien sabe la técnica de vigilia, menos."""
        return modulo_beneficios.conocidos(self.grafo, presa.habilidades.conocidas).dano_depredador

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
            individuo for individuo in self.mundo.individuos if self._puede_reproducir(individuo)
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

    def _umbral_reproduccion(self) -> float:
        """El mismo umbral en calma y en crisis: la sequía no subvenciona la cría."""
        return UMBRAL_REPRODUCCION

    def _puede_reproducir(self, individuo: Individuo) -> bool:
        return (
            individuo.edad >= individuo.madurez
            and individuo.cooldown_reproduccion == 0
            and individuo.necesidades.energia > self._umbral_reproduccion()
        )

    def _nacer(self, madre: Individuo, padre: Individuo) -> None:
        x, y = _posicion_cria(self.mundo, madre)
        # La cría nace con energía que sale de la madre: el balance es cero.
        # Así una cría no es comida gratis y la crisis no dispara un baby-boom.
        madre.necesidades.energia = max(0.0, madre.necesidades.energia - ENERGIA_CRIA)
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

    def _en_crisis(self) -> bool:
        """True mientras dure la sequía: sin límite (`sequia_ticks=0`) o hasta su tick."""
        if not self.config.crisis:
            return False
        return self.config.sequia_ticks <= 0 or self.mundo.tick <= self.config.sequia_ticks

    def _intentar_combinacion(self, individuo: Individuo) -> bool:
        """Un divergente gasta el tick probando un cruce. True si lo intentó.

        Solo pasa en crisis (concepto §9b y §13): en calma la tradición basta y
        el motor no gasta ticks en experimentar, así que sin crisis no aparece
        ningún nodo `combinacion`. El candidato tiene que tener sus dos nodos
        activos y no existir aún; si el cruce no cuaja, el intento se cuenta
        igual, porque el experimento ocurrió. Descubrirlo enseña al autor la
        habilidad de la técnica: el nodo es de la tribu, pero la ventaja es de
        quien la sabe usar (concepto §9b).
        """
        if not self._en_crisis():
            return False
        if modulo_genoma.temperamento(individuo.genoma) != "divergente":
            return False
        if necesidades.sed_critica(individuo.necesidades) or necesidades.energia_baja(
            individuo.necesidades
        ):
            return False
        candidatas = [
            combinacion
            for combinacion in COMBINACIONES.values()
            if combinacion.id not in self.grafo.nodos
            and all(self.grafo.activo(requisito) for requisito in combinacion.requisitos)
        ]
        if not candidatas:
            return False
        exceso = individuo.genoma.divergencia - modulo_genoma.UMBRAL_DIVERGENTE
        margen = modulo_genoma.DIVERGENCIA_MAX - modulo_genoma.UMBRAL_DIVERGENTE
        if self.mundo.azar.random() >= PROB_INTENTO_DIVERGENTE * exceso / margen:
            return False

        self.intentos_divergentes += 1
        candidata = self.mundo.azar.choice(candidatas)
        if self.mundo.azar.random() < PROB_COMPLETAR_COMBINACION:
            self.grafo.descubrir(
                candidata.id,
                autor=individuo.id,
                tick=self.mundo.tick,
                origen="combinacion",
            )
            individuo.habilidades.aprender(
                modulo_beneficios.HABILIDAD_POR_COMBINACION[candidata.id]
            )
            self.combinaciones_logradas += 1
        return True

    def _practicar(self, individuo: Individuo, accion: str, *, descubrir: bool) -> bool:
        """Registra la práctica de `accion` y, si toca, avanza su rama del árbol.

        Solo cuenta quien **sabe** la habilidad de la práctica, si la práctica
        exige una (concepto §5: la cultura sale de lo que ya se sabe hacer); en
        las que se definen por situación, el verbo ya comprobó la condición.
        El uso se anota en el nodo más avanzado de la rama —la técnica que está
        funcionando— y un conformista que la usa sin haberla descubierto suma
        una imitación (§9b). El nodo nuevo nace con su origen escrito por
        `Grafo.descubrir`, que valida los prerrequisitos.
        """
        practica = PRACTICAS.get(accion)
        if practica is None:
            return False
        if practica.habilidad is not None and not individuo.habilidades.sabe(practica.habilidad):
            return False
        rama = practica.rama
        en_uso = self.grafo.ultimo_activo(rama)
        if en_uso is not None:
            conformista = modulo_genoma.temperamento(individuo.genoma) == "conformista"
            self.grafo.registrar_uso(
                en_uso.id,
                usuario=individuo.id,
                es_conformista=conformista,
                tick=self.mundo.tick,
            )
        if not descubrir:
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
        temperamentos = [modulo_genoma.temperamento(individuo.genoma) for individuo in vivos]
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
            "n_divergentes": temperamentos.count("divergente"),
            "n_conformistas": temperamentos.count("conformista"),
            "n_neutros": temperamentos.count("neutro"),
            "intentos_divergentes": self.intentos_divergentes,
            "combinaciones_logradas": self.combinaciones_logradas,
            "tradiciones": self.tradiciones,
            "imitaciones": sum(self.grafo.imitado.values()),
            "beneficios": modulo_beneficios.activos(self.grafo).a_json(),
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
