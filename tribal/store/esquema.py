"""
El esquema SQLite de una partida (stack §5), como DDL y sin importar `sqlite3`.

Este módulo solo declara el texto: quién abre la conexión es
`tribal.store.repositorio`, el **único** que importa `sqlite3`. Las columnas
flexibles (`genoma`, `habilidades`, `personalidad`, `contenido`, `clima`,
`config`, `requisitos`) son JSON/texto libre; el resto son columnas con tipo
para poder consultar sin deserializar.

`nodos` guarda el grafo de cultura y `aristas` sus prerrequisitos. El `tipo`
de un nodo es su rama del árbol y `popularidad` son las veces que se ha
practicado; `origen`, `autor` y `tick` son datos de nacimiento (concepto §8b)
y por eso tienen columna propia: sin ellos el KPI no se puede reconstruir.
"""

from __future__ import annotations

#: Tablas de stack §5, en el orden en que se documentan.
TABLAS: tuple[str, ...] = (
    "individuos",
    "relaciones",
    "recursos",
    "mundo",
    "nodos",
    "aristas",
    "recuerdos",
    "diario",
    "telemetria",
)

#: DDL completo. `CREATE TABLE IF NOT EXISTS` lo hace idempotente: abrir una
#: partida ya escrita no la reinicia.
ESQUEMA: str = """
CREATE TABLE IF NOT EXISTS mundo (
    tick INTEGER PRIMARY KEY,
    seed INTEGER NOT NULL,
    ancho INTEGER NOT NULL,
    alto INTEGER NOT NULL,
    estacion TEXT,
    clima TEXT NOT NULL,
    config TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS individuos (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    edad INTEGER NOT NULL,
    sexo TEXT NOT NULL,
    energia REAL NOT NULL,
    salud REAL NOT NULL,
    sed REAL NOT NULL,
    genoma TEXT NOT NULL,
    habilidades TEXT NOT NULL,
    personalidad TEXT NOT NULL,
    divergencia REAL NOT NULL,
    saliencia REAL NOT NULL,
    estado TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS relaciones (
    id_a INTEGER NOT NULL REFERENCES individuos(id),
    id_b INTEGER NOT NULL REFERENCES individuos(id),
    tipo TEXT NOT NULL,
    intensidad REAL NOT NULL,
    PRIMARY KEY (id_a, id_b, tipo)
);

CREATE TABLE IF NOT EXISTS recursos (
    id INTEGER PRIMARY KEY,
    tipo TEXT NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    cantidad INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS nodos (
    id TEXT PRIMARY KEY,
    tipo TEXT NOT NULL,
    titulo TEXT NOT NULL,
    contenido TEXT NOT NULL,
    popularidad INTEGER NOT NULL,
    estado TEXT NOT NULL,
    origen TEXT NOT NULL,
    autor INTEGER NOT NULL,
    tick INTEGER NOT NULL,
    nivel INTEGER NOT NULL,
    requisitos TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS aristas (
    id_origen TEXT NOT NULL REFERENCES nodos(id),
    id_destino TEXT NOT NULL REFERENCES nodos(id),
    tipo_relacion TEXT NOT NULL,
    peso REAL NOT NULL,
    PRIMARY KEY (id_origen, id_destino, tipo_relacion)
);

CREATE TABLE IF NOT EXISTS recuerdos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_individuo INTEGER REFERENCES individuos(id),
    tipo TEXT NOT NULL,
    texto TEXT NOT NULL,
    embedding BLOB,
    tick INTEGER NOT NULL,
    saliencia REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS diario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tick INTEGER NOT NULL,
    tipo_evento TEXT NOT NULL,
    narracion TEXT NOT NULL,
    individuo_id INTEGER,
    narrador_id INTEGER,
    narrada INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS telemetria (
    tick INTEGER PRIMARY KEY,
    poblacion INTEGER NOT NULL,
    n_divergentes INTEGER NOT NULL,
    n_conformistas INTEGER NOT NULL,
    n_nodos INTEGER NOT NULL,
    n_aristas INTEGER NOT NULL
);
"""

#: `WAL` mantiene la escritura por intervalo barata y no bloquea al lector;
#: `foreign_keys` es por conexión y hay que activarlo en cada apertura.
PRAGMAS: tuple[str, ...] = ("PRAGMA journal_mode=WAL", "PRAGMA foreign_keys=ON")
