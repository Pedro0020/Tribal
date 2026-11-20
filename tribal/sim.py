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
from pathlib import Path
from typing import Any, cast

from tribal.agents import instinto, necesidades, saliencia
from tribal.config import SimConfig
from tribal.core import acciones, recursos
from tribal.core import depredador as modulo_depredador
from tribal.core import genoma as modulo_genoma
from tribal.core import mundo as modulo_mundo
from tribal.core.acciones import Accion, NombreAccion
from tribal.core.habilidades import Habilidades, Rama
from tribal.core.modelos import (
    LONGEVIDAD_TICKS,
    Individuo,
    Mundo,
    Necesidades,
    TipoTile,
)
from tribal.culture import beneficios as modulo_beneficios
from tribal.culture import propuestas as modulo_propuestas
from tribal.culture import tradiciones, transmision
from tribal.culture.arbol import Nodo
from tribal.culture.combinaciones import COMBINACIONES
from tribal.culture.diario import Diario
from tribal.culture.grafo import Grafo
from tribal.culture.propuestas import PropuestaInvalida
from tribal.llm import candidatas as modulo_candidatas
from tribal.llm.cola import ColaLLM, Peticion, PeticionNarracion, PeticionNodo, PropuestaNodo
from tribal.llm.embeddings import IndiceRecuerdos, embedder_por_defecto
from tribal.store.repositorio import Repositorio

#: Presupuesto de frame a 60 fps.
MS_FRAME = 16.67
#: Energía mínima de los dos progenitores para tener cría, y distancia máxima entre ellos.
UMBRAL_REPRODUCCION = 65.0
DISTANCIA_PAREJA = 2.0
#: Energía con la que nace una cría. La paga la madre **entera**, y nunca más de
#: lo que tiene: el nacimiento no inyecta energía neta en la población (concepto
#: §13: una sequía no puede ser el régimen favorable por subsidio reproductivo).
ENERGIA_CRIA = 50.0
#: Se reexporta desde `tribal.core.genoma`; los tests de F0 fijan aquí el límite.
MUTACION = modulo_genoma.MUTACION
#: Radio (en tiles) dentro del cual se considera que alguien está junto al agua.
RADIO_AGUA = 2.0
#: Verbos que `acciones.aplicar` resuelve con solo el nombre: sin destino ni
#: objetivo. `huir` no está aquí porque necesita la amenaza, que resuelve
#: `_intencion_llm` con el depredador del momento.
ACCIONES_SIN_PARAMETROS = frozenset(
    {"beber", "comer", "descansar", "hablar", "tallar", "frotar_madera", "pintar"}
)


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
#: la mitad **y** su regeneración se espacia. Sin lo segundo, la capacidad
#: recortada no cambia el flujo de comida a largo plazo (la regeneración manda)
#: y la sequía no llega a vaciar los parches ni a hacerlos migrar; con lo
#: segundo, la comida local se agota de verdad y buscarla lejos paga.
PENALIZACION_SEQUIA = 2.0
FACTOR_REGENERACION_SEQUIA = 0.75
FACTOR_SED_SEQUIA = 1.1
#: Gradiente ambiental (eje 3): ciclo de estaciones y su efecto. En invierno la
#: regeneración baja a la mitad; con `ticks_por_estacion=0` no hay estaciones y
#: el mundo es el de la Fase 0.
ESTACIONES = ("primavera", "verano", "otono", "invierno")
REGENERACION_INVIERNO = 0.5
#: Un divergente experimenta con probabilidad proporcional a lo que se desvía
#: (máximo 15 % por tick) y completa el cruce la mitad de las veces.
PROB_INTENTO_DIVERGENTE = 0.15
PROB_COMPLETAR_COMBINACION = 0.5
#: Ticks mínimos entre dos propuestas de nodo al LLM (F2-006/F3-006). El
#: inventor no puede inundar el grafo, pero el nivel 1 real necesita más que
#: las cinco del catálogo: una propuesta cada 100 ticks ≈ 30 por partida de
#: 3000, y el motor valida cada cruce antes de inscribirlo.
PROPUESTA_CADA_TICKS = 100
#: Un muerto con esta edad o más es un anciano: su muerte entra en el diario.
UMBRAL_ANCIANO = 1500
#: Nodo del árbol que dispara cada hito de "primera vez" (concepto §10). Se ata
#: al nodo que representa el hecho y no al primer escalón de su rama: `gestos` no
#: es una palabra y `arte_rupestre` no es todavía un rito.
HITO_POR_NODO: dict[str, str] = {
    "observar_rayo": "primer_fuego",
    "proto_palabras": "primera_palabra",
    "ritual": "primer_rito",
    "caza_cooperativa": "primera_caza_grupo",
}


class Simulacion:
    """Estado de una partida: mundo + contadores que no viven en el mundo."""

    def __init__(
        self,
        mundo: Mundo,
        config: SimConfig | None = None,
        cola: ColaLLM | None = None,
        db: Path | None = None,
    ) -> None:
        self.mundo = mundo
        #: Capa LLM activa, si la hay. Sin ella el tick es el de siempre.
        self.cola = cola
        #: Espejo en SQLite (`run --db`). `None` = partida solo en RAM.
        self._repositorio = Repositorio(db) if db is not None else None
        #: Muestras de telemetría que se escriben con la partida (una por
        #: `ticks_telemetria`, más el cierre si cae fuera de intervalo).
        self._telemetria: list[dict[str, Any]] = []
        #: Memoria recuperable por similitud. Solo existe si hay capa LLM: sin
        #: LLM nadie consulta recuerdos y no se paga el coste de indexarlos.
        self.recuerdos = IndiceRecuerdos(embedder_por_defecto()) if cola is not None else None
        self._recuperaciones = 0
        self._peticion_id = 0
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
        #: Parches de comida que se han reubicado por agotamiento local (eje 3).
        self.migraciones = 0
        self._movidos = 0
        self._ms_acumulados = 0.0
        #: Lo que la tribu ha descubierto. Vive aquí y no en el mundo.
        self.grafo = Grafo()
        #: Historia de la tribu (concepto §10): hitos y diálogos, con su frase si
        #: el LLM la puso. La entrada se registra siempre; narrar es opcional.
        self.diario = Diario()
        #: Tipos de hito de "primera vez" ya anotados: cada uno entra una sola vez.
        self._hitos_vistos: set[str] = set()
        #: Quién ha descubierto una combinación y quién ha existido alguna vez.
        #: Con los dos conjuntos, `resumen` mide la supervivencia de cada grupo
        #: (eje 6: no se puede refinar lo que no se mide).
        self._descubridores: set[int] = set()
        self._registrados: set[int] = {individuo.id for individuo in mundo.individuos}
        #: Respuesta en la descendencia: el rasgo de todos los nacidos y el de
        #: los individuos que se reprodujeron (una vez por individuo). `S` es la
        #: media de los reproductores menos la media de la población inicial, que
        #: es el mismo punto de partida en calma y en crisis (los fundadores).
        self._div_inicial = _media_divergencia_inicial(mundo)
        self._div_nacidos: list[float] = []
        self._div_reproductores: dict[int, float] = {}
        #: Telemetría de la ronda 6: inventos por temperamento, imitaciones,
        #: longevidad de descubridores y conformistas. No decide nada.
        self._tramo_registrados: dict[str, int] = {"divergente": 0, "conformista": 0, "neutro": 0}
        for individuo in mundo.individuos:
            self._tramo_registrados[_tramo(individuo)] += 1
        self._descubrimientos_tramo: dict[str, int] = {
            "divergente": 0,
            "conformista": 0,
            "neutro": 0,
        }
        self._longevidad_descubridores: list[int] = []
        self._longevidad_conformistas: list[int] = []
        #: Utilidad situacional aplicada a cada nodo (eje 1): suma y número de
        #: ticks con el nodo activo, para publicar `utilidad_media` en `resumen`.
        self._utilidad_suma: dict[str, float] = {}
        self._utilidad_cuenta: dict[str, int] = {}
        #: Beneficios de cada vivo en el tick en curso; los usa el depredador.
        self._beneficios_tick: dict[int, modulo_beneficios.Beneficios] = {}
        #: Peticiones LLM aceptadas por individuo y máximos observados del
        #: presupuesto de pensamiento: cuántos pensaron en un tick y cuántas
        #: había en vuelo a la vez (concepto §10b).
        self._pensamientos: dict[int, int] = {}
        self._max_pensando_visto = 0
        self._max_en_vuelo_visto = 0
        #: Ticks de crisis seguidos; al llegar a `saliencia.TICKS_CRISIS` los
        #: supervivientes ganan el hito y el contador vuelve a cero.
        self._crisis_ticks = 0
        self._agua_tiles = {
            (x, y)
            for y, fila in enumerate(mundo.tiles)
            for x, tipo in enumerate(fila)
            if tipo == TipoTile.AGUA
        }
        #: Propuestas de nodo pedidas al LLM y cómo acabaron (F2-006). El motor
        #: las valida con `tribal.culture.propuestas`: aceptar no es deber del
        #: modelo, sino de la regla de plausibilidad.
        self.propuestas_solicitadas = 0
        self.propuestas_aceptadas = 0
        self.propuestas_rechazadas = 0
        self.propuestas_por_origen: dict[str, int] = {"combinacion": 0, "llm": 0}
        self._propuestas_rechazos: dict[str, int] = {}
        self._propuesta_pedida_tick = -PROPUESTA_CADA_TICKS
        #: Peso narrativo acumulado (F2-006): área bajo la curva de saliencia con
        #: el mismo olvido que la saliencia (`DECAIMIENTO`). A diferencia de la
        #: saliencia instantánea, no se satura en `SALIENCIA_MAX`, así que sirve
        #: para ordenar a los narradores sin empates arbitrarios.
        self._saliencia_acumulada: dict[int, float] = {}
        #: Nodo → tick en que se quedó sin portadores vivos. Lo consume
        #: `culture.transmision.sostener` para apagar la técnica si nadie la
        #: transmite (concepto §9).
        self._sin_portadores: dict[str, int] = {}

    def step(self) -> None:
        """Un tick: reloj, homeostasis, depredador y muertes, decisiones y crías.

        El orden importa: la homeostasis corre primero y luego el depredador
        muerde; la muerte se comprueba al final de esa secuencia. Si se
        comprobara antes del mordisco, la recuperación de salud del tick
        siguiente devolvería la vida a una presa que se quedó a 0.
        """
        inicio = time.perf_counter()

        self.mundo.tick += 1
        self.mundo.estacion = self._estacion()
        #: El protagonismo se gasta: un tick de olvido por individuo antes de
        #: que los hitos de este tick vuelvan a sumar. Determinista y sin azar.
        for individuo in self.mundo.individuos:
            saliencia.decaer(individuo)
        en_crisis = self._en_crisis()
        recursos.regenerar(
            self.mundo,
            PENALIZACION_SEQUIA if en_crisis else 1.0,
            self._factor_regeneracion(),
        )
        #: El gradiente ambiental va antes de decidir: quien mire el mundo este
        #: tick ya ve la comida donde está, no donde estaba.
        if self.config.migracion and en_crisis:
            # En calma el parche agotado se regenera **en el sitio**: la memoria
            # del conformista sigue siendo válida porque el recurso vuelve donde
            # estaba. Solo la sequía muda la comida, y entonces la copia envejece.
            # `migracion=false` apaga la migración en los dos regímenes.
            minimo, maximo = self._cooldowns_migracion()
            self.migraciones += len(
                recursos.migrar(
                    self.mundo,
                    umbral=self.config.umbral_agotamiento,
                    cooldown_min=minimo,
                    cooldown_max=maximo,
                )
            )

        #: La utilidad de cada técnica depende del mundo de este tick (escasez
        #: del recurso que explota, cuántos saben usarla y la estación), no de
        #: un +X % fijo, y no del temperamento (eje 1).
        estado = modulo_beneficios.situacion(self.mundo, estacion=self.mundo.estacion)
        utilidades = modulo_beneficios.utilidades(self.grafo, self.mundo, estado)
        for nodo_id, valor in utilidades.items():
            self._utilidad_suma[nodo_id] = self._utilidad_suma.get(nodo_id, 0.0) + valor
            self._utilidad_cuenta[nodo_id] = self._utilidad_cuenta.get(nodo_id, 0) + 1

        #: Beneficios que disfruta cada vivo este tick, según lo que sabe. La
        #: crisis no cambia el temperamento de nadie: cambia la capacidad de
        #: carga del mundo y, con ella, cuánto importa saber una técnica.
        beneficios: dict[int, modulo_beneficios.Beneficios] = {}
        for individuo in self.mundo.individuos:
            efecto = modulo_beneficios.conocidos(
                self.grafo, individuo.habilidades.conocidas, utilidades
            )
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

        self._beneficios_tick = beneficios
        modulo_depredador.mover(self.mundo, self._factor_dano)
        self._enterrar()
        # La técnica vive mientras quede quien la sepa: un nodo que lleva
        # `TICKS_SIN_PORTADOR` ticks sin portador se apaga, no se borra (§9).
        transmision.sostener(self.grafo, self.mundo, self._sin_portadores, self.mundo.tick)
        self._hito_crisis(en_crisis)

        self._encolar_dilema()

        descubierto = False
        for individuo in self.mundo.individuos:
            # Experimentar consume el tick: el divergente que prueba un cruce
            # no come ni bebe en ese tick (concepto §9b).
            if self._intentar_combinacion(individuo):
                continue
            efecto = beneficios[individuo.id]
            ya_se_movio = individuo.movido
            intencion = self._intencion_llm(individuo)
            accion = intencion if intencion is not None else instinto.elegir(individuo, self.mundo)
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
                lenguaje=self.grafo.activo("proto_palabras"),
            )
            if intencion is not None:
                if aplicada and self.cola is not None:
                    self.cola.registrar_aplicada()
                else:
                    # El modelo eligió algo que aquí no se puede hacer: manda el
                    # instinto. La intención no puede congelar al individuo.
                    accion = instinto.elegir(individuo, self.mundo)
                    aplicada = acciones.aplicar(
                        individuo,
                        self.mundo,
                        accion,
                        bonus_bayas=efecto.bayas,
                        bonus_caza=efecto.caza,
                        lenguaje=self.grafo.activo("proto_palabras"),
                    )
            # Explorar es viaje: el tick de búsqueda cuesta energía de más. Lo
            # paga la conducta, no el rasgo: un conformista que se ve obligado a
            # buscar lejos paga lo mismo.
            if aplicada and accion.explora:
                individuo.necesidades.energia = max(
                    0.0, individuo.necesidades.energia - acciones.COSTE_EXPLORAR
                )
            # Una enseñanza que no prende no debe clavar al individuo: deambula.
            if not aplicada and accion.nombre == "ensenar":
                acciones.aplicar(
                    individuo,
                    self.mundo,
                    instinto.deambular(individuo, self.mundo),
                    bonus_bayas=efecto.bayas,
                    bonus_caza=efecto.caza,
                    lenguaje=self.grafo.activo("proto_palabras"),
                )
            if individuo.movido and not ya_se_movio:
                self._movidos += 1
            # Hitos narrativos (§10b): enseñar una técnica y sacar a un herido
            # del pozo suman saliencia a quien los hace. El que la recibe no
            # gana peso por que le ayuden.
            if aplicada and accion.nombre == "ensenar":
                saliencia.subir(individuo, "ensenanza")
            elif aplicada and accion.nombre == "cuidar":
                saliencia.subir(individuo, "rescate")
            # Un nodo nuevo como mucho por tick: el árbol avanza al ritmo de la
            # tribu, no de golpe en el primer tick en que alguien come. Practicar
            # se cuenta siempre, descubra nodo o no: así se mide la imitación.
            if aplicada and self._practicar(individuo, accion.nombre, descubrir=not descubierto):
                descubierto = True

        self._proponer_si_toca()
        tradicion = tradiciones.evaluar(self.grafo, self.mundo.tick)
        if tradicion is not None:
            self.tradiciones += 1
            autor = next(
                (
                    individuo
                    for individuo in self.mundo.individuos
                    if individuo.id == tradicion.autor
                ),
                None,
            )
            if autor is not None:
                saliencia.subir(autor, "tradicion")
            if "primera_tradicion" not in self._hitos_vistos:
                self._hitos_vistos.add("primera_tradicion")
                self._hito("primera_tradicion", autor, f"{tradicion.titulo} ({tradicion.id})")
            self._registrar_recuerdo(
                tradicion.id,
                f"tradicion {tradicion.rama} {tradicion.id} {tradicion.titulo}",
            )
        tradiciones.sostener(self.grafo, self.mundo.tick)
        self._reproducir()
        self.agrupamiento_max = max(self.agrupamiento_max, self._junto_al_agua())

        #: Protagonismo acumulado del tick: la puerta F2→F3 mide la narración
        #: contra el área real bajo la curva, no contra un top instantáneo
        #: empatado en `SALIENCIA_MAX`. La saliencia instantánea decae; el área
        #: que mide el protagonismo de toda la partida no se descuenta.
        for individuo in self.mundo.individuos:
            self._saliencia_acumulada[individuo.id] = (
                self._saliencia_acumulada.get(individuo.id, 0.0) + individuo.saliencia
            )

        self._drenar()

        self._ms_acumulados += (time.perf_counter() - inicio) * 1000.0

        if self._repositorio is not None and self.mundo.tick % self.config.ticks_telemetria == 0:
            self._telemetria.append(self.muestra())
        if self._repositorio is not None and self.mundo.tick % self.config.ticks_guardado == 0:
            self._guardar()

    def _guardar(self) -> None:
        """Vuelca la partida entera a SQLite; no-op sin `--db`.

        Las muestras de telemetría se acumulan en `step` cada
        `ticks_telemetria` ticks y se escriben con cada volcado; no se muestrea
        aquí, para que un volcado no añada una fila fuera de intervalo.
        """
        if self._repositorio is None:
            return
        self._repositorio.guardar(
            self.mundo, self.grafo, self.diario, self._telemetria, config=self.config
        )

    def cerrar(self) -> None:
        """Vuelca el estado final y cierra la base. Sin `--db` no hace nada."""
        if self._repositorio is None:
            return
        # Si la partida termina fuera de intervalo, el estado final se conserva
        # como última muestra; si el tick ya está muestreado, no se duplica.
        if not self._telemetria or self._telemetria[-1]["tick"] != self.mundo.tick:
            self._telemetria.append(self.muestra())
        try:
            self._guardar()
        finally:
            self._repositorio.cerrar()
            self._repositorio = None

    def _encolar_dilema(self) -> None:
        """Hasta `max_pensando` peticiones por tick, por saliencia (concepto §10b).

        Un dilema es un conflicto de necesidades (sed y energía a la vez) o la
        salud por los suelos. Los individuos con dilema se ordenan por
        `(-saliencia, id)`: los de más peso narrativo piensan primero y, si el
        presupuesto se agota, los demás siguen por instinto y se reevalúan el
        tick siguiente (§3). El otro tope es el de la cola: `encolar` devuelve
        `False` cuando ya hay `max_en_vuelo` peticiones sin respuesta y ese tick
        no se ofrece ninguna más.
        """
        if self.cola is None:
            return
        con_dilema: list[tuple[Individuo, list[Accion]]] = []
        for individuo in self.mundo.individuos:
            opciones = modulo_candidatas.candidatas(individuo, self.mundo)
            if _hay_dilema(individuo, self.mundo, opciones):
                con_dilema.append((individuo, opciones))
        con_dilema.sort(key=lambda par: (-par[0].saliencia, par[0].id))

        encoladas = 0
        for individuo, opciones in con_dilema:
            if encoladas >= self.config.max_pensando:
                break
            nombres = tuple(opcion.nombre for opcion in opciones)
            contexto = modulo_candidatas.estado_para(individuo, self.mundo)
            #: GraphRAG ligero: los recuerdos relevantes viajan como datos del
            #: contexto, nunca dentro del hilo del LLM ni del render.
            contexto["memoria"] = [
                {"id": recuerdo_id, "score": round(score, 4)}
                for recuerdo_id, score in self._recuperar_memoria(individuo, nombres)
            ]
            peticion = Peticion(
                id=self._peticion_id + 1,
                tick=self.mundo.tick,
                individuo_id=individuo.id,
                contexto=contexto,
                candidatas=nombres,
                valida_hasta=self.mundo.tick + self.cola.ventana,
            )
            if not self.cola.encolar(peticion):
                break
            self._peticion_id += 1
            self._pensamientos[individuo.id] = self._pensamientos.get(individuo.id, 0) + 1
            encoladas += 1
            self._max_en_vuelo_visto = max(
                self._max_en_vuelo_visto, self.cola.estadisticas["en_vuelo"]
            )
        self._max_pensando_visto = max(self._max_pensando_visto, encoladas)

    def _recuperar_memoria(
        self, individuo: Individuo, acciones: tuple[str, ...]
    ) -> list[tuple[str | int, float]]:
        """Top-3 de recuerdos parecidos a la situación; vacío sin capa LLM.

        La consulta son las acciones candidatas y la estación: lo que un nodo
        de cultura comparte con el momento que se está decidiendo.
        """
        if self.recuerdos is None:
            return []
        consulta = f"{self.mundo.estacion or ''} {' '.join(acciones)}"
        self._recuperaciones += 1
        return self.recuerdos.buscar(consulta, k=3)

    def _registrar_recuerdo(self, id: str, texto: str) -> None:
        """Indexa un hito de cultura (árbol, combinación o tradición); no-op sin LLM."""
        if self.recuerdos is not None:
            self.recuerdos.agregar(id, texto)

    def _intencion_llm(self, individuo: Individuo) -> Accion | None:
        """Intención forzada si sigue dentro de su ventana; se consume al usarse.

        Solo se aceptan verbos sin parámetros: `Accion(nombre)` no lleva destino
        ni objetivo, y aplicar `moverse`/`ensenar`/`cuidar`/`huir` sin ellos
        lanzaría `ValueError` desde el bucle. Las candidatas de `_candidatas_llm`
        ya lo cumplen; el guard cierra la puerta a candidatas futuras.
        """
        if individuo.intencion_llm is None:
            return None
        nombre, hasta = individuo.intencion_llm
        individuo.intencion_llm = None
        if self.mundo.tick > hasta:
            return None
        if nombre == "huir":
            amenaza = instinto.depredador_cercano(individuo, self.mundo)
            if amenaza is None:  # la elección ya no vale: manda el instinto
                return None
            return Accion("huir", amenaza=(amenaza.x, amenaza.y))
        if nombre == "moverse":
            # El nombre viaja en la petición; el destino lo resuelve el instinto
            # con el mundo de este tick, igual que un paseo normal.
            return instinto.deambular(individuo, self.mundo)
        if nombre not in ACCIONES_SIN_PARAMETROS:
            return None
        return Accion(cast(NombreAccion, nombre))

    def _drenar(self) -> None:
        """Recoge lo que llegue y lo aplica como intención futura (paso 7 de §3).

        El orden no depende de la carrera: `drenar` ya devuelve por `(tick, id)`.
        Las narraciones llegan por su propia cola y se aplican a la entrada que
        las pidió, sin tocar la decisión: el diario ya tenía el hito.
        """
        if self.cola is None:
            return
        for texto in self.cola.drenar_textos():
            self.diario.narrar(texto.entrada, texto.texto)
        for propuesta in self.cola.drenar_propuestas(self.mundo.tick):
            self._aplicar_propuesta(propuesta)
        vivos = {individuo.id: individuo for individuo in self.mundo.individuos}
        for respuesta in self.cola.drenar(self.mundo.tick):
            if respuesta.decision is None:
                continue
            if respuesta.decision.dialogo:
                # Habló antes de morir: el diálogo se anota aunque su emisor ya
                # no esté entre los vivos del tick.
                self.diario.registrar(
                    respuesta.tick,
                    "dialogo",
                    individuo_id=respuesta.individuo_id,
                    texto=respuesta.decision.dialogo,
                )
            individuo = vivos.get(respuesta.individuo_id)
            if individuo is None:
                continue
            individuo.intencion_llm = (
                respuesta.decision.accion,
                respuesta.tick + self.cola.ventana,
            )

    def _proponer_si_toca(self) -> None:
        """Un turno de invención por reloj, no solo cuando un divergente prueba.

        Sin esto, una tribu pequeña con pocos divergentes pedía muy pocas
        propuestas y el nivel 1 dependía del censo. El motor sigue validando
        cada propuesta; el inventor es cualquier vivo, no siempre un divergente
        que haya gastado el tick experimentando.
        """
        if self.cola is None or not self._en_crisis():
            return
        if self.mundo.tick - self._propuesta_pedida_tick < PROPUESTA_CADA_TICKS:
            return
        inventor = next((individuo for individuo in self.mundo.individuos if individuo.vivo), None)
        if inventor is None:
            return
        self._propuesta_pedida_tick = self.mundo.tick
        self._solicitar_propuesta_llm(inventor)

    def _solicitar_propuesta_llm(self, individuo: Individuo) -> None:
        """Pide al inventor un cruce (F2-006/F3-006).

        La dispara el experimento de un divergente o el turno de invención por
        reloj; una petición por tick como mucho. El contexto son datos planos
        —ids, ramas y niveles—, nunca objetos del mundo.
        """
        if self.cola is None:
            return
        activos = sorted(
            (nodo for nodo in self.grafo.nodos.values() if nodo.estado == "activo"),
            key=lambda nodo: nodo.id,
        )
        contexto = {
            "seed": self.mundo.seed,
            "tick": self.mundo.tick,
            "individuo": individuo.id,
            "nodos_activos": [
                {"id": nodo.id, "rama": nodo.rama, "nivel": nodo.nivel} for nodo in activos
            ],
            "nodos": sorted(self.grafo.nodos),
            "catalogo": sorted(COMBINACIONES),
        }
        peticion = PeticionNodo(
            id=self._peticion_id + 1,
            tick=self.mundo.tick,
            individuo_id=individuo.id,
            contexto=contexto,
            valida_hasta=self.mundo.tick + self.cola.ventana,
        )
        if self.cola.solicitar_nodo(peticion):
            self._peticion_id += 1
            self.propuestas_solicitadas += 1

    def _aplicar_propuesta(self, respuesta: PropuestaNodo) -> None:
        """Valida la propuesta contra el grafo del tick y, si pasa, la inscribe.

        El motor no confía en el modelo: `propuestas.parsear` valida la forma y
        `propuestas.validar` decide la plausibilidad. Un rechazo no toca el
        grafo; solo suma un motivo al informe.
        """
        if respuesta.propuesta is None:
            self._rechazar_propuesta(respuesta.error or "sin propuesta")
            return
        try:
            propuesta = modulo_propuestas.parsear(respuesta.propuesta)
            nodo = modulo_propuestas.validar(
                propuesta,
                self.grafo,
                autor=respuesta.individuo_id,
                tick=respuesta.tick,
            )
        except (PropuestaInvalida, ValueError) as exc:
            self._rechazar_propuesta(str(exc))
            return

        self.propuestas_aceptadas += 1
        # Canal de la propuesta: catálogo curado o cruce nuevo del modelo. El
        # nodo es `combinacion` en ambos casos (nivel 1 de §8b); `llm` aquí
        # cuenta el canal, no un origen de nodo.
        canal = "combinacion" if nodo.id in COMBINACIONES else "llm"
        self.propuestas_por_origen[canal] = self.propuestas_por_origen.get(canal, 0) + 1
        self._registrar_nodo_propuesto(nodo, respuesta.individuo_id)

    def _registrar_nodo_propuesto(self, nodo: Nodo, autor_id: int) -> None:
        """Lo que cambia en la tribu cuando un nodo propuesto pasa la validación."""
        autor = next(
            (individuo for individuo in self.mundo.individuos if individuo.id == autor_id),
            None,
        )
        if nodo.origen == "combinacion":
            self.combinaciones_logradas += 1
        # El catálogo curado enseña su habilidad al descubridor, como siempre.
        # Las combinaciones dinámicas tienen efecto para quien ya sepa la
        # habilidad de su rama; no se la regalan al autor, para no alterar la
        # dinámica social de enseñar/cuidar que mide la puerta F2.
        if nodo.id in modulo_beneficios.HABILIDAD_POR_COMBINACION and autor is not None:
            autor.habilidades.aprender(modulo_beneficios.HABILIDAD_POR_COMBINACION[nodo.id])
        self._descubridores.add(autor_id)
        if autor is not None:
            self._descubrimientos_tramo[_tramo(autor)] += 1
            # El peso narrativo es del acto físico de probar un cruce del
            # catálogo. Las combinaciones dinámicas cuentan para el KPI, pero
            # no reparten saliencia: con 17-22 por partida convertirían el
            # top-3 de la puerta F2 en un empate.
            if nodo.id in COMBINACIONES:
                saliencia.subir(autor, "combinacion")
        self._registrar_recuerdo(
            nodo.id,
            f"{nodo.origen} {nodo.rama} {nodo.id} {nodo.titulo}",
        )

    def _rechazar_propuesta(self, motivo: str) -> None:
        """Cuenta un rechazo por su causa de primer nivel (`rama`, `duplicado`…)."""
        self.propuestas_rechazadas += 1
        clave = motivo.split(":", 1)[0].strip() or "otro"
        self._propuestas_rechazos[clave] = self._propuestas_rechazos.get(clave, 0) + 1

    @property
    def propuestas_llm(self) -> dict[str, Any]:
        """Resumen serializable del canal de propuestas de nodo (F2-006)."""
        return {
            "solicitadas": self.propuestas_solicitadas,
            "aceptadas": self.propuestas_aceptadas,
            "rechazadas": self.propuestas_rechazadas,
            "por_origen": dict(sorted(self.propuestas_por_origen.items())),
            "rechazos": dict(sorted(self._propuestas_rechazos.items())),
        }

    @property
    def saliencia_acumulada(self) -> dict[int, float]:
        """Área bajo la curva de saliencia por individuo (medida de la puerta F2)."""
        return dict(self._saliencia_acumulada)

    def _factor_dano(self, presa: Individuo) -> float:
        """Cuánto le muerde el depredador: la utilidad de vigilia del tick."""
        efecto = self._beneficios_tick.get(presa.id)
        return efecto.dano_depredador if efecto is not None else 1.0

    def _utilidad_media(self) -> dict[str, float]:
        """Media de la utilidad aplicada a cada nodo durante la corrida."""
        return {
            nodo_id: round(suma / self._utilidad_cuenta[nodo_id], 4)
            for nodo_id, suma in self._utilidad_suma.items()
            if self._utilidad_cuenta.get(nodo_id)
        }

    def _enterrar(self) -> None:
        """Retira a quien se quedó sin salud o sin edad. Un contador por individuo."""
        vivos = []
        for individuo in self.mundo.individuos:
            if individuo.necesidades.salud <= 0.0 or individuo.edad >= _longevidad(individuo):
                individuo.vivo = False
                self.muertes += 1
                if individuo.edad >= UMBRAL_ANCIANO:
                    self._hito("muerte_ancestro", individuo, f"edad {individuo.edad}")
                if individuo.id in self._descubridores:
                    self._longevidad_descubridores.append(individuo.edad)
                elif _tramo(individuo) == "conformista":
                    self._longevidad_conformistas.append(individuo.edad)
            else:
                vivos.append(individuo)
        self.mundo.individuos = vivos

    def _hito_crisis(self, en_crisis: bool) -> None:
        """Sobrevivir `TICKS_CRISIS` ticks de sequía seguidos suma saliencia.

        El hito es de bloque: lo ganan los vivos que llegaron al final del
        tramo, no cada uno por su cuenta, y el contador vuelve a cero. Fuera de
        crisis el contador se reinicia, así que hacen falta ticks seguidos.
        """
        if not en_crisis:
            self._crisis_ticks = 0
            return
        self._crisis_ticks += 1
        if self._crisis_ticks < saliencia.TICKS_CRISIS:
            return
        for individuo in self.mundo.individuos:
            saliencia.subir(individuo, "crisis")
        self._crisis_ticks = 0

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
        # La cría nace con energía que sale de la madre, y con exactamente lo que
        # la madre puede pagar: el balance es cero aunque se llegue aquí sin pasar
        # por el umbral. Así una cría no es comida gratis y la crisis no dispara
        # un baby-boom.
        aportado = min(ENERGIA_CRIA, madre.necesidades.energia)
        madre.necesidades.energia -= aportado
        hijo = Individuo(
            id=max(individuo.id for individuo in self.mundo.individuos) + 1,
            sexo="f" if self.nacimientos % 2 == 0 else "m",
            genoma=modulo_genoma.heredar(madre.genoma, padre.genoma, self.mundo.azar),
            necesidades=Necesidades(energia=aportado),
            x=x,
            y=y,
            # Las habilidades no se heredan: la cría solo trae lo de la tribu.
            habilidades=Habilidades.iniciales(),
            # El parche de la madre es el territorio que la cría conoce al nacer;
            # no es un rasgo, es la memoria del sitio donde creció.
            ultimo_recurso=madre.ultimo_recurso,
            ultimo_parche=madre.ultimo_parche,
            ultimo_parche_migracion=madre.ultimo_parche_migracion,
        )
        madre.cooldown_reproduccion = self.config.cooldown_reproduccion
        padre.cooldown_reproduccion = self.config.cooldown_reproduccion
        self.mundo.individuos.append(hijo)
        self._registrados.add(hijo.id)
        # Respuesta en la descendencia: rasgo del nacido y de quien lo tuvo.
        # Una vez por individuo reproductor, no por cría.
        self._div_nacidos.append(hijo.genoma.divergencia)
        self._tramo_registrados[_tramo(hijo)] += 1
        self._div_reproductores[madre.id] = madre.genoma.divergencia
        self._div_reproductores[padre.id] = padre.genoma.divergencia
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

    def _cooldowns_migracion(self) -> tuple[int, int]:
        """Espera (mínima, máxima) entre migraciones de un mismo parche.

        El máximo es `ticks_migracion` con el parche lleno; el mínimo, una
        quinta parte con el parche agotado. `recursos.migrar` interpola según la
        abundancia: no hay salto por régimen, la escasez acelera el entorno.
        """
        maximo = self.config.ticks_migracion
        return max(1, maximo // 5), maximo

    def _estacion(self) -> str | None:
        """Estación del tick, o `None` si la partida no tiene estaciones.

        Cicla en el orden de `ESTACIONES` cada `ticks_por_estacion` ticks. El
        reloj es el del mundo, así que dos partidas con la misma semilla y la
        misma config pasan por las mismas estaciones en los mismos ticks.
        """
        if self.config.ticks_por_estacion <= 0:
            return None
        return ESTACIONES[(self.mundo.tick // self.config.ticks_por_estacion) % len(ESTACIONES)]

    def _factor_regeneracion(self) -> float:
        """Ritmo de regeneración del tick: invierno y sequía lo espacian.

        En invierno la mitad (estación), y en crisis otro tanto sobre lo que
        quede: la sequía no solo recorta el techo, también hace que la reserva
        se rellene más despacio. Es el acoplamiento que convierte «buscar lejos»
        en una decisión con consecuencia.
        """
        factor = REGENERACION_INVIERNO if self.mundo.estacion == "invierno" else 1.0
        if self._en_crisis():
            factor *= FACTOR_REGENERACION_SEQUIA
        return factor

    def _supervivencia(self, ids: set[int]) -> float:
        """Fracción de esos ids —que alguna vez vivieron— que sigue viva."""
        if not ids:
            return 0.0
        vivos = {individuo.id for individuo in self.mundo.individuos}
        return len(ids & vivos) / len(ids)

    def _diferencial_seleccion(self) -> float:
        """Supervivencia de los descubridores menos la de los demás.

        La ventaja del descubridor, si existe, viene de la habilidad que
        aprendió al descubrir (y de que su técnica sirva bajo escasez), no del
        rasgo: por eso el diferencial compara conducta —descubrir— y no
        temperamento. Sin descubridores o sin grupo de comparación vale 0.0.
        """
        resto = self._registrados - self._descubridores
        if not self._descubridores or not resto:
            return 0.0
        return self._supervivencia(self._descubridores) - self._supervivencia(resto)

    def _intentar_combinacion(self, individuo: Individuo) -> bool:
        """Un divergente gasta el tick probando un cruce. True si lo intentó.

        Solo pasa en crisis (concepto §9b y §13): en calma la tradición basta y
        el motor no gasta ticks en experimentar, así que sin crisis no aparece
        ningún nodo `combinacion`. El catálogo tiene prioridad: si hay un cruce
        con sus dos nodos activos, se intenta como siempre. Después —o cuando el
        catálogo ya no tiene candidatos— el experimento se ofrece al inventor
        (`_solicitar_propuesta_llm`), que propone un nodo nuevo que el motor
        valida (F2-006). Si el cruce no cuaja, el intento se cuenta igual,
        porque el experimento ocurrió. Descubrirlo enseña al autor la habilidad
        de la técnica: el nodo es de la tribu, pero la ventaja es de quien la
        sabe usar (concepto §9b).
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
        # Sin catálogo pendiente solo se experimenta si el inventor tiene turno:
        # si no, el divergente come o bebe como cualquier otro (la dinámica de
        # F1 sin LLM no cambia).
        puede_proponer = (
            self.cola is not None
            and self.mundo.tick - self._propuesta_pedida_tick >= PROPUESTA_CADA_TICKS
        )
        if not candidatas and not puede_proponer:
            return False
        exceso = individuo.genoma.divergencia - modulo_genoma.UMBRAL_DIVERGENTE
        margen = modulo_genoma.DIVERGENCIA_MAX - modulo_genoma.UMBRAL_DIVERGENTE
        if self.mundo.azar.random() >= PROB_INTENTO_DIVERGENTE * exceso / margen:
            return False

        self.intentos_divergentes += 1
        if candidatas:
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
                self._descubridores.add(individuo.id)
                self._descubrimientos_tramo[_tramo(individuo)] += 1
                # Hito narrativo: el cruce es de la tribu, pero el peso es de
                # quien lo hizo (concepto §10b). No depende de su divergencia:
                # la experimentación sí, la saliencia no.
                saliencia.subir(individuo, "combinacion")
                self._registrar_recuerdo(
                    candidata.id,
                    f"combinacion {candidata.rama} {candidata.id} {candidata.titulo}",
                )

        # El inventor propone lo que el catálogo no tiene. Una petición cada
        # `PROPUESTA_CADA_TICKS` como mucho, y solo cuando el experimento ya
        # ocurrió de verdad: el canal tiene ritmo, no inunda el grafo.
        if puede_proponer:
            self._propuesta_pedida_tick = self.mundo.tick
            self._solicitar_propuesta_llm(individuo)
        return True

    def _practicar(self, individuo: Individuo, accion: str, *, descubrir: bool) -> bool:
        """Registra la práctica de `accion` y, si toca, avanza su rama del árbol.

        Solo cuenta quien **sabe** la habilidad de la práctica, si la práctica
        exige una (concepto §5: la cultura sale de lo que ya se sabe hacer); en
        las que se definen por situación, el verbo ya comprobó la condición.
        El uso se anota en **todos** los nodos activos de la rama —la técnica que
        está funcionando y lo que la sostiene— y un conformista que la usa sin
        haberla descubierto suma una imitación (§9b). Anotarlo solo en la punta
        dejaba sin imitar cada escalón en cuanto la rama avanzaba, y las
        tradiciones (nivel 2) no pasaban de una por rama. El nodo nuevo nace con
        su origen escrito por `Grafo.descubrir`, que valida los prerrequisitos.
        """
        practica = PRACTICAS.get(accion)
        if practica is None:
            return False
        if practica.habilidad is not None and not individuo.habilidades.sabe(practica.habilidad):
            return False
        rama = practica.rama
        conformista = modulo_genoma.temperamento(individuo.genoma) == "conformista"
        for en_uso in self.grafo.activos_en_rama(rama):
            self.grafo.registrar_uso(
                en_uso.id,
                usuario=individuo.id,
                es_conformista=conformista,
                tick=self.mundo.tick,
            )
        if not descubrir:
            return False
        nodo = self.grafo.avanzar(rama, autor=individuo.id, tick=self.mundo.tick)
        if nodo is None:
            return False
        # Hito narrativo: ser el primero de la tribu en un escalón de la rama
        # —el primer fuego, la primera palabra, el primer líder— (concepto §10b).
        saliencia.subir(individuo, "primer_nodo")
        # Efecto cultural de una tradición viva: el descubrimiento de su rama
        # pesa un poco más en la memoria del grupo.
        if tradiciones.activa_en(self.grafo, rama):
            saliencia.subir(individuo, "tradicion_practica")
        self._hito_nodo(nodo, individuo)
        self._registrar_recuerdo(
            nodo.id, f"{nodo.rama} {nodo.id} {nodo.titulo} practicando {accion}"
        )
        return True

    def _hito_nodo(self, nodo: Nodo, individuo: Individuo) -> None:
        """El nodo que representa el hecho —fuego, palabra, rito o caza— (§10)."""
        tipo = HITO_POR_NODO.get(nodo.id)
        if tipo is None or tipo in self._hitos_vistos:
            return
        self._hitos_vistos.add(tipo)
        self._hito(tipo, individuo, f"{nodo.titulo} ({nodo.id})")

    def _narrador(self, sujeto: Individuo | None) -> int | None:
        """Quién cuenta el hito: el sujeto si es saliente, o el más saliente.

        Concepto §10b: la saliencia concentra la narración. El peso es el área
        con olvido **hasta este tick**, el mismo criterio con el que la puerta
        ordena el top-3 final: si se usara solo el valor instantáneo, el techo
        `SALIENCIA_MAX` empataría a media tribu y el cronista cambiaría a
        cualquier recién llegado. Solo se narra si algún vivo tiene peso
        positivo; el sujeto cuenta su propio hito si está en el top-3 y, si no,
        lo cuenta el individuo con más peso.
        """
        if self.cola is None:
            return None
        candidatos = [
            individuo
            for individuo in self.mundo.individuos
            if individuo.vivo and self._peso_narrativo(individuo) > 0.0
        ]
        if not candidatos:
            return None
        top3 = sorted(
            candidatos, key=lambda individuo: (-self._peso_narrativo(individuo), individuo.id)
        )[:3]
        if sujeto is not None and any(individuo.id == sujeto.id for individuo in top3):
            return sujeto.id
        return top3[0].id

    def _peso_narrativo(self, individuo: Individuo) -> float:
        """Área acumulada hasta el tick anterior, más la saliencia de este."""
        return self._saliencia_acumulada.get(individuo.id, 0.0) + individuo.saliencia

    def _hito(self, tipo: str, individuo: Individuo | None, detalle: str) -> int:
        """Anota el hito en el diario y pide su frase. Nunca espera al LLM.

        La entrada existe con o sin modelo: la narración es un adorno opcional y
        llega después, cuando la cola la resuelve. `narrador_id` lo elige la
        saliencia (`_narrador`); sin nadie con peso no se pide frase y la
        entrada queda `narrada=false`.
        """
        narrador = self._narrador(individuo)
        entrada = self.diario.registrar(
            self.mundo.tick,
            tipo,
            individuo_id=None if individuo is None else individuo.id,
            narrador_id=narrador,
        )
        if (
            self.cola is not None
            and narrador is not None
            and not self.cola.narrar(
                PeticionNarracion(
                    entrada=entrada,
                    tick=self.mundo.tick,
                    hito=tipo,
                    contexto={
                        "seed": self.mundo.seed,
                        "tick": self.mundo.tick,
                        "poblacion": len(self.mundo.individuos),
                        "estacion": self.mundo.estacion,
                        "detalle": detalle,
                        "narrador": narrador,
                    },
                )
            )
        ):
            # Sin hueco en la cola: la entrada se queda sin cronista.
            self.diario.entradas[entrada].narrador_id = None
        return entrada

    @property
    def poblacion(self) -> int:
        return len(self.mundo.individuos)

    @property
    def ms_tick_medio(self) -> float:
        return self._ms_acumulados / self.mundo.tick if self.mundo.tick else 0.0

    def muestra(self) -> dict[str, Any]:
        """Foto del estado para la telemetría por intervalo.

        Una fila por muestra, no por tick: es lo que publica `report telemetry`
        y lo que la Fase 3 escribirá en la tabla `telemetria`. La última
        muestra de una corrida coincide con su `resumen()`.
        """
        vivos = self.mundo.individuos
        temperamentos = [modulo_genoma.temperamento(individuo.genoma) for individuo in vivos]
        media_energia = (
            sum(individuo.necesidades.energia for individuo in vivos) / len(vivos) if vivos else 0.0
        )
        media_sed = (
            sum(individuo.necesidades.sed for individuo in vivos) / len(vivos) if vivos else 0.0
        )
        muestra: dict[str, Any] = {
            "tick": self.mundo.tick,
            "poblacion": len(vivos),
            "divergentes": temperamentos.count("divergente"),
            "conformistas": temperamentos.count("conformista"),
            "neutros": temperamentos.count("neutro"),
            "nodos": len(self.grafo.nodos),
            "aristas": len(self.grafo.aristas),
            "media_energia": round(media_energia, 2),
            "media_sed": round(media_sed, 2),
        }
        if self.cola is not None:
            estadisticas = self.cola.estadisticas
            muestra["llm"] = {
                "peticiones": estadisticas["enviadas"],
                "aplicadas": estadisticas["aplicadas"],
                "descartadas": estadisticas["descartadas"],
                "fallos": estadisticas["fallos"],
                "latencia_ms_media": self.cola.latencia_ms_media,
            }
        return muestra

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
        estado = modulo_beneficios.situacion(self.mundo, estacion=self.mundo.estacion)
        div_nacidos = sum(self._div_nacidos) / len(self._div_nacidos) if self._div_nacidos else 0.0
        div_reproductores = (
            sum(self._div_reproductores.values()) / len(self._div_reproductores)
            if self._div_reproductores
            else 0.0
        )
        seleccion_s = div_reproductores - self._div_inicial if self._div_reproductores else 0.0
        div_media_vivos = (
            sum(individuo.genoma.divergencia for individuo in vivos) / len(vivos) if vivos else 0.0
        )
        descubrimientos = sum(
            1 for nodo in self.grafo.nodos.values() if nodo.origen == "combinacion"
        )
        imitaciones = sum(self.grafo.imitado.values())
        tasa_imitacion = imitaciones / descubrimientos if descubrimientos else 0.0
        registrados_div = self._tramo_registrados["divergente"]
        registrados_conf = self._tramo_registrados["conformista"]
        desc_div = self._descubrimientos_tramo["divergente"]
        desc_conf = self._descubrimientos_tramo["conformista"]
        longevidad_div = (
            sum(self._longevidad_descubridores) / len(self._longevidad_descubridores)
            if self._longevidad_descubridores
            else 0.0
        )
        longevidad_conf = (
            sum(self._longevidad_conformistas) / len(self._longevidad_conformistas)
            if self._longevidad_conformistas
            else 0.0
        )
        datos: dict[str, Any] = {
            "seed": self.mundo.seed,
            "ticks": self.mundo.tick,
            "poblacion_inicial": self.poblacion_inicial,
            "poblacion_final": len(vivos),
            "nacimientos": self.nacimientos,
            "coste_reproduccion": ENERGIA_CRIA,
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
            #: Respuesta en la descendencia (medida primaria de F1-005): rasgo
            #: medio de los nacidos, de los reproductores y diferencial S contra
            #: la población inicial del brazo.
            "mean_divergencia_inicial": round(self._div_inicial, 4),
            "mean_divergencia_nacidos": round(div_nacidos, 4),
            "mean_divergencia_reproductores": round(div_reproductores, 4),
            "reproductores": len(self._div_reproductores),
            "S": round(seleccion_s, 4),
            "S_fecundidad": round(seleccion_s, 4),
            "S_viabilidad": round(div_media_vivos - self._div_inicial, 4) if vivos else 0.0,
            #: Telemetría de la ronda 6: invención e imitación por temperamento y
            #: longevidad. Las tasas se publican por individuo registrado.
            "descubrimientos": descubrimientos,
            "descubrimientos_divergentes": desc_div,
            "descubrimientos_conformistas": desc_conf,
            "divergentes_registrados": registrados_div,
            "conformistas_registrados": registrados_conf,
            "tasa_descubrimiento_divergente": round(desc_div / max(1, registrados_div), 4),
            "tasa_descubrimiento_conformista": round(desc_conf / max(1, registrados_conf), 4),
            "tasa_imitacion": round(tasa_imitacion, 4),
            "longevidad_media_descubridores": round(longevidad_div, 1),
            "longevidad_media_conformistas": round(longevidad_conf, 1),
            "muertes_descubridores": len(self._longevidad_descubridores),
            "muertes_conformistas": len(self._longevidad_conformistas),
            "intentos_divergentes": self.intentos_divergentes,
            "combinaciones_logradas": self.combinaciones_logradas,
            "descubridores": sorted(self._descubridores),
            "supervivencia_descubridores": round(self._supervivencia(self._descubridores), 3),
            "supervivencia_no_descubridores": round(
                self._supervivencia(self._registrados - self._descubridores), 3
            ),
            "diferencial_seleccion": round(self._diferencial_seleccion(), 3),
            "tradiciones": self.tradiciones,
            "imitaciones": imitaciones,
            "beneficios": modulo_beneficios.activos(self.grafo, self.mundo, estado).a_json(),
            "utilidad_media": self._utilidad_media(),
            **estado.a_json(),
            #: Gradiente ambiental (eje 3): estación, parches con su abundancia y
            #: migraciones. Sin `estacion` no hay ciclo; los parches están siempre.
            "parches": self._parches(),
            "migraciones": self.migraciones,
            **self.grafo.a_json(),
            #: Memoria recuperable: cuántos hitos hay indexados y cuántas
            #: consultas hizo el tick al construir contextos de LLM.
            "memoria": {
                "recuerdos": 0 if self.recuerdos is None else len(self.recuerdos),
                "recuperaciones": self._recuperaciones,
            },
            #: Protagonismo emergente (concepto §10b): quién ha ganado peso
            #: narrativo y cuántas veces ha pensado. Se publica siempre porque
            #: la saliencia no depende de que haya LLM; sin cola, `pensamientos`
            #: está vacío. Los `max_*` acotan el presupuesto de pensamiento.
            "saliencia": self._saliencia_json(),
            #: Diario (concepto §10): el hito se registra siempre; `narradas`
            #: cuenta las frases que puso el LLM y `dialogos` lo que dijo alguien.
            "diario": {
                **self.diario.a_json(),
                "ultimas": [entrada.a_json() for entrada in self.diario.ultimas(3)],
            },
            "config": self.config.a_json(),
        }
        if self.cola is not None:
            estadisticas = self.cola.estadisticas
            datos["llm"] = {
                "peticiones": estadisticas["enviadas"],
                "aplicadas": estadisticas["aplicadas"],
                "descartadas": estadisticas["descartadas"],
                "fallos": estadisticas["fallos"],
                "corregidas": estadisticas["corregidas"],
                "en_vuelo": estadisticas["en_vuelo"],
            }
        return datos

    def _saliencia_json(self) -> dict[str, Any]:
        """Top-3 de peso narrativo y peticiones pensadas por individuo (§10b).

        `top` sale de los vivos con saliencia positiva, ordenado por valor y, a
        igualdad, por id. `pensamientos` acumula las peticiones aceptadas —vacío
        sin capa LLM— y los dos `max_*` son la cota observada del presupuesto:
        individuos que pensaron en un mismo tick y peticiones en vuelo (este
        último solo puede ser > 0 con la cola asíncrona; la síncrona resuelve
        dentro de `encolar`).
        """
        con_peso = sorted(
            (individuo for individuo in self.mundo.individuos if individuo.saliencia > 0.0),
            key=lambda individuo: (-individuo.saliencia, individuo.id),
        )
        return {
            "top": [(individuo.id, round(individuo.saliencia, 3)) for individuo in con_peso[:3]],
            "pensamientos": dict(sorted(self._pensamientos.items())),
            "max_pensando": self._max_pensando_visto,
            "max_en_vuelo": self._max_en_vuelo_visto,
        }

    def _parches(self) -> list[dict[str, Any]]:
        """Cada parche con su tipo, su abundancia y si está activo (da de comer)."""
        resumen = []
        for parche in self.mundo.parches:
            abundancia = recursos.abundancia(self.mundo, parche)
            resumen.append(
                {
                    "id": parche.id,
                    "tipo": parche.tipo.name.lower(),
                    "activo": abundancia >= self.config.umbral_agotamiento,
                    "abundancia": round(abundancia, 3),
                    "x": round(parche.x, 1),
                    "y": round(parche.y, 1),
                }
            )
        return resumen


def crear(
    seed: int,
    individuos: int = 12,
    config: SimConfig | None = None,
    cola: ColaLLM | None = None,
    db: Path | None = None,
) -> Simulacion:
    """Partida nueva. `seed` e `individuos` mandan sobre lo que diga `config`."""
    if config is None:
        config = SimConfig(seed=seed, individuos=individuos)
    else:
        config = replace(config, seed=seed, individuos=individuos)
    return Simulacion(modulo_mundo.crear(seed, individuos, config=config), config, cola, db)


def run(
    ticks: int,
    seed: int,
    headless: bool,
    individuos: int = 12,
    config: SimConfig | None = None,
    cola: ColaLLM | None = None,
    db: Path | None = None,
) -> Simulacion:
    """Corre la partida `ticks` ticks (`0` = sin límite) y devuelve la simulación.

    En modo ventana el límite lo pone el usuario con ESC o cerrando la ventana;
    `ticks` sigue sirviendo como tope opcional. Si hay cola LLM, se cierra aquí:
    al volver no queda hilo vivo y `resumen()` publica `en_vuelo` a 0. Con `db`
    la partida se vuelca al cerrar (y cada `config.ticks_guardado` ticks).
    """
    simulacion = crear(seed, individuos, config, cola, db)
    try:
        if headless:
            for _ in range(ticks):
                simulacion.step()
            return simulacion

        from tribal.ui import app  # import perezoso: Pygame no entra en el motor

        app.bucle(simulacion, ticks)
        return simulacion
    finally:
        if cola is not None:
            cola.cerrar()
        simulacion.cerrar()


def run_muestreado(
    ticks: int,
    seed: int,
    intervalo: int,
    individuos: int = 12,
    config: SimConfig | None = None,
    cola: ColaLLM | None = None,
) -> tuple[Simulacion, list[dict[str, Any]]]:
    """Corre la partida y toma una muestra cada `intervalo` ticks.

    El último tramo puede ser más corto si `ticks` no es múltiplo de
    `intervalo`; así la última muestra es siempre el estado final y coincide
    con el `resumen()` de la misma corrida. Si hay cola LLM, se cierra al
    terminar: `report telemetry` no deja hilo vivo.
    """
    if intervalo <= 0:
        raise ValueError("intervalo debe ser mayor que 0")
    simulacion = crear(seed, individuos, config, cola)
    muestras: list[dict[str, Any]] = []
    try:
        restantes = ticks
        while restantes > 0:
            paso = min(intervalo, restantes)
            for _ in range(paso):
                simulacion.step()
            restantes -= paso
            muestras.append(simulacion.muestra())
        return simulacion, muestras
    finally:
        if cola is not None:
            cola.cerrar()


def _tramo(individuo: Individuo) -> str:
    """Temperamento para telemetría (no decide nada del motor)."""
    return modulo_genoma.temperamento(individuo.genoma)


def _hay_dilema(
    individuo: Individuo,
    mundo: Mundo,
    opciones: list[Accion] | None = None,
) -> bool:
    """True si el estado merece inferencia y deja al menos dos candidatas.

    El filtro de qué se ofrece vive en `tribal.llm.candidatas`; si el mundo no
    deja dos acciones viables, no se pide decisión: el instinto cubre el tick.
    `opciones` evita recalcular la lista cuando el llamante ya la tiene.
    """
    nec = individuo.necesidades
    if not (
        (necesidades.sed_critica(nec) and necesidades.energia_baja(nec))
        or necesidades.salud_critica(nec)
    ):
        return False
    if opciones is None:
        opciones = modulo_candidatas.candidatas(individuo, mundo)
    return len(opciones) >= 2


def _media_divergencia_inicial(mundo: Mundo) -> float:
    """Media del rasgo en los fundadores: línea base de S (medición, no conducta)."""
    if not mundo.individuos:
        return 0.0
    return sum(individuo.genoma.divergencia for individuo in mundo.individuos) / len(
        mundo.individuos
    )


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
