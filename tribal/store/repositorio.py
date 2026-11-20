"""
Persistencia de la partida en SQLite: el **único** módulo que importa `sqlite3`.

El resto del producto trabaja contra esta interfaz fina —`guardar`, `cargar`,
`instantanea`, `cerrar`— y no sabe que debajo hay SQLite (stack §3). El esquema
vive como texto en `tribal.store.esquema` y aquí se aplica al abrir la base.

La escritura es un volcado completo por intervalo, no una fila por frame: el
motor llama a `guardar` cada `ticks_guardado` ticks y al cerrar, y cada volcado
sustituye el estado anterior dentro de una sola transacción. Reabrir la partida
reconstruye el grafo con el `origen`, el `autor` y el `tick` de cada nodo, que
es lo que el KPI necesita, y con su `tick_apagado`/`motivo_apagado` si la
técnica se perdió (F3-002). Desde SAVE-001 `cargar()` devuelve además
`Estado.partida`: el `Mundo`, el `Grafo`, el `Diario` y la telemetría
rehidratados, con el estado del RNG, para que `tribal.sim` pueda seguir desde
el tick guardado. El `save_meta.json` se escribe **después** del `COMMIT`, de
forma atómica, y es un resumen legible, no la fuente de verdad: si el proceso
muere antes, la base sigue siendo válida.

Una base creada antes de F3-002 no tiene las columnas de apagado: al abrirla se
añaden con `ALTER TABLE` (`_migrar_apagado`), tanto en lectura como en escritura,
y las filas existentes conservan su estado. Lo mismo hace `_migrar_telemetria`
con las columnas de F3-004. Así la partida vieja no se rechaza ni se recrea.
"""

from __future__ import annotations

import json
import os
import random
import sqlite3
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from tribal.config import SimConfig
from tribal.core.genoma import Genoma, temperamento
from tribal.core.habilidades import Habilidades, Rama
from tribal.core.modelos import (
    Depredador,
    Individuo,
    Mundo,
    Necesidades,
    Parche,
    Recurso,
    TipoRecurso,
    TipoTile,
)
from tribal.culture.arbol import ORIGENES, Nodo, Origen
from tribal.culture.arbol import Estado as EstadoNodo
from tribal.culture.diario import Diario, Entrada
from tribal.culture.grafo import Arista, Grafo
from tribal.store.esquema import ESQUEMA, PRAGMAS, TABLAS

#: Versión del formato de `save_meta.json`. Cambia cuando cambie el contrato.
SAVE_VERSION = 1

#: Orden de borrado: primero quien referencia, luego quien es referenciado.
_ORDEN_BORRADO: tuple[str, ...] = (
    "aristas",
    "recuerdos",
    "relaciones",
    "telemetria",
    "diario",
    "nodos",
    "individuos",
    "recursos",
    "mundo",
    "contadores",
)


class BaseInvalida(RuntimeError):
    """El fichero no es una partida SQLite válida o no es de la tribu."""


@dataclass(frozen=True, slots=True)
class IndividuoGuardado:
    """Una fila de `individuos` ya deserializada."""

    id: int
    nombre: str
    edad: int
    sexo: str
    energia: float
    salud: float
    sed: float
    genoma: dict[str, float]
    habilidades: list[str]
    personalidad: dict[str, Any]
    saliencia: float
    estado: str


@dataclass(frozen=True, slots=True)
class EstadoPartida:
    """Estado rehidratado para reanudar: mundo, grafo, diario y telemetría."""

    mundo: Mundo
    grafo: Grafo
    diario: Diario
    telemetria: list[dict[str, Any]]
    contadores: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Estado:
    """Lo que se puede reabrir de una partida."""

    mundo: dict[str, Any]
    grafo: Grafo
    poblacion: list[IndividuoGuardado]
    tick: int
    seed: int
    config: dict[str, Any]
    partida: EstadoPartida | None = None


class Repositorio:
    """Puerta única a la base de una partida. `sqlite3` no sale de este módulo."""

    def __init__(self, ruta: str | Path, *, crear: bool = True) -> None:
        self.ruta = Path(ruta)
        self._con: sqlite3.Connection | None = None
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        conexion = sqlite3.connect(self.ruta)
        conexion.row_factory = sqlite3.Row
        try:
            if crear:
                for pragma in PRAGMAS:
                    conexion.execute(pragma)
                conexion.executescript(ESQUEMA)
                _migrar_apagado(conexion)
                _migrar_telemetria(conexion)
                _migrar_save(conexion)
                conexion.commit()
            else:
                self._comprobar_esquema(conexion)
                # Abrir una partida vieja para leer también la pone al día: las
                # columnas nuevas se añaden sin tocar las filas existentes.
                _migrar_apagado(conexion)
                _migrar_telemetria(conexion)
                _migrar_save(conexion)
                conexion.commit()
        except sqlite3.DatabaseError as exc:
            conexion.close()
            raise BaseInvalida(f"{self.ruta}: no es una base SQLite válida ({exc})") from exc
        self._con = conexion

    def guardar(
        self,
        mundo: Mundo,
        grafo: Grafo,
        diario: Diario,
        telemetria: list[dict[str, Any]],
        *,
        config: SimConfig | None = None,
        contadores: dict[str, Any] | None = None,
    ) -> None:
        """Vuelca el estado completo en una transacción (volcado, no delta).

        `contadores` es el estado de `Simulacion` que no vive en el mundo
        (nacimientos, muertes, hitos, presupuestos...); sin él la partida se
        puede consultar pero no reanudar con el mismo `resumen()`. El
        `save_meta.json` se escribe después del `COMMIT`: si falla, la base ya
        está consistente.
        """
        conexion = self._conexion()
        with conexion:
            for tabla in _ORDEN_BORRADO:
                conexion.execute(f"DELETE FROM {tabla}")
            conexion.execute(
                "INSERT INTO mundo (tick, seed, ancho, alto, estacion, clima, config, "
                "tiles, rng, parches, depredadores) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    mundo.tick,
                    mundo.seed,
                    mundo.ancho,
                    mundo.alto,
                    mundo.estacion,
                    _json({"estacion": mundo.estacion, "depredadores": len(mundo.depredadores)}),
                    _json({} if config is None else config.a_json()),
                    _json([[int(tipo) for tipo in fila] for fila in mundo.tiles]),
                    _json(_rng_a_json(mundo.azar)),
                    _json([_parche_a_json(parche) for parche in mundo.parches]),
                    _json([asdict(depredador) for depredador in mundo.depredadores]),
                ),
            )
            conexion.executemany(
                "INSERT INTO individuos (id, nombre, edad, sexo, energia, salud, sed, genoma, "
                "habilidades, personalidad, divergencia, saliencia, estado, x, y, madurez, "
                "cooldown_reproduccion, huyendo, movido, paseo, ultimo_recurso, ultimo_parche, "
                "ultimo_parche_migracion, intencion_llm) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [_fila_individuo(individuo) for individuo in mundo.individuos],
            )
            conexion.executemany(
                "INSERT INTO recursos (id, tipo, x, y, cantidad, capacidad, regeneracion, alcance) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        recurso.id,
                        recurso.tipo.name.lower(),
                        recurso.x,
                        recurso.y,
                        recurso.cantidad,
                        recurso.capacidad,
                        recurso.regeneracion,
                        recurso.alcance,
                    )
                    for recurso in mundo.recursos
                ],
            )
            conexion.executemany(
                "INSERT INTO nodos (id, tipo, titulo, contenido, popularidad, estado, origen, "
                "autor, tick, nivel, requisitos, tick_apagado, motivo_apagado, imitado, "
                "imitadores, ultimo_imitador, imitaciones_tick) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        nodo.id,
                        nodo.rama,
                        nodo.titulo,
                        nodo.contenido,
                        grafo.veces_usado.get(nodo.id, 0),
                        nodo.estado,
                        nodo.origen,
                        nodo.autor,
                        nodo.tick,
                        nodo.nivel,
                        _json(list(nodo.requisitos)),
                        nodo.tick_apagado,
                        nodo.motivo_apagado,
                        grafo.imitado.get(nodo.id, 0),
                        _json(sorted(grafo.imitadores.get(nodo.id, ()))),
                        grafo.ultimo_imitador.get(nodo.id),
                        _json(grafo.imitaciones_tick.get(nodo.id, [])),
                    )
                    for nodo in grafo.nodos.values()
                ],
            )
            conexion.executemany(
                "INSERT INTO aristas (id_origen, id_destino, tipo_relacion, peso) "
                "VALUES (?, ?, ?, ?)",
                [(arista.origen, arista.destino, "prerrequisito", 1.0) for arista in grafo.aristas],
            )
            conexion.executemany(
                "INSERT INTO diario (tick, tipo_evento, narracion, individuo_id, narrador_id, "
                "narrada) VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        entrada.tick,
                        entrada.tipo,
                        entrada.texto,
                        entrada.individuo_id,
                        entrada.narrador_id,
                        int(entrada.narrada),
                    )
                    for entrada in diario.entradas
                ],
            )
            conexion.executemany(
                "INSERT INTO telemetria (tick, poblacion, n_divergentes, n_conformistas, "
                "n_neutros, n_nodos, n_aristas, media_energia, media_sed) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        muestra["tick"],
                        muestra["poblacion"],
                        muestra["divergentes"],
                        muestra["conformistas"],
                        muestra["neutros"],
                        muestra["nodos"],
                        muestra["aristas"],
                        muestra["media_energia"],
                        muestra["media_sed"],
                    )
                    for muestra in telemetria
                ],
            )
            conexion.execute(
                "INSERT OR REPLACE INTO contadores (id, datos) VALUES (1, ?)",
                (_json({} if contadores is None else contadores),),
            )
        try:
            _escribir_meta(
                self.ruta,
                mundo,
                grafo,
                {} if config is None else config.a_json(),
            )
        except OSError as exc:
            # La meta es un resumen, no la fuente de verdad: la base ya está
            # commiteada y reanudar no la necesita. No se aborta la sesión.
            print(
                f"warning: no pude escribir {self.ruta.parent / 'save_meta.json'}: {exc}",
                file=sys.stderr,
            )

    def cargar(self) -> Estado:
        """Reconstruye el grafo, la población y, si hay volcado completo, el mundo."""
        conexion = self._conexion()
        mundo = self._leer_mundo(conexion)
        grafo = self._leer_grafo(conexion)
        poblacion = self._leer_poblacion(conexion)
        return Estado(
            mundo=mundo,
            grafo=grafo,
            poblacion=poblacion,
            tick=int(mundo.get("tick", 0)),
            seed=int(mundo.get("seed", 0)),
            config=cast(dict[str, Any], mundo.get("config", {})),
            partida=_leer_partida(conexion, grafo) if mundo else None,
        )

    def instantanea(self) -> dict[str, Any]:
        """Recuentos de `report db`: vivos, nodos por origen, aristas, diario y telemetría."""
        conexion = self._conexion()
        mundo = self._leer_mundo(conexion)
        por_origen = {origen: 0 for origen in ORIGENES}
        for origen, cuenta in conexion.execute(
            "SELECT origen, COUNT(*) FROM nodos WHERE estado = 'activo' GROUP BY origen"
        ):
            por_origen[str(origen)] = int(cuenta)
        return {
            "tick": int(mundo.get("tick", 0)),
            "seed": int(mundo.get("seed", 0)),
            "estacion": mundo.get("estacion"),
            "poblacion": _contar(conexion, "individuos", "estado = 'vivo'"),
            "nodos": _contar(conexion, "nodos"),
            "nodos_por_origen": por_origen,
            "aristas": _contar(conexion, "aristas"),
            "diario": _contar(conexion, "diario"),
            "telemetria": _contar(conexion, "telemetria"),
            "recursos": _contar(conexion, "recursos"),
            "recuerdos": _contar(conexion, "recuerdos"),
        }

    def telemetria(self) -> list[dict[str, Any]]:
        """Muestras guardadas, ordenadas por tick y con los nombres de `muestra()`."""
        return [
            {
                "tick": int(fila["tick"]),
                "poblacion": int(fila["poblacion"]),
                "divergentes": int(fila["n_divergentes"]),
                "conformistas": int(fila["n_conformistas"]),
                "neutros": int(fila["n_neutros"]),
                "nodos": int(fila["n_nodos"]),
                "aristas": int(fila["n_aristas"]),
                "media_energia": float(fila["media_energia"]),
                "media_sed": float(fila["media_sed"]),
            }
            for fila in self._conexion().execute(
                "SELECT tick, poblacion, n_divergentes, n_conformistas, n_neutros, "
                "n_nodos, n_aristas, media_energia, media_sed FROM telemetria ORDER BY tick"
            )
        ]

    def cerrar(self) -> None:
        """`COMMIT` + cierre. Idempotente: llamarlo dos veces no falla."""
        if self._con is None:
            return
        try:
            self._con.commit()
        finally:
            self._con.close()
            self._con = None

    def _comprobar_esquema(self, conexion: sqlite3.Connection) -> None:
        """Una base sin las tablas de la tribu no es una partida: error, no DDL.

        Las tablas son obligatorias; las columnas nuevas de una tabla existente
        se migran después con `ALTER TABLE`, que no borra filas.
        """
        existentes = {
            str(fila[0])
            for fila in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        faltan = sorted(set(TABLAS) - existentes)
        if faltan:
            raise BaseInvalida(f"{self.ruta}: faltan tablas de la partida: {', '.join(faltan)}")

    def _conexion(self) -> sqlite3.Connection:
        if self._con is None:
            raise RuntimeError("el repositorio ya está cerrado")
        return self._con

    def _leer_mundo(self, conexion: sqlite3.Connection) -> dict[str, Any]:
        fila = conexion.execute(
            "SELECT tick, seed, ancho, alto, estacion, clima, config, tiles, rng, parches, "
            "depredadores FROM mundo ORDER BY tick DESC LIMIT 1"
        ).fetchone()
        if fila is None:
            return {}
        return {
            "tick": fila["tick"],
            "seed": fila["seed"],
            "ancho": fila["ancho"],
            "alto": fila["alto"],
            "estacion": fila["estacion"],
            "clima": json.loads(fila["clima"]),
            "config": json.loads(fila["config"]),
            "tiles": json.loads(fila["tiles"]) if fila["tiles"] else [],
            "rng": json.loads(fila["rng"]) if fila["rng"] else None,
            "parches": json.loads(fila["parches"]) if fila["parches"] else [],
            "depredadores": json.loads(fila["depredadores"]) if fila["depredadores"] else [],
        }

    def _leer_grafo(self, conexion: sqlite3.Connection) -> Grafo:
        grafo = Grafo()
        # Una base creada antes de F3-002 no tiene las columnas de apagado: se
        # leen como activas (0/""), igual que hacía el esquema anterior.
        columnas = {str(fila[1]) for fila in conexion.execute("PRAGMA table_info(nodos)")}
        apagado = (
            "tick_apagado, motivo_apagado"
            if {"tick_apagado", "motivo_apagado"} <= columnas
            else "0 AS tick_apagado, '' AS motivo_apagado"
        )
        for fila in conexion.execute(
            "SELECT id, tipo, titulo, contenido, popularidad, estado, origen, autor, tick, "
            f"nivel, requisitos, {apagado}, imitado, imitadores, ultimo_imitador, "
            "imitaciones_tick FROM nodos"
        ):
            nodo = Nodo(
                id=str(fila["id"]),
                rama=cast(Rama, fila["tipo"]),
                nivel=int(fila["nivel"]),
                titulo=str(fila["titulo"]),
                contenido=str(fila["contenido"]),
                requisitos=tuple(json.loads(fila["requisitos"])),
                origen=cast(Origen, fila["origen"]),
                estado=cast(EstadoNodo, fila["estado"]),
                autor=int(fila["autor"]),
                tick=int(fila["tick"]),
                tick_apagado=int(fila["tick_apagado"]),
                motivo_apagado=str(fila["motivo_apagado"]),
            )
            grafo.nodos[nodo.id] = nodo
            if fila["popularidad"]:
                grafo.veces_usado[nodo.id] = int(fila["popularidad"])
            if fila["imitado"]:
                grafo.imitado[nodo.id] = int(fila["imitado"])
            if fila["imitadores"]:
                grafo.imitadores[nodo.id] = {int(quien) for quien in json.loads(fila["imitadores"])}
            if fila["ultimo_imitador"] is not None:
                grafo.ultimo_imitador[nodo.id] = int(fila["ultimo_imitador"])
            if fila["imitaciones_tick"]:
                grafo.imitaciones_tick[nodo.id] = [
                    int(momento) for momento in json.loads(fila["imitaciones_tick"])
                ]
        for fila in conexion.execute("SELECT id_origen, id_destino FROM aristas"):
            grafo.aristas.append(Arista(str(fila["id_origen"]), str(fila["id_destino"])))
        return grafo

    def _leer_poblacion(self, conexion: sqlite3.Connection) -> list[IndividuoGuardado]:
        return [
            IndividuoGuardado(
                id=int(fila["id"]),
                nombre=str(fila["nombre"]),
                edad=int(fila["edad"]),
                sexo=str(fila["sexo"]),
                energia=float(fila["energia"]),
                salud=float(fila["salud"]),
                sed=float(fila["sed"]),
                genoma=json.loads(fila["genoma"]),
                habilidades=json.loads(fila["habilidades"]),
                personalidad=json.loads(fila["personalidad"]),
                saliencia=float(fila["saliencia"]),
                estado=str(fila["estado"]),
            )
            for fila in conexion.execute(
                "SELECT id, nombre, edad, sexo, energia, salud, sed, genoma, habilidades, "
                "personalidad, saliencia, estado FROM individuos ORDER BY id"
            )
        ]


def _fila_individuo(individuo: Individuo) -> tuple[Any, ...]:
    genoma = asdict(individuo.genoma)
    return (
        individuo.id,
        f"ind-{individuo.id}",
        individuo.edad,
        individuo.sexo,
        individuo.necesidades.energia,
        individuo.necesidades.salud,
        individuo.necesidades.sed,
        _json(genoma),
        _json(sorted(individuo.habilidades.conocidas)),
        _json({"temperamento": temperamento(individuo.genoma)}),
        individuo.genoma.divergencia,
        individuo.saliencia,
        "vivo" if individuo.vivo else "muerto",
        individuo.x,
        individuo.y,
        individuo.madurez,
        individuo.cooldown_reproduccion,
        int(individuo.huyendo),
        int(individuo.movido),
        _json(individuo.paseo),
        _json(individuo.ultimo_recurso),
        individuo.ultimo_parche,
        individuo.ultimo_parche_migracion,
        _json(individuo.intencion_llm),
    )


def _json(valor: object) -> str:
    return json.dumps(valor, ensure_ascii=False, sort_keys=True)


def _leer_partida(conexion: sqlite3.Connection, grafo: Grafo) -> EstadoPartida | None:
    """Rehidrata mundo, grafo, diario y contadores si el volcado es completo.

    Una base anterior a SAVE-001 no tiene `tiles`/`rng`: se puede consultar,
    pero no reanudar, y `Estado.partida` se queda en `None`.
    """
    fila = conexion.execute(
        "SELECT tick, seed, ancho, alto, estacion, tiles, rng, parches, depredadores "
        "FROM mundo ORDER BY tick DESC LIMIT 1"
    ).fetchone()
    if fila is None or not fila["tiles"]:
        return None
    tiles = [
        [TipoTile(int(tipo)) for tipo in fila_tiles]
        for fila_tiles in cast(list[list[int]], json.loads(fila["tiles"]))
    ]
    mundo = Mundo(
        ancho=int(fila["ancho"]),
        alto=int(fila["alto"]),
        tiles=tiles,
        recursos=_leer_recursos(conexion),
        individuos=_leer_individuos(conexion),
        azar=_rng_desde_json(json.loads(fila["rng"])),
        seed=int(fila["seed"]),
        tick=int(fila["tick"]),
        depredadores=[Depredador(**datos) for datos in json.loads(fila["depredadores"])],
        parches=[_parche_desde_json(datos) for datos in json.loads(fila["parches"])],
        estacion=fila["estacion"],
    )
    diario = Diario()
    for entrada in conexion.execute(
        "SELECT tick, tipo_evento, narracion, individuo_id, narrador_id, narrada "
        "FROM diario ORDER BY id"
    ):
        diario.entradas.append(
            Entrada(
                tick=int(entrada["tick"]),
                tipo=str(entrada["tipo_evento"]),
                texto=str(entrada["narracion"]),
                individuo_id=None
                if entrada["individuo_id"] is None
                else int(entrada["individuo_id"]),
                narrador_id=None if entrada["narrador_id"] is None else int(entrada["narrador_id"]),
                narrada=bool(entrada["narrada"]),
            )
        )
    fila_contadores = conexion.execute("SELECT datos FROM contadores WHERE id = 1").fetchone()
    contadores = {} if fila_contadores is None else json.loads(fila_contadores["datos"])
    return EstadoPartida(
        mundo=mundo,
        grafo=grafo,
        diario=diario,
        telemetria=_leer_telemetria(conexion),
        contadores=cast(dict[str, Any], contadores),
    )


def _leer_recursos(conexion: sqlite3.Connection) -> list[Recurso]:
    return [
        Recurso(
            id=int(fila["id"]),
            tipo=TipoRecurso[str(fila["tipo"]).upper()],
            x=int(fila["x"]),
            y=int(fila["y"]),
            cantidad=int(fila["cantidad"]),
            capacidad=int(fila["capacidad"]),
            regeneracion=int(fila["regeneracion"]),
            alcance=float(fila["alcance"]),
        )
        for fila in conexion.execute(
            "SELECT id, tipo, x, y, cantidad, capacidad, regeneracion, alcance "
            "FROM recursos ORDER BY id"
        )
    ]


def _leer_individuos(conexion: sqlite3.Connection) -> list[Individuo]:
    """Individuos completos, en orden de id, listos para el motor."""
    individuos = []
    for fila in conexion.execute(
        "SELECT id, sexo, genoma, habilidades, saliencia, x, y, madurez, "
        "cooldown_reproduccion, huyendo, movido, paseo, ultimo_recurso, ultimo_parche, "
        "ultimo_parche_migracion, intencion_llm, energia, salud, sed, estado, edad "
        "FROM individuos ORDER BY id"
    ):
        individuos.append(
            Individuo(
                id=int(fila["id"]),
                sexo=cast(Any, str(fila["sexo"])),
                genoma=Genoma(**json.loads(fila["genoma"])),
                necesidades=Necesidades(
                    energia=float(fila["energia"]),
                    sed=float(fila["sed"]),
                    salud=float(fila["salud"]),
                ),
                x=float(fila["x"]),
                y=float(fila["y"]),
                vivo=str(fila["estado"]) == "vivo",
                movido=bool(fila["movido"]),
                edad=int(fila["edad"]),
                madurez=int(fila["madurez"]),
                cooldown_reproduccion=int(fila["cooldown_reproduccion"]),
                huyendo=bool(fila["huyendo"]),
                habilidades=Habilidades(set(json.loads(fila["habilidades"]))),
                paseo=_par(fila["paseo"]),
                ultimo_recurso=_par(fila["ultimo_recurso"]),
                ultimo_parche=None if fila["ultimo_parche"] is None else int(fila["ultimo_parche"]),
                ultimo_parche_migracion=int(fila["ultimo_parche_migracion"]),
                intencion_llm=_intencion(fila["intencion_llm"]),
                saliencia=float(fila["saliencia"]),
            )
        )
    return individuos


def _leer_telemetria(conexion: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        {
            "tick": int(fila["tick"]),
            "poblacion": int(fila["poblacion"]),
            "divergentes": int(fila["n_divergentes"]),
            "conformistas": int(fila["n_conformistas"]),
            "neutros": int(fila["n_neutros"]),
            "nodos": int(fila["n_nodos"]),
            "aristas": int(fila["n_aristas"]),
            "media_energia": float(fila["media_energia"]),
            "media_sed": float(fila["media_sed"]),
        }
        for fila in conexion.execute(
            "SELECT tick, poblacion, n_divergentes, n_conformistas, n_neutros, n_nodos, "
            "n_aristas, media_energia, media_sed FROM telemetria ORDER BY tick"
        )
    ]


def _par(valor: Any) -> tuple[float, float] | None:
    if valor in (None, "", "null"):
        return None
    datos = json.loads(valor)
    return (float(datos[0]), float(datos[1]))


def _intencion(valor: Any) -> tuple[str, int] | None:
    if valor in (None, "", "null"):
        return None
    datos = json.loads(valor)
    return (str(datos[0]), int(datos[1]))


def _parche_a_json(parche: Parche) -> dict[str, Any]:
    return {
        "id": parche.id,
        "tipo": parche.tipo.name.lower(),
        "x": parche.x,
        "y": parche.y,
        "radio": parche.radio,
        "fuentes": list(parche.fuentes),
        "migraciones": parche.migraciones,
        "tick_migracion": parche.tick_migracion,
    }


def _parche_desde_json(datos: dict[str, Any]) -> Parche:
    return Parche(
        id=int(datos["id"]),
        tipo=TipoRecurso[str(datos["tipo"]).upper()],
        x=float(datos["x"]),
        y=float(datos["y"]),
        radio=float(datos["radio"]),
        fuentes=[int(fuente) for fuente in datos["fuentes"]],
        migraciones=int(datos["migraciones"]),
        tick_migracion=int(datos["tick_migracion"]),
    )


def _rng_a_json(azar: random.Random) -> list[Any]:
    version, estado, gauss = azar.getstate()
    return [int(version), [int(valor) for valor in estado], gauss]


def _rng_desde_json(datos: list[Any]) -> random.Random:
    version, estado, gauss = datos
    azar = random.Random()
    azar.setstate((int(version), tuple(int(valor) for valor in estado), gauss))
    return azar


def _escribir_meta(ruta: Path, mundo: Mundo, grafo: Grafo, config: dict[str, Any]) -> None:
    """Escribe `save_meta.json` junto a la base, ya commiteada y de forma atómica.

    Es un resumen legible, no la fuente de verdad: `cargar()` lee la base. Se
    escribe con `os.replace` después del `COMMIT`, así que un fallo aquí no deja
    la partida a medias.
    """
    destino = ruta.parent / "save_meta.json"
    ahora = datetime.now(UTC).isoformat(timespec="seconds")
    creado = ahora
    try:
        anterior = json.loads(destino.read_text(encoding="utf-8"))
        creado = str(anterior.get("creado") or ahora)
    except (OSError, ValueError):
        pass
    datos = {
        "version": SAVE_VERSION,
        "nombre": ruta.stem,
        "seed": mundo.seed,
        "tick": mundo.tick,
        "poblacion": len(mundo.individuos),
        "nodos": len(grafo.nodos),
        "config": config,
        "rng": _rng_a_json(mundo.azar),
        "creado": creado,
        "actualizado": ahora,
    }
    temporal = destino.with_name(f"{destino.name}.tmp")
    temporal.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporal, destino)


#: Columnas de apagado que llegaron en F3-002, con su valor por defecto. Una
#: base creada antes no las tiene; `estado` no cambia de formato (`activo`/
#: `apagado`), solo se añade el tick y la causa de la pérdida.
_COLUMNAS_APAGADO: tuple[tuple[str, str], ...] = (
    ("tick_apagado", "INTEGER NOT NULL DEFAULT 0"),
    ("motivo_apagado", "TEXT NOT NULL DEFAULT ''"),
)


def _migrar_apagado(conexion: sqlite3.Connection) -> None:
    """Añade las columnas de apagado si la partida se creó antes de F3-002."""
    columnas = {str(fila[1]) for fila in conexion.execute("PRAGMA table_info(nodos)")}
    for nombre, tipo in _COLUMNAS_APAGADO:
        if nombre not in columnas:
            conexion.execute(f"ALTER TABLE nodos ADD COLUMN {nombre} {tipo}")


#: Columnas de telemetría que llegaron en F3-004. Una base anterior las recibe
#: con cero: las muestras viejas se conservan y las nuevas traen el dato.
_COLUMNAS_TELEMETRIA: tuple[tuple[str, str], ...] = (
    ("n_neutros", "INTEGER NOT NULL DEFAULT 0"),
    ("media_energia", "REAL NOT NULL DEFAULT 0"),
    ("media_sed", "REAL NOT NULL DEFAULT 0"),
)


def _migrar_telemetria(conexion: sqlite3.Connection) -> None:
    """Añade las columnas de telemetría si la partida se creó antes de F3-004."""
    columnas = {str(fila[1]) for fila in conexion.execute("PRAGMA table_info(telemetria)")}
    for nombre, tipo in _COLUMNAS_TELEMETRIA:
        if nombre not in columnas:
            conexion.execute(f"ALTER TABLE telemetria ADD COLUMN {nombre} {tipo}")


#: Columnas que llegaron con SAVE-001 para reanudar: posición y conducta de cada
#: individuo, estado del RNG, tiles, parches, depredadores y los contadores del
#: grafo. Una base anterior las recibe con su valor por defecto y sigue siendo
#: consultable; `Estado.partida` solo aparece cuando `tiles`/`rng` ya existen.
_COLUMNAS_SAVE: dict[str, tuple[tuple[str, str], ...]] = {
    "mundo": (
        ("tiles", "TEXT NOT NULL DEFAULT ''"),
        ("rng", "TEXT NOT NULL DEFAULT ''"),
        ("parches", "TEXT NOT NULL DEFAULT ''"),
        ("depredadores", "TEXT NOT NULL DEFAULT ''"),
    ),
    "individuos": (
        ("x", "REAL NOT NULL DEFAULT 0"),
        ("y", "REAL NOT NULL DEFAULT 0"),
        ("madurez", "INTEGER NOT NULL DEFAULT 300"),
        ("cooldown_reproduccion", "INTEGER NOT NULL DEFAULT 0"),
        ("huyendo", "INTEGER NOT NULL DEFAULT 0"),
        ("movido", "INTEGER NOT NULL DEFAULT 0"),
        ("paseo", "TEXT NOT NULL DEFAULT ''"),
        ("ultimo_recurso", "TEXT NOT NULL DEFAULT ''"),
        ("ultimo_parche", "INTEGER"),
        ("ultimo_parche_migracion", "INTEGER NOT NULL DEFAULT -1"),
        ("intencion_llm", "TEXT NOT NULL DEFAULT ''"),
    ),
    "recursos": (
        ("capacidad", "INTEGER NOT NULL DEFAULT 0"),
        ("regeneracion", "INTEGER NOT NULL DEFAULT 0"),
        ("alcance", "REAL NOT NULL DEFAULT 0"),
    ),
    "nodos": (
        ("imitado", "INTEGER NOT NULL DEFAULT 0"),
        ("imitadores", "TEXT NOT NULL DEFAULT ''"),
        ("ultimo_imitador", "INTEGER"),
        ("imitaciones_tick", "TEXT NOT NULL DEFAULT ''"),
    ),
}


def _migrar_save(conexion: sqlite3.Connection) -> None:
    """Añade las columnas de SAVE-001 y la tabla `contadores` sin tocar filas."""
    for tabla, columnas_nuevas in _COLUMNAS_SAVE.items():
        existentes = {str(fila[1]) for fila in conexion.execute(f"PRAGMA table_info({tabla})")}
        for nombre, tipo in columnas_nuevas:
            if nombre not in existentes:
                conexion.execute(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}")
    conexion.execute(
        "CREATE TABLE IF NOT EXISTS contadores ("
        "id INTEGER PRIMARY KEY CHECK (id = 1), datos TEXT NOT NULL)"
    )


def _contar(conexion: sqlite3.Connection, tabla: str, donde: str | None = None) -> int:
    sql = f"SELECT COUNT(*) FROM {tabla}"  # tabla y condición salen de constantes
    if donde is not None:
        sql += f" WHERE {donde}"
    return int(conexion.execute(sql).fetchone()[0])
