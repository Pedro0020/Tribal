"""Hojas de contacto y mockup del kit de arte de Tribal.

Lee los PNG originales de ``raw/`` (salida del MCP de PixelLab), los cuantiza
a la paleta de ``palette.json`` y escribe:

  kit-16px/            arte final, ya con la paleta cerrada
  kit-8px/             lo mismo a la mitad, para TILE_PX=8
  hoja-personajes.png  los 4 personajes x 8 direcciones, a 4x
  hoja-objetos.png     props y tilesets, a 4x
  mockup-16px.png      escena 60x34 tiles a 16 px (960x544)
  mockup-8px.png       la misma escena a 8 px

Solo depende de pygame-ce (ya en el proyecto). No toca el juego: ``tribal/``
no se importa ni se modifica.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

import pygame

RAIZ = Path(__file__).resolve().parent
RAW = RAIZ / "raw"
KIT = RAIZ / "kit-16px"
TILE = 16
Z = 4  # zoom de las hojas de contacto

PERSONAJES = {
    "anciano": "Anciano-Idle.png",
    "cazador": "Cazador-Idle.png",
    "recolectora": "Recolectora-Idle.png",
    "chaman": "Chaman-Idle.png",
}
PROPS = {
    "tipi": "tipi.png",
    "campfire": "campfire.png",
    "rocas": "rocas.png",
    "bayas": "bayas.png",
    "silex": "silex.png",
    "cueva": "cueva.png",
    "acacia": "acacia.png",
}
TILESETS = {
    "agua-hierba": "agua-hierba-v2.png",
    "hierba-bosque": "hierba-bosque.png",
    "tierra-hierba": "tierra-hierba-verde.png",
    "agua-hierba-seca": "agua-hierba-seca.png",
}

ANCHO_TILES, ALTO_TILES = 60, 34


# --------------------------------------------------------------------------
# paleta
# --------------------------------------------------------------------------


def cargar_paleta() -> dict[str, tuple[int, int, int]]:
    datos = json.loads((RAIZ / "palette.json").read_text(encoding="utf-8"))
    colores = {}
    for entrada in datos["colors"]:
        limpio = entrada["hex"].lstrip("#")
        colores[entrada["name"]] = tuple(int(limpio[i : i + 2], 16) for i in (0, 2, 4))
    return colores


def _distancia(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


class Cuantizador:
    """Mapea cada color al mas cercano de la paleta, con cache."""

    def __init__(self, paleta: dict[str, tuple[int, int, int]]) -> None:
        self.paleta = list(paleta.values())
        self._cache: dict[tuple[int, int, int], tuple[int, int, int]] = {}

    def __call__(self, color: tuple[int, int, int]) -> tuple[int, int, int]:
        cercano = self._cache.get(color)
        if cercano is None:
            cercano = min(self.paleta, key=lambda p: _distancia(color, p))
            self._cache[color] = cercano
        return cercano

    def superficie(self, original: pygame.Surface) -> pygame.Surface:
        salida = pygame.Surface(original.get_size(), pygame.SRCALPHA)
        ancho, alto = original.get_size()
        for y in range(alto):
            for x in range(ancho):
                r, g, b, a = original.get_at((x, y))
                if a == 0:
                    continue
                salida.set_at((x, y), (*self((r, g, b)), a))
        return salida


# --------------------------------------------------------------------------
# carga
# --------------------------------------------------------------------------


def cargar(ruta: Path) -> pygame.Surface:
    return pygame.image.load(str(ruta)).convert_alpha()


def cuantizar_carpeta(cuanti: Cuantizador) -> dict[str, pygame.Surface]:
    """Copia todo raw/ a kit-16px/ ya cuantizado y devuelve las superficies."""
    piezas: dict[str, pygame.Surface] = {}

    for nombre, fichero in PERSONAJES.items():
        surf = cuanti.superficie(cargar(RAW / "chars" / nombre / fichero))
        (KIT / "personajes").mkdir(parents=True, exist_ok=True)
        pygame.image.save(surf, str(KIT / "personajes" / f"{nombre}.png"))
        piezas[f"personaje:{nombre}"] = surf

    for nombre, fichero in PROPS.items():
        surf = cuanti.superficie(cargar(RAW / "props" / fichero))
        (KIT / "props").mkdir(parents=True, exist_ok=True)
        pygame.image.save(surf, str(KIT / "props" / f"{nombre}.png"))
        piezas[f"prop:{nombre}"] = surf

    for nombre, fichero in TILESETS.items():
        surf = cuanti.superficie(cargar(RAW / "tilesets" / fichero))
        (KIT / "tilesets").mkdir(parents=True, exist_ok=True)
        pygame.image.save(surf, str(KIT / "tilesets" / f"{nombre}.png"))
        piezas[f"tileset:{nombre}"] = surf

    keyart = cuanti.superficie(cargar(RAW / "props" / "keyart-campamento.png"))
    pygame.image.save(keyart, str(KIT / "keyart-campamento.png"))
    piezas["keyart"] = keyart
    return piezas


# --------------------------------------------------------------------------
# tilesets Wang
# --------------------------------------------------------------------------


class TilesetWang:
    """Un PNG 4x4 de 16 tiles y su metadata: esquinas -> rect."""

    def __init__(self, png: Path, metadata: Path, lower: str) -> None:
        self.sheet = cargar(png)
        self.lower = lower
        datos = json.loads(metadata.read_text(encoding="utf-8"))
        self.tiles: list[tuple[tuple[str, str, str, str], pygame.Rect]] = []
        for tile in datos["tileset_data"]["tiles"]:
            caja = tile["bounding_box"]
            esquinas = tuple(tile["corners"][k] for k in ("NW", "NE", "SW", "SE"))
            self.tiles.append((esquinas, pygame.Rect(caja["x"], caja["y"], caja["width"], caja["height"])))

    def buscar(self, esquinas: tuple[str, str, str, str]) -> pygame.Surface:
        for candidatas, rect in self.tiles:
            if candidatas == esquinas:
                return self.sheet.subsurface(rect)
        return self.sheet.subsurface(self.tiles[0][1])

    def tile(self, terreno: str, esquinas: dict[str, str]) -> pygame.Surface:
        """Traduce 4 terrenos (NW, NE, SW, SE) a una de las 16 piezas."""
        claves = tuple("lower" if esquinas[k] == self.lower else "upper" for k in ("NW", "NE", "SW", "SE"))
        return self.buscar(claves)


def cargar_tilesets() -> dict[str, TilesetWang]:
    return {
        "agua": TilesetWang(KIT / "tilesets" / "agua-hierba.png", RAW / "tilesets" / "agua-hierba-v2.json", "agua"),
        "bosque": TilesetWang(KIT / "tilesets" / "hierba-bosque.png", RAW / "tilesets" / "hierba-bosque.json", "bosque"),
        "tierra": TilesetWang(KIT / "tilesets" / "tierra-hierba.png", RAW / "tilesets" / "tierra-hierba-verde.json", "tierra"),
    }


# --------------------------------------------------------------------------
# variantes de hierba (rompen la repeticion sin salirse de la paleta)
# --------------------------------------------------------------------------


def variantes_hierba(base: pygame.Surface, paleta: dict[str, tuple[int, int, int]], n: int = 6) -> list[pygame.Surface]:
    """Devuelve ``n`` versiones del tile de hierba con matas distintas.

    Solo se tocan pixeles interiores (1..14) para no romper las costuras, y
    todos los colores salen de la paleta. La variante 0 es el tile original.
    """
    tonos = [paleta["grass-dark"], paleta["grass-light"], paleta["leaf"]]
    salida = [base]
    for k in range(1, n):
        surf = base.copy()
        rnd = random.Random(7919 * k)
        for _ in range(4):
            x, y = rnd.randint(2, 13), rnd.randint(2, 13)
            tono = rnd.choice(tonos)
            forma = rnd.choice(
                [
                    [(0, 0), (1, 0), (2, 0)],
                    [(0, 0), (0, 1), (0, 2)],
                    [(0, 0), (1, 0), (0, 1), (1, 1)],
                    [(0, 0), (0, 1), (1, 1)],
                    [(0, 0), (1, 1), (2, 2)],
                ]
            )
            for dx, dy in forma:
                if 1 <= x + dx <= 14 and 1 <= y + dy <= 14:
                    surf.set_at((x + dx, y + dy), tono)
        salida.append(surf)
    return salida


# --------------------------------------------------------------------------
# el mapa
# --------------------------------------------------------------------------


def _catmull(p0: float, p1: float, p2: float, p3: float, t: float) -> float:
    return 0.5 * (
        2 * p1
        + (-p0 + p2) * t
        + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
        + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t
    )


# El rio entra arriba por la izquierda, se abre a la derecha y vuelve a
# cerrarse abajo: un meandro de verdad, no una banda vertical.
CONTROL_RIO = [(0, 14.0), (5, 17.5), (10, 19.0), (15, 16.0), (20, 11.0), (25, 8.5), (30, 10.5), (33, 12.0)]


def centro_rio(y: float) -> float:
    if y <= CONTROL_RIO[0][0]:
        return CONTROL_RIO[0][1]
    if y >= CONTROL_RIO[-1][0]:
        return CONTROL_RIO[-1][1]
    for i in range(len(CONTROL_RIO) - 1):
        y0, x0 = CONTROL_RIO[i]
        y1, x1 = CONTROL_RIO[i + 1]
        if y0 <= y <= y1:
            t = (y - y0) / (y1 - y0)
            p0 = CONTROL_RIO[max(i - 1, 0)][1]
            p3 = CONTROL_RIO[min(i + 2, len(CONTROL_RIO) - 1)][1]
            return _catmull(p0, x0, x1, p3, t)
    return CONTROL_RIO[-1][1]


def ancho_rio(y: float) -> float:
    base = 1.9 + 0.7 * math.sin(y * 0.21 + 0.7) + 0.4 * math.sin(y * 0.07)
    if 16 <= y <= 22:  # vado: el cauce se estrecha poco a poco
        d = abs(y - 19) / 3
        base *= 0.55 + 0.45 * d * d
    return max(1.5, base)


CAMPAMENTO = (35, 19)
CLARO = 7.5
SEMILLAS_BOSQUE = [(6, 6, 3.6), (7, 24, 4.0), (19, 4, 3.0), (24, 27, 3.8), (16, 13, 2.6), (45, 4, 3.4), (53, 27, 3.2), (47, 14, 2.4), (12, 31, 2.2)]


def en_claro(x: int, y: int) -> bool:
    return math.hypot(x - CAMPAMENTO[0], (y - CAMPAMENTO[1]) * 0.9) < CLARO


def zona_libre(rejilla: list[list[str]], x: int, y: int, radio: int = 1, permitido: tuple[str, ...] = ("hierba",)) -> bool:
    """True si la celda y su entorno no tienen agua ni senderos."""
    for yy in range(y - radio, y + radio + 1):
        for xx in range(x - radio, x + radio + 1):
            if not (0 <= xx < ANCHO_TILES and 0 <= yy < ALTO_TILES):
                return False
            if rejilla[yy][xx] not in permitido:
                return False
    return True


def posiciones_arboles(rejilla: list[list[str]]) -> list[tuple[int, int]]:
    """Arboles con separacion minima: manchas de bosque, no una alfombra."""
    rnd = random.Random(20261119)
    sitios: list[tuple[int, int]] = []
    for sx, sy, radio in SEMILLAS_BOSQUE:
        for _ in range(int(radio * radio * 2.2)):
            ang, dist = rnd.uniform(0, 2 * math.pi), rnd.uniform(0, radio)
            x = int(round(sx + math.cos(ang) * dist))
            y = int(round(sy + math.sin(ang) * dist * 0.85))
            if not (0 <= x < ANCHO_TILES and 0 <= y < ALTO_TILES):
                continue
            if rejilla[y][x] != "hierba" or en_claro(x, y):
                continue
            if not zona_libre(rejilla, x, y, 1, ("hierba",)):
                continue
            if any((x - px) ** 2 + (y - py) ** 2 < 2.0**2 for px, py in sitios):
                continue
            sitios.append((x, y))
    return sitios


def construir_terreno() -> tuple[list[list[str]], list[tuple[int, int]]]:
    """Rejilla de terreno y donde van los arboles.

    El suelo de bosque se pinta solo bajo un arbol: asi el marron se lee como
    hojarasca bajo la copa y no como una mancha suelta en mitad de la hierba.
    """
    rejilla = [["hierba"] * ANCHO_TILES for _ in range(ALTO_TILES)]

    # rio
    for y in range(ALTO_TILES):
        c, w = centro_rio(y), ancho_rio(y)
        for x in range(ANCHO_TILES):
            if abs(x - c) <= w:
                rejilla[y][x] = "agua"

    arboles = posiciones_arboles(rejilla)
    for x, y in arboles:
        rejilla[y][x] = "bosque"

    # sendero: cruza por el vado y sigue por la otra orilla; rama al norte
    y_cruce = 19
    c, w = centro_rio(y_cruce), ancho_rio(y_cruce)
    x_este = int(math.ceil(c + w)) + 1
    x_oeste = int(math.floor(c - w)) - 1
    for puntos in (
        [(35, 20), (32, 21), (27, 21), (21, 20), (x_este, y_cruce)],
        [(x_oeste, y_cruce), (x_oeste - 3, 23), (x_oeste - 7, 27)],
        [(35, 20), (38, 15), (42, 10), (46, 8)],
    ):
        for (x0, y0), (x1, y1) in zip(puntos, puntos[1:], strict=False):
            pasos = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
            for i in range(pasos + 1):
                t = i / pasos
                px = round(x0 + (x1 - x0) * t)
                py = round(y0 + (y1 - y0) * t)
                ancho = ((0, 0), (1, 0)) if i % 5 == 0 else ((0, 0),)
                for dx, dy in ancho:
                    x, y = px + dx, py + dy
                    if 0 <= x < ANCHO_TILES and 0 <= y < ALTO_TILES and rejilla[y][x] in ("hierba", "bosque"):
                        rejilla[y][x] = "tierra"

    return rejilla, arboles


def esquinas_de(rejilla: list[list[str]], x: int, y: int) -> dict[str, str]:
    def t(cx: int, cy: int) -> str:
        return rejilla[min(max(cy, 0), ALTO_TILES - 1)][min(max(cx, 0), ANCHO_TILES - 1)]

    return {"NW": t(x - 1, y - 1), "NE": t(x, y - 1), "SW": t(x - 1, y), "SE": t(x, y)}


def tile_para(rejilla, x: int, y: int, sets, variantes) -> pygame.Surface:
    propio = rejilla[y][x]
    esquinas = esquinas_de(rejilla, x, y)
    valores = set(esquinas.values())

    if propio == "agua" or "agua" in valores:
        pieza = sets["agua"].tile("agua", esquinas)
    elif propio == "tierra" or "tierra" in valores:
        pieza = sets["tierra"].tile("tierra", esquinas)
    elif propio == "bosque" or "bosque" in valores:
        pieza = sets["bosque"].tile("bosque", esquinas)
    else:
        # variantes en manchas de 4x4: rompe la repeticion sin ruido pixel a pixel
        pieza = variantes[((x // 4) * 7 + (y // 4) * 13) % len(variantes)]
    return pieza


# --------------------------------------------------------------------------
# dibujo
# --------------------------------------------------------------------------


def sombra(lienzo: pygame.Surface, cx: int, cy: int, rx: int, ry: int, color) -> None:
    """Sombra de contacto: dither al 25% para no inventar colores."""
    for y in range(cy - ry, cy + ry + 1):
        for x in range(cx - rx, cx + rx + 1):
            dx, dy = (x - cx) / max(rx, 1), (y - cy) / max(ry, 1)
            if (
                dx * dx + dy * dy <= 1.0
                and x % 2 == 0
                and y % 2 == 0
                and 0 <= x < lienzo.get_width()
                and 0 <= y < lienzo.get_height()
            ):
                lienzo.set_at((x, y), color)


def mockup(piezas: dict[str, pygame.Surface], paleta: dict[str, tuple[int, int, int]]) -> pygame.Surface:
    lienzo = pygame.Surface((ANCHO_TILES * TILE, ALTO_TILES * TILE))
    sets = cargar_tilesets()
    variantes = variantes_hierba(sets["agua"].buscar(("upper",) * 4), paleta)

    rejilla, arboles = construir_terreno()
    for y in range(ALTO_TILES):
        for x in range(ANCHO_TILES):
            lienzo.blit(tile_para(rejilla, x, y, sets, variantes), (x * TILE, y * TILE))

    # vado: corrientes cortas en la franja estrecha y piedras de paso
    claro = paleta["water-light"]
    for y in range(18, 21):
        for x in range(ANCHO_TILES):
            if rejilla[y][x] != "agua":
                continue
            for py in (y * TILE + 6, y * TILE + 11):
                for px in range(x * TILE + 1, x * TILE + TILE - 3, 6):
                    for d in (0, 1, 2):
                        lienzo.set_at((px + d, py), claro)

    piedra, piedra_osc = paleta["stone"], paleta["stone-dark"]
    c_vado, w_vado = centro_rio(19), ancho_rio(19)
    for i in range(3):
        px = int((c_vado - w_vado + (i + 0.5) * (2 * w_vado) / 3) * TILE)
        py = 19 * TILE + 7 + (i % 2) * 2
        for dy in range(-1, 2):
            for dx in range(-2, 3):
                if abs(dx) + abs(dy) * 2 <= 3:
                    lienzo.set_at((px + dx, py + dy), piedra if dy < 1 else piedra_osc)

    cosas: list[tuple[pygame.Surface, int, int]] = []

    for x, y in arboles:
        cosas.append((piezas["prop:acacia"], x * TILE - 16, y * TILE - 26))

    # campamento
    cosas.append((piezas["prop:campfire"], 34 * TILE, 19 * TILE))
    cosas.append((piezas["prop:tipi"], 31 * TILE - 8, 17 * TILE - 18))
    cosas.append((piezas["prop:tipi"], 37 * TILE - 8, 18 * TILE - 18))
    cosas.append((piezas["prop:tipi"], 34 * TILE - 8, 22 * TILE - 18))
    cosas.append((piezas["prop:silex"], 37 * TILE, 21 * TILE))
    cosas.append((piezas["prop:bayas"], 27 * TILE, 16 * TILE))

    # matorrales sueltos en la hierba abierta
    rnd = random.Random(555)
    puestos = 0
    for _ in range(80):
        if puestos >= 10:
            break
        x, y = rnd.randint(2, ANCHO_TILES - 3), rnd.randint(2, ALTO_TILES - 3)
        if rejilla[y][x] == "hierba" and not en_claro(x, y) and zona_libre(rejilla, x, y, 1, ("hierba",)):
            cosas.append((piezas["prop:bayas"], x * TILE - 4, y * TILE - 6))
            puestos += 1

    # saliente rocosa al noreste, con la cueva encima
    cosas.append((piezas["prop:rocas"], 47 * TILE - 8, 5 * TILE - 16))
    cosas.append((piezas["prop:rocas"], 50 * TILE - 8, 7 * TILE - 16))
    cosas.append((piezas["prop:rocas"], 45 * TILE - 8, 8 * TILE - 16))
    cosas.append((piezas["prop:cueva"], 49 * TILE - 8, 2 * TILE - 12))

    alrededor = [("cazador", 33, 17), ("recolectora", 36, 20), ("anciano", 32, 21), ("chaman", 38, 16)]
    for nombre, tx, ty in alrededor:
        sheet = piezas[f"personaje:{nombre}"]
        cosas.append((sheet.subsurface((0, 0, 48, 48)), tx * TILE - 16, ty * TILE - 32))

    cosas.sort(key=lambda c: c[2] + c[0].get_height())
    for surf, px, py in cosas:
        sombra(lienzo, px + surf.get_width() // 2, py + surf.get_height() - 6, surf.get_width() // 4, 3, paleta["forest"])
        lienzo.blit(surf, (px, py))
    return lienzo


# --------------------------------------------------------------------------
# hojas de contacto
# --------------------------------------------------------------------------


def _fuente(tam: int) -> pygame.font.Font:
    pygame.font.init()
    return pygame.font.SysFont("consolas", tam)


def hoja_personajes(piezas: dict[str, pygame.Surface]) -> pygame.Surface:
    celda = 48 * Z
    margen = 12
    cabecera = 30
    filas = len(PERSONAJES)
    ancho = margen * 2 + celda * 8 + 120
    alto = cabecera + (celda + margen) * filas
    hoja = pygame.Surface((ancho, alto))
    hoja.fill((24, 22, 24))
    fuente = _fuente(18)
    hoja.blit(fuente.render("8 direcciones - fila = personaje", False, (240, 230, 210)), (margen, 6))

    for fila, nombre in enumerate(PERSONAJES):
        y = cabecera + fila * (celda + margen)
        hoja.blit(fuente.render(nombre, False, (244, 201, 93)), (margen, y + celda // 2))
        sprite_sheet = piezas[f"personaje:{nombre}"]
        for col in range(8):
            celda_surf = sprite_sheet.subsurface((col * 48, 0, 48, 48))
            grande = pygame.transform.scale(celda_surf, (celda, celda))
            x = margen + 110 + col * celda
            fondo = pygame.Surface((celda, celda))
            fondo.fill((62, 88, 48) if (fila + col) % 2 else (72, 98, 56))
            hoja.blit(fondo, (x, y))
            hoja.blit(grande, (x, y))
    return hoja


def hoja_objetos(piezas: dict[str, pygame.Surface]) -> pygame.Surface:
    hoja = pygame.Surface((1130, 700))
    hoja.fill((24, 22, 24))
    fuente = _fuente(18)
    titulo = _fuente(20)

    x, y = 12, 8
    for nombre in PROPS:
        surf = piezas[f"prop:{nombre}"]
        grande = pygame.transform.scale(surf, (surf.get_width() * Z, surf.get_height() * Z))
        hoja.blit(titulo.render(nombre, False, (244, 201, 93)), (x, y))
        hoja.blit(grande, (x, y + 26))
        x += max(grande.get_width(), 130) + 26
        if x > 840:
            x, y = 12, y + 240

    y += 240
    x = 12
    hoja.blit(titulo.render("tilesets (16x16, Wang 4x4)", False, (244, 201, 93)), (x, y))
    y += 26
    for nombre in TILESETS:
        surf = piezas[f"tileset:{nombre}"]
        grande = pygame.transform.scale(surf, (surf.get_width() * Z, surf.get_height() * Z))
        hoja.blit(fuente.render(nombre, False, (232, 226, 210)), (x, y))
        hoja.blit(grande, (x, y + 22))
        x += grande.get_width() + 16
    return hoja


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def escalar_kit() -> None:
    """Copia kit-16px/ a kit-8px/ a la mitad, para el TILE_PX=8 de hoy."""
    for origen in KIT.rglob("*.png"):
        destino = KIT.parent / "kit-8px" / origen.relative_to(KIT)
        destino.parent.mkdir(parents=True, exist_ok=True)
        surf = cargar(origen)
        mitad = (max(1, surf.get_width() // 2), max(1, surf.get_height() // 2))
        pygame.image.save(pygame.transform.scale(surf, mitad), str(destino))


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    KIT.mkdir(parents=True, exist_ok=True)

    paleta = cargar_paleta()
    cuanti = Cuantizador(paleta)
    piezas = cuantizar_carpeta(cuanti)

    pygame.image.save(hoja_personajes(piezas), str(RAIZ / "hoja-personajes.png"))
    pygame.image.save(hoja_objetos(piezas), str(RAIZ / "hoja-objetos.png"))

    escena = mockup(piezas, paleta)
    pygame.image.save(escena, str(RAIZ / "mockup-16px.png"))
    pygame.image.save(
        pygame.transform.scale(escena, (escena.get_width() // 2, escena.get_height() // 2)),
        str(RAIZ / "mockup-8px.png"),
    )

    escalar_kit()

    print("kit cuantizado en kit-16px/ y kit-8px/")
    print("hojas: hoja-personajes.png, hoja-objetos.png")
    print("mockups: mockup-16px.png, mockup-8px.png")


if __name__ == "__main__":
    main()
