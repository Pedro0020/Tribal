"""
Recursos del mundo: fuentes de agua, bayas y caza.

Cada recurso es finito (`cantidad`) y se regenera una unidad cada
`regeneracion` ticks hasta `capacidad`. Beber y comer los agotan, así que un
recurso muy visitado deja de servir y el individuo tiene que buscar otro.
"""

from __future__ import annotations

import math

from tribal.core.modelos import (
    Individuo,
    Mundo,
    Recurso,
    TipoRecurso,
    TipoTile,
)

CAPACIDAD = {TipoRecurso.AGUA: 40, TipoRecurso.BAYAS: 4, TipoRecurso.CAZA: 2}
REGENERACION = {TipoRecurso.AGUA: 10, TipoRecurso.BAYAS: 420, TipoRecurso.CAZA: 1500}
#: Margen de uso: para el agua, lo que se suma al radio del lago (beber desde la orilla).
ALCANCE = {TipoRecurso.AGUA: 1.5, TipoRecurso.BAYAS: 1.5, TipoRecurso.CAZA: 1.5}
#: Cuántas piezas de caza se reparten por el mapa.
N_CAZA = 8


def sembrar(mundo: Mundo) -> None:
    """Reparte los recursos a partir del terreno ya generado. Idempotente."""
    mundo.recursos.clear()
    siguiente_id = 1

    for x, y, radio in _anclas_de_agua(mundo):
        mundo.recursos.append(
            _nuevo(siguiente_id, TipoRecurso.AGUA, x, y, alcance=radio + ALCANCE[TipoRecurso.AGUA])
        )
        siguiente_id += 1

    bosques = [
        (x, y)
        for y, fila in enumerate(mundo.tiles)
        for x, tipo in enumerate(fila)
        if tipo == TipoTile.BOSQUE
    ]
    for indice, (x, y) in enumerate(bosques):
        if indice % 2 == 0:
            mundo.recursos.append(_nuevo(siguiente_id, TipoRecurso.BAYAS, x, y))
            siguiente_id += 1

    hierba = [
        (x, y)
        for y, fila in enumerate(mundo.tiles)
        for x, tipo in enumerate(fila)
        if tipo == TipoTile.HIERBA
    ]
    for x, y in mundo.azar.sample(hierba, min(N_CAZA, len(hierba))):
        mundo.recursos.append(_nuevo(siguiente_id, TipoRecurso.CAZA, x, y))
        siguiente_id += 1


def regenerar(mundo: Mundo) -> None:
    """Un punto de recurso por intervalo; nunca por encima de la capacidad."""
    for recurso in mundo.recursos:
        if recurso.cantidad < recurso.capacidad and mundo.tick % recurso.regeneracion == 0:
            recurso.cantidad += 1


def consumir(recurso: Recurso, cantidad: int = 1) -> bool:
    """Gasta `cantidad` unidades. False si no queda nada que gastar."""
    if recurso.cantidad < cantidad:
        return False
    recurso.cantidad -= cantidad
    return True


def distancia(a_x: float, a_y: float, b_x: float, b_y: float) -> float:
    return math.hypot(a_x - b_x, a_y - b_y)


def en_alcance(individuo: Individuo, recurso: Recurso) -> bool:
    return distancia(individuo.x, individuo.y, recurso.x, recurso.y) <= recurso.alcance


def mas_cercano(
    mundo: Mundo, individuo: Individuo, tipos: tuple[TipoRecurso, ...]
) -> Recurso | None:
    """Recurso con existencias más próximo. Desempata por id para no depender del orden."""
    mejor: Recurso | None = None
    mejor_clave = (math.inf, 0)
    for recurso in mundo.recursos:
        if recurso.tipo not in tipos or recurso.cantidad <= 0:
            continue
        clave = (distancia(individuo.x, individuo.y, recurso.x, recurso.y), recurso.id)
        if clave < mejor_clave:
            mejor = recurso
            mejor_clave = clave
    return mejor


def _nuevo(id_: int, tipo: TipoRecurso, x: int, y: int, alcance: float | None = None) -> Recurso:
    capacidad = CAPACIDAD[tipo]
    return Recurso(
        id=id_,
        tipo=tipo,
        x=x,
        y=y,
        cantidad=capacidad,
        capacidad=capacidad,
        regeneracion=REGENERACION[tipo],
        alcance=ALCANCE[tipo] if alcance is None else alcance,
    )


def _anclas_de_agua(mundo: Mundo) -> list[tuple[int, int, float]]:
    """Un punto por lago: la casilla de agua más cercana a su centro, y su radio.

    Un solo recurso por lago evita contar el mismo agua cinco veces. El alcance
    cubre el radio entero, así que desde cualquier orilla se puede beber.
    """
    vistos = [[False] * mundo.ancho for _ in range(mundo.alto)]
    anclas: list[tuple[int, int, float]] = []
    for y, fila in enumerate(mundo.tiles):
        for x, tipo in enumerate(fila):
            if tipo != TipoTile.AGUA or vistos[y][x]:
                continue
            celdas = _lago(mundo, x, y, vistos)
            ancla = _centro(celdas)
            radio = max(distancia(ancla[0], ancla[1], cx, cy) for cx, cy in celdas)
            anclas.append((ancla[0], ancla[1], radio))
    return anclas


def _lago(mundo: Mundo, x: int, y: int, vistos: list[list[bool]]) -> list[tuple[int, int]]:
    celdas: list[tuple[int, int]] = []
    pendientes = [(x, y)]
    vistos[y][x] = True
    while pendientes:
        actual_x, actual_y = pendientes.pop()
        celdas.append((actual_x, actual_y))
        for vecina_x, vecina_y in (
            (actual_x + 1, actual_y),
            (actual_x - 1, actual_y),
            (actual_x, actual_y + 1),
            (actual_x, actual_y - 1),
        ):
            if (
                0 <= vecina_x < mundo.ancho
                and 0 <= vecina_y < mundo.alto
                and mundo.tiles[vecina_y][vecina_x] == TipoTile.AGUA
                and not vistos[vecina_y][vecina_x]
            ):
                vistos[vecina_y][vecina_x] = True
                pendientes.append((vecina_x, vecina_y))
    return celdas


def _centro(celdas: list[tuple[int, int]]) -> tuple[int, int]:
    media_x = sum(x for x, _ in celdas) / len(celdas)
    media_y = sum(y for _, y in celdas) / len(celdas)
    return min(celdas, key=lambda celda: (abs(celda[0] - media_x) + abs(celda[1] - media_y), celda))
