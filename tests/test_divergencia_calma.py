"""DIVERGENCIA-002: la divergencia decide conducta, nunca aptitud.

Cuatro contratos:

1. En calma el divergente explora y se aparta; el conformista se queda cerca.
2. El rasgo no recibe ventaja directa, y hay tests que lo vigilan uno a uno:
   bocado (`comer`), sed al beber, umbral de cría, homeostasis y genoma
   congelado; más una lista blanca de los únicos sitios que leen el rasgo.
3. La selección se mide por conducta: `descubridores` y `diferencial_seleccion`.
4. Un divergente que no descubre nada rinde igual que un conformista.
"""

from __future__ import annotations

import ast
import math
import random
from pathlib import Path

import pytest

from tribal.agents import instinto
from tribal.config import SimConfig
from tribal.core import acciones
from tribal.core.genoma import Genoma
from tribal.core.habilidades import Habilidades
from tribal.core.modelos import (
    Individuo,
    Mundo,
    Necesidades,
    Recurso,
    TipoRecurso,
    TipoTile,
)
from tribal.culture import beneficios
from tribal.culture.arbol import ARBOL
from tribal.culture.combinaciones import COMBINACIONES
from tribal.culture.grafo import Grafo
from tribal.sim import UMBRAL_REPRODUCCION, Simulacion, crear, run

SEMILLA = 42
#: 2000 ticks: la ventana en la que los descubridores de una partida corta
#: siguen vivos. Con 3000+ la vejez borra el grupo y no mide conducta.
TICKS_CRISIS = 2000
#: Adulto adulto, sin hambre ni sed: el tramo ocioso, donde se deambula.
POSICION = (30.0, 17.0)


def _pradera(seed: int, *individuos: Individuo) -> Mundo:
    """Mapa de 60x34 de hierba, sin recursos ni depredadores."""
    tiles = [[TipoTile.HIERBA for _ in range(60)] for _ in range(34)]
    return Mundo(
        ancho=60,
        alto=34,
        tiles=tiles,
        recursos=[],
        individuos=list(individuos),
        azar=random.Random(seed),
    )


def _errante(id_: int, divergencia: float, x: float, y: float) -> Individuo:
    return Individuo(
        id=id_,
        sexo="m",
        genoma=Genoma(divergencia=divergencia),
        necesidades=Necesidades(energia=100.0, sed=0.0),
        x=x,
        y=y,
        habilidades=Habilidades(),
    )


def _con_hambre(id_: int) -> Individuo:
    return Individuo(
        id=id_,
        sexo="m",
        genoma=Genoma(divergencia=0.5),
        necesidades=Necesidades(energia=40.0),
        x=1.0,
        y=1.0,
        habilidades=Habilidades(),
    )


def _mundo_con_comida(*individuos: Individuo) -> Mundo:
    """Seis por seis de hierba con bayas de sobra en (1, 1)."""
    tiles = [[TipoTile.HIERBA for _ in range(6)] for _ in range(6)]
    bayas = Recurso(
        id=1,
        tipo=TipoRecurso.BAYAS,
        x=1,
        y=1,
        cantidad=8,
        capacidad=8,
        regeneracion=420,
        alcance=1.5,
    )
    return Mundo(
        ancho=6,
        alto=6,
        tiles=tiles,
        recursos=[bayas],
        individuos=list(individuos),
        azar=random.Random(0),
    )


def _grafo_con(*nodo_ids: str) -> Grafo:
    """Grafo con esos nodos activos y todos sus prerrequisitos."""
    grafo = Grafo()

    def activar(nodo_id: str) -> None:
        if grafo.activo(nodo_id):
            return
        plantilla = ARBOL.get(nodo_id) or COMBINACIONES[nodo_id]
        for requisito in plantilla.requisitos:
            activar(requisito)
        grafo.descubrir(nodo_id, autor=1, tick=1)

    for nodo_id in nodo_ids:
        activar(nodo_id)
    return grafo


def _radio_explorado(semilla: int, divergencia: float, ticks: int = 120) -> float:
    """Mayor distancia al punto de partida de un individuo solo, mismo mapa."""
    individuo = _errante(1, divergencia, *POSICION)
    simulacion = Simulacion(_pradera(semilla, individuo), SimConfig(seed=semilla, individuos=1))
    radio = 0.0
    for _ in range(ticks):
        simulacion.step()
        radio = max(radio, math.hypot(individuo.x - POSICION[0], individuo.y - POSICION[1]))
    return radio


# --- 1. Conducta en calma -------------------------------------------------


def test_el_radio_de_deambular_crece_con_la_divergencia() -> None:
    conformista = _errante(1, 0.0, 10.0, 10.0)
    neutro = _errante(2, 0.5, 10.0, 10.0)
    divergente = _errante(3, 1.0, 10.0, 10.0)

    assert 2.0 <= instinto.radio_deambular(conformista) <= 3.0
    assert 4.0 <= instinto.radio_deambular(neutro) <= 6.0
    assert 8.0 <= instinto.radio_deambular(divergente) <= 12.0
    assert (
        instinto.radio_deambular(conformista)
        < instinto.radio_deambular(neutro)
        < instinto.radio_deambular(divergente)
    )


def test_en_calma_el_divergente_explora_mas_radio_que_el_conformista() -> None:
    """Ocho semillas, misma partida: solo cambia el rasgo. Se compara la media."""
    semillas = range(1, 9)
    conformista = sum(_radio_explorado(s, 0.1) for s in semillas) / 8
    divergente = sum(_radio_explorado(s, 0.9) for s in semillas) / 8

    assert divergente > 8.0, f"el divergente no explora ({divergente:.2f} tiles)"
    assert conformista < 8.0, f"el conformista se va lejos ({conformista:.2f} tiles)"
    assert divergente > 1.4 * conformista


def test_el_paseo_en_calma_es_determinista() -> None:
    assert _radio_explorado(SEMILLA, 0.9) == _radio_explorado(SEMILLA, 0.9)
    assert _radio_explorado(SEMILLA, 0.1) == _radio_explorado(SEMILLA, 0.1)


def test_el_sesgo_de_cohesion_es_opuesto_en_el_divergente() -> None:
    """El conformista apunta al vecino; el divergente, lejos de él.

    Se piden 64 destinos sin aplicarlos, así que las posiciones no cambian: lo
    que se mide es la preferencia, no su efecto acumulado.
    """
    vecino = _errante(9, 0.5, 20.0, 17.0)

    def distancia_media(divergencia: float) -> float:
        individuo = _errante(1, divergencia, 15.0, 17.0)
        mundo = _pradera(SEMILLA, individuo, vecino)
        distancias = []
        for _ in range(64):
            individuo.paseo = None
            destino = instinto.deambular(individuo, mundo).destino
            assert destino is not None
            distancias.append(math.hypot(destino[0] - vecino.x, destino[1] - vecino.y))
        return sum(distancias) / len(distancias)

    assert distancia_media(0.9) > distancia_media(0.1)


def test_la_urgencia_manda_igual_en_los_dos_temperamentos() -> None:
    """Con sed crítica, el rasgo no cambia la acción: los dos van al agua."""
    tiles = [[TipoTile.HIERBA for _ in range(12)] for _ in range(12)]
    agua = Recurso(
        id=1,
        tipo=TipoRecurso.AGUA,
        x=6,
        y=6,
        cantidad=40,
        capacidad=40,
        regeneracion=10,
        alcance=3.0,
    )

    def accion(divergencia: float) -> acciones.Accion:
        individuo = _errante(1, divergencia, 1.0, 1.0)
        individuo.necesidades.sed = 99.0
        mundo = Mundo(
            ancho=12,
            alto=12,
            tiles=tiles,
            recursos=[agua],
            individuos=[individuo],
            azar=random.Random(0),
        )
        return instinto.elegir(individuo, mundo)

    assert accion(0.9) == accion(0.1) == acciones.Accion("moverse", destino=(6.0, 6.0))


# --- 2. Sin ventaja directa (contrato de código) --------------------------

RAIZ = Path(__file__).resolve().parents[1]
MODULOS_SIN_VENTAJA = (
    "tribal/core/acciones.py",
    "tribal/core/modelos.py",
    "tribal/core/genoma.py",
    "tribal/agents/necesidades.py",
    "tribal/sim.py",
)
#: Canales de "fitness por decreto" que borró DIVERGENCIA-001. Si reaparecen,
#: este test falla: un rasgo no puede dar comida, sed ni crías.
NOMBRES_PROHIBIDOS = (
    "PENALIZACION_CONFORMISTA",
    "VENTAJA_REPRODUCTIVA_DIVERGENTE",
    "_plasmar_divergencia",
    "_moldear_divergencia",
)
#: En una misma línea, el rasgo y una vía de aptitud no pueden convivir.
TOKENS_DE_RECURSO = ("factor_sed", "tasa_sed", "bocado", "ventaja", "plasticidad")
#: Lista blanca de los únicos sitios que pueden *leer* `divergencia`. Leerlo en
#: cualquier otro sitio es un canal de aptitud, sea una comparación, un umbral o
#: un `+=`: aquí no se vigilan nombres, se vigila el acceso al dato.
SITIOS_CON_DIVERGENCIA = {
    # Clasificación del temperamento (divergente / neutro / conformista).
    ("tribal/core/genoma.py", "temperamento"),
    # Herencia: se copia el gen del padre y de la madre, no decide nada.
    ("tribal/core/genoma.py", "heredar"),
    # Conducta en calma: radio del paseo y sesgo de cohesión.
    ("tribal/agents/instinto.py", "radio_deambular"),
    ("tribal/agents/instinto.py", "_punto_errante"),
    # Conducta en crisis: quién gasta el tick experimentando un cruce.
    ("tribal/sim.py", "_intentar_combinacion"),
}


def _lecturas_de_divergencia(ruta: Path) -> list[tuple[str, int]]:
    """`(función, línea)` de cada lectura del atributo `divergencia` del módulo."""
    lecturas: list[tuple[str, int]] = []

    def recorrer(nodo: ast.AST, funcion: str) -> None:
        for hijo in ast.iter_child_nodes(nodo):
            siguiente = (
                hijo.name if isinstance(hijo, (ast.FunctionDef, ast.AsyncFunctionDef)) else funcion
            )
            if isinstance(hijo, ast.Attribute) and hijo.attr == "divergencia":
                lecturas.append((funcion, hijo.lineno))
            recorrer(hijo, siguiente)

    recorrer(ast.parse(ruta.read_text(encoding="utf-8")), "<modulo>")
    return lecturas


def test_el_rasgo_solo_se_lee_donde_es_conducta() -> None:
    """Fuera de la lista blanca, leer `divergencia` es un canal de ventaja.

    Recorre los cuerpos de funciones de todo `tribal/` (no solo las
    asignaciones de nivel de módulo), así que caza comparaciones, umbrales y
    `+=` — las formas que el guard por nombres no veía.
    """
    for ruta in sorted(RAIZ.glob("tribal/**/*.py")):
        relativa = ruta.relative_to(RAIZ).as_posix()
        for funcion, linea in _lecturas_de_divergencia(ruta):
            assert (relativa, funcion) in SITIOS_CON_DIVERGENCIA, (
                f"{relativa}:{linea}: {funcion} lee `divergencia` fuera de la lista blanca"
            )

    # `getattr(genoma, "divergencia")` esquiva la comprobación de atributos, así
    # que el nombre solo puede aparecer como cadena en la tabla de rasgos.
    for ruta in sorted(RAIZ.glob("tribal/**/*.py")):
        relativa = ruta.relative_to(RAIZ).as_posix()
        if relativa == "tribal/core/genoma.py":
            continue
        for nodo in ast.walk(ast.parse(ruta.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.Constant) and nodo.value == "divergencia":
                raise AssertionError(f"{relativa}:{nodo.lineno}: lectura por cadena del rasgo")


def test_no_reaparecen_los_canales_de_ventaja_directa() -> None:
    for ruta in MODULOS_SIN_VENTAJA:
        fuente = (RAIZ / ruta).read_text(encoding="utf-8")

        for prohibido in NOMBRES_PROHIBIDOS:
            assert prohibido not in fuente, f"{ruta}: reaparece {prohibido}"

        for numero, linea in enumerate(fuente.splitlines(), start=1):
            minuscula = linea.lower()
            if "divergencia" not in minuscula:
                continue
            for token in TOKENS_DE_RECURSO:
                assert token not in minuscula, (
                    f"{ruta}:{numero}: el rasgo toca {token!r}: {linea.strip()}"
                )


def test_beber_sacia_igual_a_los_dos_temperamentos() -> None:
    """Misma sed y misma agua: la sed que queda no depende del rasgo."""

    def tras_beber(divergencia: float, sed: float) -> tuple[float, int]:
        tiles = [[TipoTile.HIERBA for _ in range(6)] for _ in range(6)]
        agua = Recurso(
            id=1,
            tipo=TipoRecurso.AGUA,
            x=1,
            y=1,
            cantidad=40,
            capacidad=40,
            regeneracion=10,
            alcance=3.0,
        )
        individuo = Individuo(
            id=1,
            sexo="m",
            genoma=Genoma(divergencia=divergencia),
            necesidades=Necesidades(energia=100.0, sed=sed),
            x=1.0,
            y=1.0,
            habilidades=Habilidades(),
        )
        mundo = Mundo(
            ancho=6,
            alto=6,
            tiles=tiles,
            recursos=[agua],
            individuos=[individuo],
            azar=random.Random(0),
        )
        assert acciones.beber(individuo, mundo)
        return individuo.necesidades.sed, agua.cantidad

    # 50 y 90: con 50 los dos quedan saciados y con 90 se ve cuánto sacia cada
    # uno, así que una saciedad distinta no se esconde en el suelo de 0.
    for sed in (50.0, 90.0):
        assert tras_beber(0.1, sed) == tras_beber(0.9, sed)


def test_el_temperamento_no_cambia_quien_puede_criar() -> None:
    """Edad, cooldown y energía deciden; el rasgo no mueve el umbral."""

    def puede(divergencia: float) -> list[bool]:
        simulacion = crear(1, 12)
        individuo = simulacion.mundo.individuos[0]
        individuo.edad = individuo.madurez
        individuo.cooldown_reproduccion = 0
        individuo.genoma = Genoma(divergencia=divergencia)
        resultados = []
        for energia in (UMBRAL_REPRODUCCION - 1, UMBRAL_REPRODUCCION, UMBRAL_REPRODUCCION + 1):
            individuo.necesidades.energia = energia
            resultados.append(simulacion._puede_reproducir(individuo))
        return resultados

    assert puede(0.1) == puede(0.9) == [False, False, True]


def test_el_genoma_no_cambia_en_una_partida() -> None:
    """Nadie edita el genoma en caliente: mismo individuo, mismo genoma."""
    simulacion = crear(SEMILLA, 12, config=SimConfig(seed=SEMILLA, individuos=12, crisis=True))
    simulacion.step()
    antes = {individuo.id: individuo.genoma for individuo in simulacion.mundo.individuos}
    for _ in range(499):
        simulacion.step()
    despues = {
        individuo.id: individuo.genoma
        for individuo in simulacion.mundo.individuos
        if individuo.id in antes
    }

    assert despues, "la tribu se extinguió en 500 ticks: el test no mediría nada"
    for id_, genoma in despues.items():
        assert genoma == antes[id_], f"el genoma de {id_} cambió en la partida"


def test_el_temperamento_no_cambia_lo_que_cuesta_vivir() -> None:
    """Mismo genoma salvo `divergencia`: misma energía y misma sed tras N ticks."""

    def necesidades_finales(divergencia: float) -> Necesidades:
        individuo = _errante(1, divergencia, *POSICION)
        simulacion = Simulacion(
            _pradera(SEMILLA, individuo),
            SimConfig(seed=SEMILLA, individuos=1, depredadores=0),
        )
        for _ in range(200):
            simulacion.step()
        return individuo.necesidades

    conformista = necesidades_finales(0.1)
    divergente = necesidades_finales(0.9)

    assert divergente.energia == pytest.approx(conformista.energia)
    assert divergente.sed == pytest.approx(conformista.sed)


# --- 3. Selección por conducta, medible ----------------------------------


def test_el_resumen_publica_descubridores_y_diferencial_de_seleccion() -> None:
    uno, dos, tres = (_con_hambre(id_) for id_ in (1, 2, 3))
    simulacion = Simulacion(_pradera(0, uno, dos, tres))
    simulacion._descubridores.add(1)
    dos.necesidades.salud = 0.0
    simulacion._enterrar()

    resumen = simulacion.resumen()
    assert resumen["descubridores"] == [1]
    assert resumen["supervivencia_descubridores"] == pytest.approx(1.0)
    assert resumen["supervivencia_no_descubridores"] == pytest.approx(0.5)
    assert resumen["diferencial_seleccion"] == pytest.approx(0.5)


def test_las_crias_entran_en_el_denominador_del_diferencial() -> None:
    simulacion = crear(1, 12)
    simulacion._descubridores.add(1)
    madre, padre = simulacion.mundo.individuos[:2]

    assert simulacion.resumen()["supervivencia_no_descubridores"] == pytest.approx(1.0)

    simulacion.mundo.individuos[1].necesidades.salud = 0.0
    simulacion._enterrar()
    assert simulacion.resumen()["supervivencia_no_descubridores"] == pytest.approx(
        10 / 11, abs=1e-3
    )

    simulacion._nacer(madre, padre)

    assert simulacion.resumen()["supervivencia_no_descubridores"] == pytest.approx(
        11 / 12, abs=1e-3
    )


def test_con_escasez_el_descubridor_conserva_mas_energia() -> None:
    """La ventaja es de la habilidad aprendida, no del rasgo: misma divergencia."""
    grafo = _grafo_con("raedera")

    sabio = _con_hambre(1)
    sabio.habilidades = Habilidades({"fabricar"})
    ignorante = _con_hambre(2)
    mundo = _mundo_con_comida(sabio, ignorante)

    efecto_sabio = beneficios.conocidos(grafo, sabio.habilidades.conocidas)
    efecto_ignorante = beneficios.conocidos(grafo, ignorante.habilidades.conocidas)
    assert acciones.comer(sabio, mundo, bonus_bayas=efecto_sabio.bayas)
    assert acciones.comer(ignorante, mundo, bonus_bayas=efecto_ignorante.bayas)

    assert sabio.necesidades.energia > ignorante.necesidades.energia
    assert sabio.genoma.divergencia == ignorante.genoma.divergencia


def test_con_escasez_aparecen_descubridores_y_en_calma_el_diferencial_es_cero() -> None:
    crisis = run(
        ticks=TICKS_CRISIS,
        seed=SEMILLA,
        headless=True,
        config=SimConfig(seed=SEMILLA, individuos=12, crisis=True),
    ).resumen()
    calma = run(
        ticks=TICKS_CRISIS,
        seed=SEMILLA,
        headless=True,
        config=SimConfig(seed=SEMILLA, individuos=12),
    ).resumen()

    assert crisis["descubridores"], "en crisis nadie descubrió nada: no hay mecanismo"
    assert crisis["diferencial_seleccion"] == pytest.approx(
        crisis["supervivencia_descubridores"] - crisis["supervivencia_no_descubridores"],
        abs=1e-3,
    )

    assert calma["descubridores"] == []
    assert calma["diferencial_seleccion"] == 0.0


# --- 4. Un divergente que no descubre nada no tiene ventaja ----------------


def test_un_divergente_que_no_descubre_nada_rinde_igual_que_un_conformista() -> None:
    """Mismo mapa y misma semilla; sin combinaciones, misma energía."""

    def tras_comer(divergencia: float) -> float:
        individuo = _con_hambre(1)
        individuo.genoma = Genoma(divergencia=divergencia)
        simulacion = Simulacion(_mundo_con_comida(individuo))
        simulacion.step()
        return individuo.necesidades.energia

    assert tras_comer(0.9) == pytest.approx(tras_comer(0.1))
