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
técnica se perdió (F3-002). **No** se reanuda la simulación: este módulo deja el
estado consultable para `report db` y los tests; reanudar es SAVE-001.

Una base creada antes de F3-002 no tiene las columnas de apagado: al abrirla se
añaden con `ALTER TABLE` (`_migrar_apagado`), tanto en lectura como en escritura,
y las filas existentes conservan su estado. Lo mismo hace `_migrar_telemetria`
con las columnas de F3-004. Así la partida vieja no se rechaza ni se recrea.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from tribal.config import SimConfig
from tribal.core.genoma import temperamento
from tribal.core.habilidades import Rama
from tribal.core.modelos import Individuo, Mundo
from tribal.culture.arbol import ORIGENES, Nodo, Origen
from tribal.culture.arbol import Estado as EstadoNodo
from tribal.culture.diario import Diario
from tribal.culture.grafo import Arista, Grafo
from tribal.store.esquema import ESQUEMA, PRAGMAS, TABLAS

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
class Estado:
    """Lo que se puede reabrir de una partida, sin reanudarla."""

    mundo: dict[str, Any]
    grafo: Grafo
    poblacion: list[IndividuoGuardado]
    tick: int
    seed: int
    config: dict[str, Any]


class Repositorio:
    """Puerta única a la base de una partida. `sqlite3` no sale de este módulo."""

    def __init__(self, ruta: str | Path, *, crear: bool = True) -> None:
        self.ruta = Path(ruta)
        self._con: sqlite3.Connection | None = None
        conexion = sqlite3.connect(self.ruta)
        conexion.row_factory = sqlite3.Row
        try:
            if crear:
                for pragma in PRAGMAS:
                    conexion.execute(pragma)
                conexion.executescript(ESQUEMA)
                _migrar_apagado(conexion)
                _migrar_telemetria(conexion)
                conexion.commit()
            else:
                self._comprobar_esquema(conexion)
                # Abrir una partida vieja para leer también la pone al día: las
                # columnas nuevas se añaden sin tocar las filas existentes.
                _migrar_apagado(conexion)
                _migrar_telemetria(conexion)
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
    ) -> None:
        """Vuelca el estado completo en una transacción (volcado, no delta)."""
        conexion = self._conexion()
        with conexion:
            for tabla in _ORDEN_BORRADO:
                conexion.execute(f"DELETE FROM {tabla}")
            conexion.execute(
                "INSERT INTO mundo (tick, seed, ancho, alto, estacion, clima, config) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    mundo.tick,
                    mundo.seed,
                    mundo.ancho,
                    mundo.alto,
                    mundo.estacion,
                    _json({"estacion": mundo.estacion, "depredadores": len(mundo.depredadores)}),
                    _json({} if config is None else config.a_json()),
                ),
            )
            conexion.executemany(
                "INSERT INTO individuos (id, nombre, edad, sexo, energia, salud, sed, genoma, "
                "habilidades, personalidad, divergencia, saliencia, estado) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [_fila_individuo(individuo) for individuo in mundo.individuos],
            )
            conexion.executemany(
                "INSERT INTO recursos (id, tipo, x, y, cantidad) VALUES (?, ?, ?, ?, ?)",
                [
                    (recurso.id, recurso.tipo.name.lower(), recurso.x, recurso.y, recurso.cantidad)
                    for recurso in mundo.recursos
                ],
            )
            conexion.executemany(
                "INSERT INTO nodos (id, tipo, titulo, contenido, popularidad, estado, origen, "
                "autor, tick, nivel, requisitos, tick_apagado, motivo_apagado) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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

    def cargar(self) -> Estado:
        """Reconstruye el grafo y la población guardados, sin tocarlos."""
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
            "SELECT tick, seed, ancho, alto, estacion, clima, config FROM mundo "
            "ORDER BY tick DESC LIMIT 1"
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
            f"nivel, requisitos, {apagado} FROM nodos"
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
    )


def _json(valor: object) -> str:
    return json.dumps(valor, ensure_ascii=False, sort_keys=True)


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


def _contar(conexion: sqlite3.Connection, tabla: str, donde: str | None = None) -> int:
    sql = f"SELECT COUNT(*) FROM {tabla}"  # tabla y condición salen de constantes
    if donde is not None:
        sql += f" WHERE {donde}"
    return int(conexion.execute(sql).fetchone()[0])
