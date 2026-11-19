"""F1-005: la puerta F1→F2 se mide por conducta, no por el rasgo.

Cinco contratos:

1. En crisis, quien descubrió una combinación rinde más que quien no la
   descubrió, con la misma divergencia; y un divergente que no descubre nada
   rinde igual que un conformista.
2. El guard del rasgo se amplía: snapshot de genoma y necesidades alrededor de
   las funciones de conducta permitidas, lista blanca de llamadas a
   `temperamento()` y prohibición de escribir `divergencia` en runtime.
3. El barrido compara los dos brazos (misma config salvo `crisis`) y publica
   la tabla con un veredicto booleano por criterio.
4. El test de CI usa tres semillas y comprueba la dirección del mecanismo:
   en crisis se experimenta y aparecen combinaciones; en calma, no.
5. Dos procesos con la misma semilla dan el mismo informe.
"""

from __future__ import annotations

import ast
import json
import random
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from tribal.agents import instinto
from tribal.config import SimConfig
from tribal.core import acciones, recursos
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
from tribal.gate_f1 import Barrido, Brazo, Fila, medir_barrido, parsear_semillas
from tribal.sim import Simulacion, crear

RAIZ = Path(__file__).resolve().parents[1]
#: Únicos sitios que pueden *llamar* a `temperamento()`: clasificar quién
#: experimenta, quién imita y contar temperamentos en el resumen. Llamarlo
#: desde una vía de aptitud es un canal nuevo, y este test lo caza.
SITIOS_CON_TEMPERAMENTO = {
    ("tribal/sim.py", "_intentar_combinacion"),
    ("tribal/sim.py", "_practicar"),
    ("tribal/sim.py", "resumen"),
    # Telemetría de la ronda 6: contar temperamentos para publicar descubrimientos,
    # imitaciones y longevidad. No decide nada del motor.
    ("tribal/sim.py", "_tramo"),
    # Telemetría por intervalo (`report telemetry`): cuenta los temperamentos
    # vivos de cada muestra. Medición, no conducta.
    ("tribal/sim.py", "muestra"),
    # Conducta: qué radio de comida ve cada temperamento y a dónde va cuando no
    # ve nada. Cambia lo que sabe, no lo que rinde lo que come.
    ("tribal/agents/instinto.py", "radio_percepcion"),
    ("tribal/agents/instinto.py", "_buscar_comida"),
}


def _mundo_con_comida(*individuos: Individuo) -> Mundo:
    """Seis por seis de hierba y bayas en (1, 1)."""
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


def _hambriento(id_: int, divergencia: float = 0.5) -> Individuo:
    return Individuo(
        id=id_,
        sexo="m",
        genoma=Genoma(divergencia=divergencia),
        necesidades=Necesidades(energia=40.0),
        x=1.0,
        y=1.0,
        habilidades=Habilidades(),
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


def _energia_tras_comer(individuo: Individuo, grafo: Grafo) -> float:
    """Come con escasez (2 de 8): con el recurso lleno la técnica no paga."""
    mundo = _mundo_con_comida(individuo)
    mundo.recursos[0].cantidad = 2
    estado = beneficios.situacion(mundo)
    utilidades_tick = beneficios.utilidades(grafo, mundo, estado)
    efecto = beneficios.conocidos(grafo, individuo.habilidades.conocidas, utilidades_tick)
    assert acciones.comer(individuo, mundo, bonus_bayas=efecto.bayas, bonus_caza=efecto.caza)
    return individuo.necesidades.energia


def _instantanea(simulacion: Simulacion) -> list[tuple[int, Genoma, float, float, float]]:
    """Genoma y necesidades de todos los vivos, para comparar antes/después."""
    return [
        (
            individuo.id,
            individuo.genoma,
            individuo.necesidades.energia,
            individuo.necesidades.sed,
            individuo.necesidades.salud,
        )
        for individuo in simulacion.mundo.individuos
    ]


def _lecturas_de_temperamento(ruta: Path) -> list[tuple[str, int]]:
    """`(función, línea)` de cada llamada a `temperamento(...)` del módulo."""
    llamadas: list[tuple[str, int]] = []

    def es_temperamento(nodo: ast.expr) -> bool:
        if isinstance(nodo, ast.Name):
            return nodo.id == "temperamento"
        return isinstance(nodo, ast.Attribute) and nodo.attr == "temperamento"

    def recorrer(nodo: ast.AST, funcion: str) -> None:
        for hijo in ast.iter_child_nodes(nodo):
            siguiente = (
                hijo.name if isinstance(hijo, (ast.FunctionDef, ast.AsyncFunctionDef)) else funcion
            )
            if isinstance(hijo, ast.Call) and es_temperamento(hijo.func):
                llamadas.append((funcion, hijo.lineno))
            recorrer(hijo, siguiente)

    recorrer(ast.parse(ruta.read_text(encoding="utf-8")), "<modulo>")
    return llamadas


# --- 1. Mecanismo: la ventaja es del descubridor, no del rasgo --------------


@pytest.mark.parametrize("divergencia", [0.1, 0.5, 0.9])
def test_en_escasez_el_descubridor_rinde_mas_aunque_su_divergencia_sea_la_misma(
    divergencia: float,
) -> None:
    """El que sabe `fabricar` (la aprendió al descubrir) come mejor; el rasgo no cambia."""
    grafo = _grafo_con("raedera")
    sabio = _hambriento(1, divergencia)
    sabio.habilidades = Habilidades({"fabricar"})
    ignorante = _hambriento(2, divergencia)

    assert sabio.genoma.divergencia == ignorante.genoma.divergencia
    assert _energia_tras_comer(sabio, grafo) > _energia_tras_comer(ignorante, grafo)


def test_descubrir_es_lo_que_ensena_la_habilidad_y_de_ahi_viene_la_ventaja(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dos divergentes idénticos: solo uno experimenta, y esa diferencia se cobra."""
    descubridor = _hambriento(1, 0.9)
    testigo = _hambriento(2, 0.9)
    descubridor.necesidades = Necesidades(energia=80.0, sed=0.0)
    testigo.necesidades = Necesidades(energia=80.0, sed=0.0)
    mundo = _mundo_con_comida(descubridor, testigo)
    mundo.recursos[0].cantidad = 4
    simulacion = Simulacion(mundo, SimConfig(seed=0, individuos=1, crisis=True))
    simulacion.grafo = Grafo()
    for nodo_id in ("guijarro", "lasca", "bifaz"):
        simulacion.grafo.descubrir(nodo_id, autor=1, tick=1)
    monkeypatch.setattr("tribal.sim.PROB_INTENTO_DIVERGENTE", 100.0)
    monkeypatch.setattr("tribal.sim.PROB_COMPLETAR_COMBINACION", 1.0)

    assert simulacion._intentar_combinacion(descubridor) is True
    assert simulacion.grafo.activo("raedera")
    assert descubridor.habilidades.sabe("fabricar")
    assert not testigo.habilidades.sabe("fabricar")

    # La energía se mide al comer, no al descubrir: los dos vuelven a 40.
    descubridor.necesidades.energia = 40.0
    testigo.necesidades.energia = 40.0
    estado = beneficios.situacion(mundo)
    utilidades_tick = beneficios.utilidades(simulacion.grafo, mundo, estado)
    efectos = [
        beneficios.conocidos(simulacion.grafo, individuo.habilidades.conocidas, utilidades_tick)
        for individuo in (descubridor, testigo)
    ]
    for individuo, efecto in zip((descubridor, testigo), efectos, strict=True):
        assert acciones.comer(individuo, mundo, bonus_bayas=efecto.bayas)

    assert descubridor.necesidades.energia > testigo.necesidades.energia

    resumen = simulacion.resumen()
    assert resumen["descubrimientos"] == 1
    assert resumen["descubrimientos_divergentes"] == 1
    assert resumen["divergentes_registrados"] >= 1
    assert resumen["tasa_descubrimiento_divergente"] > 0.0
    assert resumen["tasa_imitacion"] == 0.0


def test_un_divergente_sin_descubrimientos_rinde_igual_que_un_conformista() -> None:
    """Mismo mapa y misma semilla; sin combinaciones, misma energía tras comer."""

    def energia(divergencia: float) -> float:
        individuo = _hambriento(1, divergencia)
        simulacion = Simulacion(_mundo_con_comida(individuo))
        simulacion.step()
        return individuo.necesidades.energia

    assert energia(0.9) == pytest.approx(energia(0.1))


def test_sin_crisis_explorar_no_mejora_la_energia_media() -> None:
    """Con comida al alcance, los tres temperamentos comen igual y nadie explora."""
    individuos = [
        _hambriento(id_, divergencia)
        for id_, divergencia in enumerate((0.1, 0.1, 0.5, 0.5, 0.9, 0.9), start=1)
    ]
    mundo = _mundo_con_comida(*individuos)
    mundo.recursos[0].cantidad = len(individuos)

    elegidas = [instinto.elegir(individuo, mundo) for individuo in individuos]
    assert all(accion.nombre == "comer" and not accion.explora for accion in elegidas)

    for individuo, accion in zip(individuos, elegidas, strict=True):
        assert acciones.aplicar(individuo, mundo, accion)
    energias = [individuo.necesidades.energia for individuo in individuos]
    assert energias == pytest.approx([80.0] * len(individuos))


# --- 2. Guard ampliado: snapshots y llamadas a temperamento() --------------


def test_las_funciones_de_conducta_no_editan_genoma_ni_necesidades(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`_intentar_combinacion`, `_practicar` y `_punto_errante` no tocan la aptitud."""
    simulacion = crear(3, 12, config=SimConfig(seed=3, individuos=12, crisis=True))
    for individuo in simulacion.mundo.individuos:
        individuo.necesidades = Necesidades(energia=80.0, sed=10.0, salud=90.0)
    simulacion.grafo = Grafo()
    for nodo_id in ("guijarro", "lasca", "bifaz"):
        simulacion.grafo.descubrir(nodo_id, autor=1, tick=1)

    actores = simulacion.mundo.individuos
    actores[0].genoma = replace(actores[0].genoma, divergencia=0.9)
    actores[1].genoma = replace(actores[1].genoma, divergencia=0.1)
    monkeypatch.setattr("tribal.sim.PROB_INTENTO_DIVERGENTE", 100.0)
    monkeypatch.setattr("tribal.sim.PROB_COMPLETAR_COMBINACION", 1.0)

    antes = _instantanea(simulacion)
    assert simulacion._intentar_combinacion(actores[0]) is True
    assert _instantanea(simulacion) == antes

    simulacion._practicar(actores[1], "tallar", descubrir=True)
    assert _instantanea(simulacion) == antes

    actores[0].paseo = None
    simulacion._practicar(actores[0], "tallar", descubrir=False)
    assert _instantanea(simulacion) == antes


def test_el_paseo_no_edita_genoma_ni_necesidades() -> None:
    simulacion = crear(3, 12)
    for individuo in simulacion.mundo.individuos:
        individuo.necesidades = Necesidades(energia=80.0, sed=10.0, salud=90.0)
    antes = _instantanea(simulacion)
    for individuo in simulacion.mundo.individuos:
        individuo.paseo = None
        instinto._punto_errante(individuo, simulacion.mundo)
    assert _instantanea(simulacion) == antes


def test_temperamento_solo_se_llama_donde_es_conducta() -> None:
    """Una llamada nueva a `temperamento()` fuera de la lista blanca es un canal."""
    for ruta in sorted(RAIZ.glob("tribal/**/*.py")):
        relativa = ruta.relative_to(RAIZ).as_posix()
        for funcion, linea in _lecturas_de_temperamento(ruta):
            assert (relativa, funcion) in SITIOS_CON_TEMPERAMENTO, (
                f"{relativa}:{linea}: {funcion} llama a temperamento() fuera de la lista blanca"
            )


def test_el_rasgo_no_se_escribe_en_runtime() -> None:
    """Escribir `.divergencia` (o `setattr`) en cualquier módulo es editar la aptitud."""
    for ruta in sorted(RAIZ.glob("tribal/**/*.py")):
        relativa = ruta.relative_to(RAIZ).as_posix()
        arbol = ast.parse(ruta.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if (
                isinstance(nodo, ast.Attribute)
                and nodo.attr == "divergencia"
                and isinstance(nodo.ctx, ast.Store)
            ):
                raise AssertionError(f"{relativa}:{nodo.lineno}: escritura de `divergencia`")
            if (
                isinstance(nodo, ast.Call)
                and isinstance(nodo.func, ast.Name)
                and nodo.func.id == "setattr"
                and len(nodo.args) >= 2
                and isinstance(nodo.args[1], ast.Constant)
                and nodo.args[1].value == "divergencia"
            ):
                raise AssertionError(f"{relativa}:{nodo.lineno}: `setattr` de `divergencia`")


def test_la_informacion_del_conformista_es_precisa_si_el_parche_no_migra() -> None:
    """La memoria solo envejece con la migración; el consumo no la invalida."""
    from tribal.core.modelos import Parche

    def mundo_con_parche() -> tuple[Mundo, Recurso]:
        tiles = [[TipoTile.HIERBA for _ in range(30)] for _ in range(20)]
        caza = Recurso(
            id=1,
            tipo=TipoRecurso.CAZA,
            x=4,
            y=4,
            cantidad=2,
            capacidad=2,
            regeneracion=1500,
            alcance=1.5,
        )
        mundo = Mundo(
            ancho=30,
            alto=20,
            tiles=tiles,
            recursos=[caza],
            individuos=[],
            azar=random.Random(0),
        )
        mundo.tick = 1
        mundo.parches = [Parche(id=1, tipo=TipoRecurso.CAZA, x=4.0, y=4.0, radio=0.0, fuentes=[1])]
        return mundo, caza

    def fijar(mundo: Mundo) -> tuple[Individuo, Individuo, Individuo]:
        conformista = _hambriento(1, 0.2)
        conformista.x, conformista.y = 5.0, 4.0
        referente = _hambriento(2, 0.2)
        referente.x, referente.y = 5.5, 4.0
        referente.necesidades.energia = 90.0
        divergente = _hambriento(3, 0.9)
        divergente.x, divergente.y = 5.0, 4.0
        for individuo in (conformista, referente, divergente):
            # Memoria formada en el parche 1 cuando aún no había migrado.
            individuo.ultimo_recurso = (4.0, 4.0)
            individuo.ultimo_parche = 1
            individuo.ultimo_parche_migracion = 0
        mundo.individuos = [conformista, referente, divergente]
        return conformista, referente, divergente

    # Sin migración, aunque el consumo vacíe el parche, la memoria sigue siendo
    # cierta: el conformista vuelve al sitio y espera la regeneración.
    mundo, caza = mundo_con_parche()
    conformista, _, _ = fijar(mundo)
    caza.cantidad = 0
    assert instinto._memoria_vigente(mundo, conformista)
    resultado = instinto._buscar_comida(conformista, mundo)
    assert resultado == ((4.0, 4.0), False)

    # Con migración, la memoria caduca: el conformista copia otra memoria vieja
    # y el divergente rastrea el parche nuevo.
    mundo, caza = mundo_con_parche()
    conformista, _, divergente = fijar(mundo)
    caza.cantidad = 0
    assert recursos.migrar(mundo, umbral=0.5, cooldown=0)
    assert (caza.x, caza.y) != (4, 4)
    assert not instinto._memoria_vigente(mundo, conformista)

    resultado_conformista = instinto._buscar_comida(conformista, mundo)
    assert resultado_conformista is not None
    destino_conformista, explora = resultado_conformista
    assert (destino_conformista, explora) == ((4.0, 4.0), False)

    resultado_divergente = instinto._buscar_comida(divergente, mundo)
    assert resultado_divergente is not None
    destino_divergente, explora_divergente = resultado_divergente
    assert explora_divergente
    assert recursos.distancia(destino_divergente[0], destino_divergente[1], caza.x, caza.y) <= 1.0


# --- 3. El barrido y su veredicto -----------------------------------------


def _brazo(
    div: float,
    *,
    poblacion: int = 10,
    extinta: bool = False,
    S: float = 0.0,
    reproductores: int = 10,
    mean_div_nacidos: float = 0.5,
) -> Brazo:
    return Brazo(
        div_pct=div,
        div_media=0.5,
        div_sigma=0.1,
        nacimientos=10,
        nodos_nuevos=3,
        poblacion=0 if extinta else poblacion,
        combinaciones=2,
        intentos=4,
        mean_div_nacidos=mean_div_nacidos,
        S=S,
        reproductores=reproductores,
    )


def _barrido(filas: list[Fila]) -> Barrido:
    return Barrido(ticks=8000, individuos=12, filas=tuple(filas))


def test_el_veredicto_exige_que_suba_en_ocho_y_no_baje_en_ninguna() -> None:
    filas = [Fila(seed, _brazo(10.0), _brazo(20.0 if seed <= 8 else 10.0)) for seed in range(1, 11)]
    veredicto = _barrido(filas).veredicto()

    assert veredicto["sube"] == 8
    assert veredicto["empata"] == 2
    assert veredicto["sube_en_8_de_10"] is True
    assert veredicto["no_baja"] is True
    assert veredicto["secundaria"] is True


def test_una_sola_semilla_que_baja_tumba_el_veredicto() -> None:
    filas = [Fila(seed, _brazo(10.0), _brazo(20.0 if seed <= 8 else 10.0)) for seed in range(1, 11)]
    filas[8] = Fila(9, _brazo(20.0), _brazo(10.0))
    veredicto = _barrido(filas).veredicto()

    assert veredicto["sube"] == 8
    assert veredicto["baja"] == 1
    assert veredicto["no_baja"] is False
    assert veredicto["secundaria"] is False


def test_la_crisis_no_puede_ser_el_regimen_favorable() -> None:
    filas = [
        Fila(
            seed,
            _brazo(10.0),
            _brazo(20.0, poblacion=30 if seed <= 4 else 5),
        )
        for seed in range(1, 11)
    ]
    veredicto = _barrido(filas).veredicto()

    assert veredicto["crisis_menos_poblada"] == 6
    assert veredicto["crisis_no_mas_poblada_en_6_de_10"] is True
    assert veredicto["secundaria"] is True

    filas[6] = Fila(7, _brazo(10.0), _brazo(20.0, poblacion=30, extinta=True))
    veredicto = _barrido(filas).veredicto()
    assert veredicto["extinciones_crisis"] == 1
    assert veredicto["extinciones_calma"] == 0
    assert veredicto["no_mas_extinciones_en_crisis"] is False
    assert veredicto["secundaria"] is False


def test_el_veredicto_de_S_exige_crisis_positiva_y_calma_negativa() -> None:
    filas = [
        Fila(
            seed,
            _brazo(10.0, S=-0.02),
            _brazo(20.0, S=0.05 if seed <= 6 else -0.02),
        )
        for seed in range(1, 11)
    ]
    veredicto = _barrido(filas).veredicto()

    assert veredicto["S_crisis_positivo"] == 6
    assert veredicto["S_calma_negativo"] == 10
    assert veredicto["S_crisis_positivo_en_6_de_10"] is True
    assert veredicto["S_calma_negativo_en_6_de_10"] is True
    assert veredicto["senal"] is True
    assert veredicto["primaria"] is True

    # Cinco positivas en crisis: no hay señal.
    filas_cinco = [
        Fila(seed, _brazo(10.0, S=-0.02), _brazo(20.0, S=0.05 if seed <= 5 else 0.0))
        for seed in range(1, 11)
    ]
    veredicto = _barrido(filas_cinco).veredicto()
    assert veredicto["S_crisis_positivo"] == 5
    assert veredicto["senal"] is False
    assert veredicto["primaria"] is False

    # Cinco calmas no negativas: tampoco.
    filas_calma = [
        Fila(
            seed,
            _brazo(10.0, S=-0.02 if seed <= 5 else 0.0),
            _brazo(20.0, S=0.05),
        )
        for seed in range(1, 11)
    ]
    veredicto = _barrido(filas_calma).veredicto()
    assert veredicto["S_calma_negativo"] == 5
    assert veredicto["senal"] is False
    assert veredicto["primaria"] is False

    # Sin reproductores no hay S medible y no cuenta como negativo.
    filas[0] = Fila(1, _brazo(10.0, S=-0.02, reproductores=0), _brazo(20.0, S=0.0))
    assert _barrido(filas).veredicto()["S_calma_negativo"] == 9


def test_el_resumen_acumula_la_divergencia_de_nacidos_y_reproductores() -> None:
    simulacion = crear(3, 12)
    inicial = sum(individuo.genoma.divergencia for individuo in simulacion.mundo.individuos) / 12
    madre, padre = simulacion.mundo.individuos[:2]
    madre.genoma = replace(madre.genoma, divergencia=0.8)
    padre.genoma = replace(padre.genoma, divergencia=0.6)

    simulacion._nacer(madre, padre)

    hijo = simulacion.mundo.individuos[-1]
    resumen = simulacion.resumen()
    assert resumen["mean_divergencia_inicial"] == pytest.approx(inicial, abs=1e-4)
    assert resumen["mean_divergencia_nacidos"] == pytest.approx(hijo.genoma.divergencia)
    assert resumen["mean_divergencia_reproductores"] == pytest.approx(0.7)
    assert resumen["reproductores"] == 2
    assert resumen["S"] == pytest.approx(0.7 - inicial, abs=1e-4)
    assert resumen["S_fecundidad"] == pytest.approx(0.7 - inicial, abs=1e-4)
    final = sum(individuo.genoma.divergencia for individuo in simulacion.mundo.individuos) / len(
        simulacion.mundo.individuos
    )
    assert resumen["S_viabilidad"] == pytest.approx(final - inicial, abs=1e-4)


def test_el_resumen_mide_longevidad_de_descubridores_y_conformistas() -> None:
    simulacion = crear(1, 12)
    descubridor, conformista = simulacion.mundo.individuos[:2]
    descubridor.genoma = replace(descubridor.genoma, divergencia=0.9)
    conformista.genoma = replace(conformista.genoma, divergencia=0.1)
    descubridor.edad = 123
    conformista.edad = 77
    descubridor.necesidades.salud = 0.0
    conformista.necesidades.salud = 0.0
    simulacion._descubridores.add(descubridor.id)

    simulacion._enterrar()

    resumen = simulacion.resumen()
    assert resumen["longevidad_media_descubridores"] == pytest.approx(123.0)
    assert resumen["longevidad_media_conformistas"] == pytest.approx(77.0)
    assert resumen["muertes_descubridores"] == 1
    assert resumen["muertes_conformistas"] == 1


def test_el_barrido_serializa_la_tabla_y_el_veredicto() -> None:
    filas = [Fila(1, _brazo(10.0), _brazo(20.0)), Fila(2, _brazo(10.0), _brazo(20.0))]
    datos = _barrido(filas).a_json()

    assert datos["seeds"] == [1, 2]
    assert datos["filas"][0]["calma"]["div_pct"] == 10.0
    assert datos["filas"][0]["crisis"]["div_pct"] == 20.0
    assert set(datos["veredicto"]) >= {"sube_en_8_de_10", "no_baja", "primaria", "secundaria"}


def test_el_barrido_compara_los_dos_brazos_en_tres_semillas() -> None:
    """Dirección del mecanismo, no del rasgo: en crisis se experimenta; en calma, no."""
    barrido = medir_barrido((1, 2, 3), ticks=600)

    assert len(barrido.filas) == 3
    for fila in barrido.filas:
        assert fila.calma.intentos == 0
        assert fila.calma.combinaciones == 0
        assert fila.crisis.intentos > 0
        assert fila.crisis.combinaciones > 0


def test_el_barrido_admite_poblaciones_mayores_que_el_juego() -> None:
    """El parámetro del barrido llega a 100 aunque el juego viva en 8-15."""
    barrido = medir_barrido((1,), ticks=100, individuos=50)

    assert barrido.individuos == 50
    assert len(barrido.filas) == 1
    with pytest.raises(ValueError):
        medir_barrido((1,), ticks=10, individuos=101)


@pytest.mark.parametrize("texto", ["1-10", "1,3,5", "1-3,7", " 2 , 2 "])
def test_el_parseo_de_semillas_ordena_y_no_repite(texto: str) -> None:
    semillas = parsear_semillas(texto)
    assert list(semillas) == sorted(set(semillas))
    assert all(semilla >= 1 for semilla in semillas)


@pytest.mark.parametrize("texto", ["", "0-2", "3-1", "a", "1-"])
def test_el_parseo_de_semillas_rechaza_lo_que_no_es_un_rango(texto: str) -> None:
    with pytest.raises(ValueError):
        parsear_semillas(texto)


# --- 4. Determinismo entre procesos ---------------------------------------


def test_dos_procesos_dan_el_mismo_barrido() -> None:
    comando = [
        sys.executable,
        "-m",
        "tribal",
        "report",
        "gate-f1",
        "--seeds",
        "1",
        "--ticks",
        "400",
        "--json",
    ]

    primera = subprocess.run(comando, capture_output=True, text=True, check=True)
    segunda = subprocess.run(comando, capture_output=True, text=True, check=True)

    assert primera.stdout == segunda.stdout
    datos = json.loads(primera.stdout)
    assert datos["seeds"] == [1]
    assert "primaria" in datos["veredicto"]
