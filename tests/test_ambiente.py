"""AMB-001: gradiente ambiental — parches, migración y estaciones (eje 3).

Contratos:

1. Las fuentes de recurso se agrupan en parches; un parche de comida agotado
   migra a otra zona con la misma semilla siempre al mismo sitio, y con otra
   semilla a otro.
2. La estación cicla cada `ticks_por_estacion` ticks y en invierno la
   regeneración cae a la mitad.
3. `resumen` publica `estacion`, `parches` (tipo, activo, abundancia) y
   `migraciones`.
4. Mecanismo, sin rasgos: en el mismo mundo y con el mismo genoma, la política
   que sigue el parche sobrevive más ticks que la que patrulla la zona agotada.
5. Dos procesos con la misma semilla dan el mismo resumen; otra semilla migra
   a otro sitio.
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tribal.agents import necesidades as nec
from tribal.config import SimConfig
from tribal.core import acciones, recursos
from tribal.core import mundo as modulo_mundo
from tribal.core.modelos import (
    Genoma,
    Individuo,
    Mundo,
    Necesidades,
    Parche,
    Recurso,
    TipoRecurso,
    TipoTile,
)
from tribal.culture import beneficios
from tribal.sim import ESTACIONES, Simulacion, run

#: Abundancia por debajo de la cual un parche cuenta como agotado en los tests.
UMBRAL = 0.25
#: Semilla del escenario controlado: la migración cae lejos del que se queda.
SEMILLA = 3
#: Horizonte del test de mecanismo: al que se queda le llega la muerte hacia el
#: tick 834 (energía a 0 en el 667 y 100 de salud a 0,6 por tick).
TICKS_MECANISMO = 1200
#: Tasas del test de mecanismo. La sed se deja casi plana para que lo que se
#: mida sea la comida, no la sed, y ninguna de las dos políticas descanse
#: (descansar da energía y taparía el efecto del parche).
TASA_SED = 0.02
TASA_ENERGIA = 0.15
TASA_SALUD = 0.6


def _escenario(seed: int = SEMILLA) -> tuple[Mundo, list[Recurso]]:
    """30×20 de hierba, agua de sobra y un parche de caza agotado en (4, 4)."""
    tiles = [[TipoTile.HIERBA for _ in range(30)] for _ in range(20)]
    agua = Recurso(
        id=1,
        tipo=TipoRecurso.AGUA,
        x=2,
        y=2,
        cantidad=1000,
        capacidad=1000,
        regeneracion=1,
        alcance=4.0,
    )
    caza = [
        Recurso(
            id=2 + indice,
            tipo=TipoRecurso.CAZA,
            x=4 + indice,
            y=4,
            cantidad=0,
            capacidad=40,
            # No se rellena sola: el parche solo vuelve a dar de comer si migra.
            regeneracion=10**9,
            alcance=1.5,
        )
        for indice in range(2)
    ]
    mundo = Mundo(
        ancho=30,
        alto=20,
        tiles=tiles,
        recursos=[agua, *caza],
        individuos=[],
        azar=random.Random(seed),
    )
    mundo.parches = [Parche(id=1, tipo=TipoRecurso.CAZA, x=4.5, y=4.0, radio=0.5, fuentes=[2, 3])]
    return mundo, caza


# --- 1. Parches -----------------------------------------------------------


def test_sembrar_agrupa_las_fuentes_en_parches() -> None:
    mundo = modulo_mundo.crear(seed=42, individuos=12)

    assert mundo.parches
    fuentes = [fuente for parche in mundo.parches for fuente in parche.fuentes]
    assert sorted(fuentes) == sorted(recurso.id for recurso in mundo.recursos)
    assert {parche.tipo for parche in mundo.parches} == set(TipoRecurso)
    for parche in mundo.parches:
        assert parche.fuentes
        assert all(
            recurso.tipo == parche.tipo
            for recurso in mundo.recursos
            if recurso.id in set(parche.fuentes)
        )

    # Misma semilla, mismos parches: el reparto no depende del orden del set.
    otro = modulo_mundo.crear(seed=42, individuos=12)
    assert [(p.tipo, p.x, p.y, p.fuentes) for p in otro.parches] == [
        (p.tipo, p.x, p.y, p.fuentes) for p in mundo.parches
    ]


def test_un_parche_agotado_migra_y_se_rellena_conservando_tipo_y_capacidad() -> None:
    mundo, caza = _escenario()
    mundo.tick = 1
    antes = [(recurso.x, recurso.y) for recurso in caza]

    migrados = recursos.migrar(mundo, umbral=UMBRAL, cooldown=0)

    assert len(migrados) == 1
    parche = migrados[0]
    assert parche.tipo == TipoRecurso.CAZA
    assert parche.migraciones == 1
    assert parche.tick_migracion == mundo.tick
    assert [(recurso.x, recurso.y) for recurso in caza] != antes
    assert all(recurso.cantidad == recurso.capacidad == 40 for recurso in caza)
    # Lleno otra vez: no migra dos veces seguidas.
    assert recursos.migrar(mundo, umbral=UMBRAL, cooldown=0) == []


def _fuentes(mundo: Mundo, parche: Parche) -> list[Recurso]:
    ids = set(parche.fuentes)
    return [recurso for recurso in mundo.recursos if recurso.id in ids]


def _agotar(mundo: Mundo, tipo: TipoRecurso) -> Parche:
    """Vacía el primer parche de ese tipo y deja el reloj listo para migrar."""
    parche = next(parche for parche in mundo.parches if parche.tipo == tipo)
    for recurso in _fuentes(mundo, parche):
        recurso.cantidad = 0
    mundo.tick = 1
    return parche


def test_los_parches_de_bayas_migran_en_el_mundo_real() -> None:
    """Un parche de bayas agotado se muda dentro del bosque del mapa de verdad.

    El bosque del mapa por defecto es pequeño y las bayas están repartidas por
    él: con el filtro viejo (dos tiles libres alrededor de cada mata frente a
    todas las demás) la migración de bayas era imposible y el test solo cubría
    la caza en un mundo fabricado.
    """
    mundo = modulo_mundo.crear(seed=42, individuos=12)
    parche = _agotar(mundo, TipoRecurso.BAYAS)
    fuentes = _fuentes(mundo, parche)
    antes = [(recurso.x, recurso.y) for recurso in fuentes]
    capacidades = [recurso.capacidad for recurso in fuentes]

    migrados = recursos.migrar(mundo, umbral=UMBRAL, cooldown=0)

    assert migrados == [parche]
    assert [(recurso.x, recurso.y) for recurso in fuentes] != antes
    assert [recurso.cantidad for recurso in fuentes] == capacidades
    assert [recurso.capacidad for recurso in fuentes] == capacidades
    assert all(mundo.pisable(recurso.x, recurso.y) for recurso in fuentes)
    assert all(mundo.tiles[recurso.y][recurso.x] != TipoTile.AGUA for recurso in fuentes)
    # El centro sigue cayendo en el terreno que le toca a la comida.
    assert mundo.tiles[int(parche.y)][int(parche.x)] == TipoTile.BOSQUE


def test_los_parches_de_caza_migran_en_el_mundo_real() -> None:
    mundo = modulo_mundo.crear(seed=42, individuos=12)
    parche = _agotar(mundo, TipoRecurso.CAZA)
    fuentes = _fuentes(mundo, parche)
    antes = [(recurso.x, recurso.y) for recurso in fuentes]

    assert recursos.migrar(mundo, umbral=UMBRAL, cooldown=0) == [parche]
    assert [(recurso.x, recurso.y) for recurso in fuentes] != antes
    assert all(recurso.cantidad == recurso.capacidad for recurso in fuentes)
    assert all(mundo.pisable(recurso.x, recurso.y) for recurso in fuentes)
    assert mundo.tiles[int(parche.y)][int(parche.x)] == TipoTile.HIERBA


def test_el_agua_no_migra_aunque_se_agote() -> None:
    """El agua es terreno: se bebe desde la orilla y su fuente es el propio lago.

    Moverla dejaría el tile azul donde ya no se puede beber, así que el parche
    de agua no migra; la estación es lo que la hace cambiar.
    """
    mundo = modulo_mundo.crear(seed=42, individuos=12)
    parche = _agotar(mundo, TipoRecurso.AGUA)
    fuentes = _fuentes(mundo, parche)
    antes = [(recurso.x, recurso.y) for recurso in fuentes]

    assert recursos.migrar(mundo, umbral=UMBRAL, cooldown=0) == []
    assert [(recurso.x, recurso.y) for recurso in fuentes] == antes
    assert parche.migraciones == 0


def test_no_se_migra_a_una_zona_con_fuentes_en_agua() -> None:
    """Si el único destino posible deja una fuente en agua, el parche no se mueve.

    Mapa de agua con una sola columna de hierba: el parche de caza está tumbado
    (sus fuentes se separan en horizontal), así que todo traslado deja la
    segunda fuente en el agua. `pisable` lo rechaza y las coordenadas no se
    tocan; sin ese filtro las fuentes acabarían dentro del lago.
    """
    tiles = [[TipoTile.AGUA for _ in range(12)] for _ in range(20)]
    for y in range(20):
        tiles[y][6] = TipoTile.HIERBA
    caza = [
        Recurso(
            id=1,
            tipo=TipoRecurso.CAZA,
            x=6,
            y=5,
            cantidad=0,
            capacidad=10,
            regeneracion=10**9,
            alcance=1.5,
        ),
        Recurso(
            id=2,
            tipo=TipoRecurso.CAZA,
            x=7,
            y=5,
            cantidad=0,
            capacidad=10,
            regeneracion=10**9,
            alcance=1.5,
        ),
    ]
    mundo = Mundo(
        ancho=12,
        alto=20,
        tiles=tiles,
        recursos=caza,
        individuos=[],
        azar=random.Random(1),
    )
    mundo.parches = [Parche(id=1, tipo=TipoRecurso.CAZA, x=6.5, y=5.0, radio=0.5, fuentes=[1, 2])]
    mundo.tick = 1

    assert recursos.migrar(mundo, umbral=UMBRAL, cooldown=0) == []
    assert [(recurso.x, recurso.y) for recurso in caza] == [(6, 5), (7, 5)]


def test_una_partida_normal_acaba_migrando_bayas_y_caza() -> None:
    """Sin tocar nada a mano, la comida agotada se muda con los dos tipos."""
    simulacion = Simulacion(modulo_mundo.crear(seed=42, individuos=12))

    for _ in range(1500):
        simulacion.step()

    migrados = {parche.tipo for parche in simulacion.mundo.parches if parche.migraciones > 0}
    assert TipoRecurso.BAYAS in migrados, "las bayas no migraron en una partida normal"
    assert TipoRecurso.CAZA in migrados, "la caza no migró en una partida normal"


def test_la_migracion_respeta_el_cooldown() -> None:
    mundo, caza = _escenario()
    mundo.tick = 10
    assert recursos.migrar(mundo, umbral=UMBRAL, cooldown=10)

    for recurso in caza:
        recurso.cantidad = 0
    mundo.tick = 15
    assert recursos.migrar(mundo, umbral=UMBRAL, cooldown=10) == []
    mundo.tick = 20
    assert recursos.migrar(mundo, umbral=UMBRAL, cooldown=10)


def test_la_migracion_es_determinista_y_depende_de_la_semilla() -> None:
    def destinos(seed: int) -> list[tuple[int, int]]:
        mundo, caza = _escenario(seed)
        mundo.tick = 1
        recursos.migrar(mundo, umbral=UMBRAL, cooldown=0)
        return [(recurso.x, recurso.y) for recurso in caza]

    assert destinos(SEMILLA) == destinos(SEMILLA)
    assert len({tuple(destinos(seed)) for seed in range(1, 6)}) > 1


# --- 2. Estación ----------------------------------------------------------


def test_la_estacion_cicla_cada_ticks_por_estacion() -> None:
    mundo, _ = _escenario()
    simulacion = Simulacion(
        mundo,
        SimConfig(seed=SEMILLA, individuos=1, ticks_por_estacion=10, depredadores=0),
    )

    vistas = []
    for _ in range(4 * 10):
        simulacion.step()
        vistas.append(mundo.estacion)

    esperado = [ESTACIONES[(tick // 10) % len(ESTACIONES)] for tick in range(1, 41)]
    assert vistas == esperado
    assert set(vistas) == set(ESTACIONES)
    assert simulacion.resumen()["estacion"] == ESTACIONES[(40 // 10) % len(ESTACIONES)]


def test_en_invierno_la_regeneracion_cae_a_la_mitad() -> None:
    def regenerado(factor: float) -> int:
        tile = [[TipoTile.HIERBA for _ in range(10)] for _ in range(10)]
        bayas = Recurso(
            id=1,
            tipo=TipoRecurso.BAYAS,
            x=5,
            y=5,
            cantidad=0,
            capacidad=40,
            regeneracion=10,
            alcance=1.5,
        )
        mundo = Mundo(
            ancho=10,
            alto=10,
            tiles=tile,
            recursos=[bayas],
            individuos=[],
            azar=random.Random(1),
        )
        for tick in range(1, 101):
            mundo.tick = tick
            recursos.regenerar(mundo, factor=factor)
        return bayas.cantidad

    assert regenerado(1.0) == 10
    assert regenerado(0.5) == 5


def test_la_utilidad_sube_en_invierno_solo_para_el_recurso_estacional() -> None:
    lleno = {tipo: 1.0 for tipo in TipoRecurso}

    def utilidad(nodo: str, estacion: str) -> float:
        return beneficios.utilidad(nodo, beneficios.Situacion(escasez=lleno, estacion=estacion), 1)

    assert utilidad("raedera", "invierno") > utilidad("raedera", "verano")
    assert utilidad("caceria_dirigida", "invierno") > utilidad("caceria_dirigida", "verano")
    # El agua no tiene estación: su técnica vale igual todo el año.
    assert utilidad("canto_ritual", "invierno") == pytest.approx(utilidad("canto_ritual", "verano"))


# --- 3. Telemetría en el resumen ------------------------------------------


def test_el_resumen_expone_estacion_parches_y_migraciones() -> None:
    config = SimConfig(seed=42, individuos=12, ticks_por_estacion=100)
    resumen = run(ticks=600, seed=42, headless=True, config=config).resumen()

    assert resumen["estacion"] == ESTACIONES[(600 // 100) % len(ESTACIONES)]
    assert resumen["parches"]
    for parche in resumen["parches"]:
        assert set(parche) == {"id", "tipo", "activo", "abundancia", "x", "y"}
        assert parche["tipo"] in {tipo.name.lower() for tipo in TipoRecurso}
        assert 0.0 <= parche["abundancia"] <= 1.0
    assert isinstance(resumen["migraciones"], int)
    assert resumen["migraciones"] > 0, "en 600 ticks el mundo ya tiene un parche agotado"


# --- 4. Mecanismo: seguir el parche paga ----------------------------------


def _rondar(individuo: Individuo, mundo: Mundo) -> acciones.Accion:
    """Patrulla un tile arriba y abajo: consume el tick sin regalar energía."""
    signo = 1.0 if mundo.tick % 2 else -1.0
    return acciones.Accion("moverse", destino=(individuo.x + signo, individuo.y))


def _seguir(individuo: Individuo, mundo: Mundo) -> acciones.Accion:
    """Va al parche con existencias y come allí cuando toca."""
    comida = recursos.mas_cercano(mundo, individuo, (TipoRecurso.CAZA,))
    if comida is None:
        return _rondar(individuo, mundo)
    if recursos.en_alcance(individuo, comida):
        if nec.energia_baja(individuo.necesidades):
            return acciones.Accion("comer")
        return _rondar(individuo, mundo)
    return acciones.Accion("moverse", destino=(float(comida.x), float(comida.y)))


def _quedarse(individuo: Individuo, mundo: Mundo) -> acciones.Accion:
    """Patrulla la zona agotada; solo come si algo le cae al alcance."""
    if nec.energia_baja(individuo.necesidades):
        comida = recursos.mas_cercano(mundo, individuo, (TipoRecurso.CAZA,))
        if comida is not None and recursos.en_alcance(individuo, comida):
            return acciones.Accion("comer")
    return _rondar(individuo, mundo)


def _superviviente(id_: int, x: float, y: float) -> Individuo:
    """Mismo genoma, sexo y necesidades: lo único que cambia es la política."""
    return Individuo(
        id=id_,
        sexo="m",
        genoma=Genoma(),
        necesidades=Necesidades(energia=100.0, sed=0.0),
        x=x,
        y=y,
    )


def test_seguir_el_parche_sobrevive_mas_que_quedarse_en_la_zona_agotada() -> None:
    mundo, _ = _escenario()
    seguir = _superviviente(1, 4.5, 4.0)
    quedarse = _superviviente(2, 4.5, 4.0)
    mundo.individuos = [seguir, quedarse]
    assert (seguir.x, seguir.y) == (quedarse.x, quedarse.y), "arrancan en el mismo sitio"
    assert seguir.genoma == quedarse.genoma, "el test no puede premiar rasgos"
    assert seguir.sexo == quedarse.sexo, "el sexo no entra en el bucle"

    mundo.tick = 1
    recursos.migrar(mundo, umbral=UMBRAL, cooldown=0)
    comida = recursos.mas_cercano(mundo, seguir, (TipoRecurso.CAZA,))
    assert comida is not None, "el parche agotado tenía que migrar con comida"
    assert recursos.distancia(comida.x, comida.y, quedarse.x, quedarse.y) > 8, (
        "el parche migró al lado del que se queda: el escenario no mide nada"
    )

    politicas = ((seguir, _seguir), (quedarse, _quedarse))
    muertes: dict[int, int | None] = {seguir.id: None, quedarse.id: None}
    for _ in range(TICKS_MECANISMO):
        mundo.tick += 1
        recursos.migrar(mundo, umbral=UMBRAL, cooldown=0)
        for individuo, politica in politicas:
            if muertes[individuo.id] is not None:
                continue
            nec.evolucionar(
                individuo.necesidades,
                individuo.genoma,
                tasa_sed=TASA_SED,
                tasa_energia=TASA_ENERGIA,
                tasa_salud=TASA_SALUD,
            )
            acciones.aplicar(individuo, mundo, politica(individuo, mundo))
            if individuo.necesidades.salud <= 0.0:
                muertes[individuo.id] = mundo.tick

    assert muertes[quedarse.id] is not None, "el que patrulla la zona agotada no murió"
    muerte_quedarse = muertes[quedarse.id]
    assert muerte_quedarse is not None
    muerte_seguir = muertes[seguir.id]
    sobrevive = TICKS_MECANISMO if muerte_seguir is None else muerte_seguir
    assert sobrevive > muerte_quedarse, (
        f"seguir el parche no pagó: {muerte_seguir} vs {muerte_quedarse}"
    )


# --- 5. Dos procesos ------------------------------------------------------


def _resumen_cli(config: SimConfig, tmp_path: Path) -> dict[str, Any]:
    destino = _escribir(tmp_path, config)
    comando = [
        sys.executable,
        "-m",
        "tribal",
        "run",
        "--headless",
        "--json",
        "--ticks",
        "1000",
        "--config",
        str(destino),
    ]
    salida = subprocess.run(comando, capture_output=True, text=True, check=True)
    datos: dict[str, Any] = json.loads(salida.stdout)
    return datos


def test_dos_procesos_iguales_y_otra_semilla_migra_a_otro_sitio(tmp_path: Path) -> None:
    config = SimConfig(seed=1, individuos=12, ticks_por_estacion=100)

    primera = _resumen_cli(config, tmp_path)
    segunda = _resumen_cli(config, tmp_path)
    assert primera == segunda

    otra = _resumen_cli(SimConfig(seed=2, individuos=12, ticks_por_estacion=100), tmp_path)
    assert primera["estacion"] in ESTACIONES
    assert primera["migraciones"] > 0, "con la semilla 1 no migró nada en 1000 ticks"
    assert otra["migraciones"] > 0, "con la semilla 2 no migró nada en 1000 ticks"
    assert [(p["tipo"], p["x"], p["y"]) for p in primera["parches"]] != [
        (p["tipo"], p["x"], p["y"]) for p in otra["parches"]
    ]


def _escribir(tmp_path: Path, config: SimConfig) -> Path:
    ruta = tmp_path / "cfg.json"
    ruta.write_text(json.dumps(config.a_json()), encoding="utf-8")
    return ruta
