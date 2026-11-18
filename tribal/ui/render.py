"""
Render top-down en pixel art, sin assets: cada tile de 8x8 se genera por código
una vez y se cachea. La UI solo lee el mundo y devuelve una `Surface`; quién la
pinta en pantalla es `tribal.ui.app`.
"""

from __future__ import annotations

from functools import cache, lru_cache

import pygame

from tribal.core.modelos import TILE_PX, Mundo, TipoRecurso, TipoTile

#: Franja superior con tick, población y medias.
ALTO_HUD = 14
COLOR_HUD = (26, 26, 30)
COLOR_TEXTO = (232, 226, 210)

_HIERBA = [(74, 140, 72), (82, 148, 76), (68, 132, 68)]
_HIERBA_PUNTO = (54, 112, 58)
#: Matas de hierba por variante: puntos sueltos, no una trama repetida.
_PUNTOS_HIERBA = (
    ((1, 3), (5, 6), (3, 1)),
    ((6, 2), (2, 6), (4, 4)),
    ((0, 5), (4, 0), (7, 3)),
)
_AGUA = [(40, 96, 168), (48, 106, 182)]
_AGUA_BRILLO = (86, 152, 208)
_TRONCO = (88, 62, 38)
_COPA = [(32, 92, 46), (40, 104, 52)]
_BAYA = (196, 48, 52)
_CAZA = (150, 112, 62)
_PIEL = (232, 190, 150)
_PELO = (44, 30, 22)
_PIERNAS = (58, 48, 40)
_TUNICA = {"m": (146, 88, 46), "f": (170, 66, 60)}
#: Depredador: pelaje oscuro y ojo rojo, para no confundirlo con la tribu.
_PELAJE = (66, 58, 52)
_PELAJE_CLARO = (92, 80, 70)
_OJO = (214, 54, 42)


def tamano_ventana(mundo: Mundo) -> tuple[int, int]:
    return (mundo.ancho * TILE_PX, mundo.alto * TILE_PX + ALTO_HUD)


def dibujar_frame(mundo: Mundo) -> pygame.Surface:
    """Dibuja el mundo entero en una Surface nueva (no toca el estado del mundo)."""
    lienzo = pygame.Surface(tamano_ventana(mundo))
    lienzo.fill(COLOR_HUD)

    for y, fila in enumerate(mundo.tiles):
        for x, tipo in enumerate(fila):
            variante = (x * 13 + y * 7 + (x * y) % 5) % 3
            lienzo.blit(_tile(tipo, variante), (x * TILE_PX, ALTO_HUD + y * TILE_PX))

    for recurso in mundo.recursos:
        if recurso.tipo == TipoRecurso.BAYAS and recurso.cantidad > 0:
            lienzo.blit(
                _marcador_bayas(), (recurso.x * TILE_PX + 1, ALTO_HUD + recurso.y * TILE_PX)
            )
        elif recurso.tipo == TipoRecurso.CAZA and recurso.cantidad > 0:
            lienzo.blit(
                _marcador_caza(), (recurso.x * TILE_PX + 1, ALTO_HUD + recurso.y * TILE_PX + 4)
            )

    for individuo in mundo.individuos:
        cria = individuo.edad < individuo.madurez
        sprite = _sprite_cria(individuo.sexo) if cria else _sprite(individuo.sexo)
        x = int(individuo.x * TILE_PX) + (2 if cria else 1)
        y = ALTO_HUD + int(individuo.y * TILE_PX) + (3 if cria else 1)
        lienzo.blit(sprite, (x, y))

    for depredador in mundo.depredadores:
        lienzo.blit(
            _sprite_depredador(),
            (int(depredador.x * TILE_PX), ALTO_HUD + int(depredador.y * TILE_PX)),
        )

    _dibujar_hud(lienzo, mundo)
    return lienzo


def _dibujar_hud(lienzo: pygame.Surface, mundo: Mundo) -> None:
    vivos = mundo.individuos
    if vivos:
        energia = sum(individuo.necesidades.energia for individuo in vivos) / len(vivos)
        sed = sum(individuo.necesidades.sed for individuo in vivos) / len(vivos)
    else:
        energia = 0.0
        sed = 0.0
    texto = f"tick {mundo.tick}  pob {len(vivos)}  energia {energia:.0f}  sed {sed:.0f}"
    lienzo.blit(_fuente().render(texto, False, COLOR_TEXTO), (3, 2))


@cache
def _tile(tipo: TipoTile, variante: int) -> pygame.Surface:
    superficie = pygame.Surface((TILE_PX, TILE_PX))
    if tipo == TipoTile.AGUA:
        superficie.fill(_AGUA[variante % len(_AGUA)])
        for x in range(1, 7, 3):
            superficie.set_at((x, 2 + (variante % 2) * 3), _AGUA_BRILLO)
            superficie.set_at((x + 1, 2 + (variante % 2) * 3), _AGUA_BRILLO)
        return superficie

    superficie.fill(_HIERBA[variante % len(_HIERBA)])
    if tipo == TipoTile.HIERBA:
        for x, y in _PUNTOS_HIERBA[variante % len(_PUNTOS_HIERBA)]:
            superficie.set_at((x, y), _HIERBA_PUNTO)
        return superficie

    # Bosque: suelo de hierba con un árbol encima.
    pygame.draw.rect(superficie, _TRONCO, pygame.Rect(3, 5, 2, 3))
    pygame.draw.rect(superficie, _COPA[variante % len(_COPA)], pygame.Rect(1, 1, 6, 4))
    pygame.draw.rect(superficie, _COPA[(variante + 1) % len(_COPA)], pygame.Rect(2, 2, 4, 2))
    return superficie


@cache
def _sprite(sexo: str) -> pygame.Surface:
    sprite = pygame.Surface((6, 8), pygame.SRCALPHA)
    tela = _TUNICA[sexo]
    pygame.draw.rect(sprite, _PELO, pygame.Rect(2, 0, 2, 1))
    pygame.draw.rect(sprite, _PIEL, pygame.Rect(2, 1, 2, 2))
    pygame.draw.rect(sprite, tela, pygame.Rect(1, 3, 4, 3))
    pygame.draw.rect(sprite, _PIEL, pygame.Rect(0, 3, 1, 2))
    pygame.draw.rect(sprite, _PIEL, pygame.Rect(5, 3, 1, 2))
    pygame.draw.rect(sprite, _PIERNAS, pygame.Rect(1, 6, 1, 2))
    pygame.draw.rect(sprite, _PIERNAS, pygame.Rect(4, 6, 1, 2))
    return sprite


@cache
def _sprite_cria(sexo: str) -> pygame.Surface:
    """Cría: misma paleta que el adulto, un tercio más baja."""
    sprite = pygame.Surface((4, 5), pygame.SRCALPHA)
    pygame.draw.rect(sprite, _PELO, pygame.Rect(1, 0, 2, 1))
    pygame.draw.rect(sprite, _PIEL, pygame.Rect(1, 1, 2, 1))
    pygame.draw.rect(sprite, _TUNICA[sexo], pygame.Rect(0, 2, 4, 2))
    pygame.draw.rect(sprite, _PIERNAS, pygame.Rect(1, 4, 1, 1))
    pygame.draw.rect(sprite, _PIERNAS, pygame.Rect(2, 4, 1, 1))
    return sprite


@cache
def _sprite_depredador() -> pygame.Surface:
    """Cuadrúpedo de 8x6: lomo oscuro, cabeza a la derecha y ojo rojo."""
    sprite = pygame.Surface((8, 6), pygame.SRCALPHA)
    pygame.draw.rect(sprite, _PELAJE, pygame.Rect(0, 2, 8, 3))
    pygame.draw.rect(sprite, _PELAJE_CLARO, pygame.Rect(0, 2, 5, 1))
    pygame.draw.rect(sprite, _PELAJE, pygame.Rect(5, 0, 3, 3))
    pygame.draw.rect(sprite, _PELAJE_CLARO, pygame.Rect(7, 0, 1, 1))
    pygame.draw.rect(sprite, _OJO, pygame.Rect(6, 1, 1, 1))
    pygame.draw.rect(sprite, _PELAJE, pygame.Rect(1, 4, 1, 2))
    pygame.draw.rect(sprite, _PELAJE, pygame.Rect(6, 4, 1, 2))
    return sprite


@cache
def _marcador_bayas() -> pygame.Surface:
    marcador = pygame.Surface((6, 4), pygame.SRCALPHA)
    pygame.draw.rect(marcador, _BAYA, pygame.Rect(1, 1, 2, 2))
    pygame.draw.rect(marcador, _BAYA, pygame.Rect(4, 0, 1, 1))
    pygame.draw.rect(marcador, _BAYA, pygame.Rect(0, 2, 1, 1))
    return marcador


@cache
def _marcador_caza() -> pygame.Surface:
    marcador = pygame.Surface((6, 4), pygame.SRCALPHA)
    pygame.draw.rect(marcador, _CAZA, pygame.Rect(0, 1, 5, 2))
    pygame.draw.rect(marcador, _CAZA, pygame.Rect(3, 0, 2, 1))
    return marcador


@lru_cache(maxsize=1)
def _fuente() -> pygame.font.Font:
    pygame.font.init()
    return pygame.font.SysFont(None, 14)
