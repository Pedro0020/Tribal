"""
Recursos del mundo: fuentes de agua, bayas y caza.

Cada recurso es finito (`cantidad`) y se regenera una unidad cada
`regeneracion` ticks hasta `capacidad`. Beber y comer los agotan, así que un
recurso muy visitado deja de servir y el individuo tiene que buscar otro.

Las fuentes se agrupan en **parches** (eje 3 de la hoja de ruta). Un parche de
comida agotado —su abundancia cae por debajo de un umbral— se reubica tras un
cooldown: la comida «migra» a otra zona y el parche vuelve a estar lleno. Eso
es lo que hace que seguir la presa pague y quedarse en la zona agotada mate.
"""

from __future__ import annotations

import math

from tribal.core.modelos import (
    Individuo,
    Mundo,
    Parche,
    Recurso,
    TipoRecurso,
    TipoTile,
)

CAPACIDAD = {TipoRecurso.AGUA: 40, TipoRecurso.BAYAS: 4, TipoRecurso.CAZA: 2}
#: Regeneración en ticks por unidad. Las bayas se reponen en 300 ticks (antes
#: 420): con el mapa más denso, la tribu puede sostener la población base; la
#: crisis recorta la capacidad a la mitad y vuelve a apretar sin secar el mundo.
REGENERACION = {TipoRecurso.AGUA: 10, TipoRecurso.BAYAS: 300, TipoRecurso.CAZA: 1500}
#: Margen de uso: para el agua, lo que se suma al radio del lago (beber desde la orilla).
ALCANCE = {TipoRecurso.AGUA: 1.5, TipoRecurso.BAYAS: 1.5, TipoRecurso.CAZA: 1.5}
#: Cuántas piezas de caza se reparten por el mapa.
N_CAZA = 8
#: Radio (en tiles) dentro del que dos fuentes del mismo tipo son el mismo parche.
RADIO_PARCHE = 4.0
#: Ticks mínimos entre dos migraciones del mismo parche: el mundo no es un
#: carrusel. `migrar` lo usa como espera máxima (parche lleno) y la acorta de
#: forma continua según la abundancia: un parche agotado espera 1/5. No hay
#: salto por régimen; la escasez es la que acelera el entorno.
TICKS_ENTRE_MIGRACIONES = 600
#: Una migración no es un paso al lado: la zona vieja se queda vacía y el
#: parche nuevo cae **fuera del horizonte del conformista** (4 tiles) y dentro
#: del divergente (14). Con 11, quien solo mira cerca no puede verlo; quien
#: explora, sí. Si un mapa no tiene casilla válida a esa distancia, `_reubicar`
#: no migra ese parche (no se fuerza un salto imposible).
DISTANCIA_MINIMA_MIGRACION = 11.0
#: Dos fuentes del mismo tipo no pueden acabar en la misma casilla. A 1.0 el
#: filtro deja pasar las vecinas y prohíbe el apilamiento: es lo que hacía
#: viable la migración de las bayas en el bosque.
DISTANCIA_ENTRE_FUENTES = 1.0


def parche_de(mundo: Mundo, recurso: Recurso) -> Parche | None:
    """Parche al que pertenece una fuente; `None` si no está en ninguno."""
    for parche in mundo.parches:
        if recurso.id in parche.fuentes:
            return parche
    return None


def sembrar(mundo: Mundo) -> None:
    """Reparte los recursos a partir del terreno ya generado. Idempotente."""
    mundo.recursos.clear()
    mundo.parches.clear()
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
        # Una mata por tile de bosque par: la densidad sostiene la tribu y deja
        # bosque libre para que los parches agotados puedan migrar.
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

    _agrupar(mundo)


def regenerar(mundo: Mundo, penalizacion: float = 1.0, factor: float = 1.0) -> None:
    """Un punto de recurso por intervalo; nunca por encima de la capacidad.

    `penalizacion` (sequía, concepto §13) baja la **capacidad de carga** del
    agua y las bayas: con 2.0 el tope se queda en la mitad. La regeneración
    conserva su ritmo, así que la sequía reduce la reserva disponible sin
    convertir el mapa en un desierto. La caza no se toca. Al reducir la
    capacidad también se recorta lo que hubiera de más, para que la sequía se
    note desde el primer tick y no solo cuando se agote la reserva.

    `factor` escala el ritmo de regeneración sin tocar la capacidad: en
    invierno vale 0.5 y el intervalo se dobla, así que la reserva se rellena a
    la mitad de velocidad. Con 1.0 el camino es exactamente el de Fase 0.
    """
    for recurso in mundo.recursos:
        capacidad = recurso.capacidad
        if penalizacion > 1.0 and recurso.tipo in (TipoRecurso.AGUA, TipoRecurso.BAYAS):
            capacidad = max(1, int(recurso.capacidad / penalizacion))
        recurso.cantidad = min(recurso.cantidad, capacidad)
        intervalo = (
            recurso.regeneracion
            if factor >= 1.0
            else max(1, math.ceil(recurso.regeneracion / factor))
        )
        if recurso.cantidad < capacidad and mundo.tick % intervalo == 0:
            recurso.cantidad += 1


def abundancia(mundo: Mundo, parche: Parche) -> float:
    """`cantidad / capacidad` del parche, en [0, 1]; 1 = lleno, 0 = agotado."""
    miembros = _miembros(mundo, parche)
    capacidad = sum(recurso.capacidad for recurso in miembros)
    if capacidad <= 0:
        return 0.0
    cantidad = sum(recurso.cantidad for recurso in miembros)
    return min(1.0, max(0.0, cantidad / capacidad))


def migrar(
    mundo: Mundo,
    *,
    umbral: float,
    cooldown: int | None = None,
    cooldown_min: int | None = None,
    cooldown_max: int | None = None,
) -> list[Parche]:
    """Reubica los parches de comida agotados; devuelve los que migraron este tick.

    Un parche está agotado cuando su abundancia cae por debajo de `umbral`: la
    zona ya no da para mantener a nadie. La espera desde la última migración
    **depende de la abundancia**: lleno espera `cooldown_max`, agotado
    `cooldown_min`, y en medio interpola linealmente. Así la escasez acelera el
    entorno de forma gradual, sin un salto binario por régimen. `cooldown`
    fija la espera para tests y llamadas puntuales.

    La zona nueva es del tipo de terreno que le toca a la comida —bosque para
    las bayas, hierba para la caza—, está a `DISTANCIA_MINIMA_MIGRACION` o más
    del centro viejo, tiene que caer en casillas pisables y no puede apilar una
    fuente sobre otra del mismo tipo (`DISTANCIA_ENTRE_FUENTES`).
    """
    maximo = cooldown_max if cooldown_max is not None else TICKS_ENTRE_MIGRACIONES
    minimo = cooldown_min if cooldown_min is not None else max(1, maximo // 5)
    migrados: list[Parche] = []
    for parche in mundo.parches:
        if parche.tipo == TipoRecurso.AGUA:
            continue
        disponible = abundancia(mundo, parche)
        espera = cooldown if cooldown is not None else minimo + (maximo - minimo) * disponible
        if mundo.tick - parche.tick_migracion < espera:
            continue
        if disponible >= umbral:
            continue
        miembros = _miembros(mundo, parche)
        if not miembros or not _reubicar(mundo, parche, miembros):
            continue
        parche.tick_migracion = mundo.tick
        parche.migraciones += 1
        migrados.append(parche)
    return migrados


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
    return mas_cercano_en_radio(mundo, individuo, tipos, math.inf)


def mas_cercano_en_radio(
    mundo: Mundo,
    individuo: Individuo,
    tipos: tuple[TipoRecurso, ...],
    radio: float,
) -> Recurso | None:
    """Como `mas_cercano`, pero solo ve lo que cae dentro de `radio` tiles.

    La percepción es conducta: un conformista busca cerca de donde está y un
    divergente mira más lejos. El radio no cambia lo que aporta el recurso, solo
    si el individuo sabe que está ahí.
    """
    mejor: Recurso | None = None
    mejor_clave = (math.inf, 0)
    radio2 = radio * radio
    for recurso in mundo.recursos:
        if recurso.tipo not in tipos or recurso.cantidad <= 0:
            continue
        dx = individuo.x - recurso.x
        dy = individuo.y - recurso.y
        distancia2 = dx * dx + dy * dy
        if distancia2 > radio2:
            continue
        clave = (distancia2, recurso.id)
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


def _agrupar(mundo: Mundo) -> None:
    """Agrupa las fuentes ya sembradas en parches por tipo y cercanía.

    Enlace simple: dos fuentes del mismo tipo a `RADIO_PARCHE` tiles o menos
    pertenecen al mismo parche, y la pertenencia se propaga. Se recorren por
    `id`, así que el reparto es determinista con la misma semilla.
    """
    siguiente_id = 1
    for tipo in (TipoRecurso.AGUA, TipoRecurso.BAYAS, TipoRecurso.CAZA):
        pendientes = sorted(
            (recurso for recurso in mundo.recursos if recurso.tipo == tipo),
            key=lambda recurso: recurso.id,
        )
        while pendientes:
            miembros = [pendientes.pop(0)]
            crecio = True
            while crecio:
                crecio = False
                for candidato in list(pendientes):
                    if any(
                        distancia(candidato.x, candidato.y, miembro.x, miembro.y) <= RADIO_PARCHE
                        for miembro in miembros
                    ):
                        miembros.append(candidato)
                        pendientes.remove(candidato)
                        crecio = True
            mundo.parches.append(_parche(siguiente_id, miembros))
            siguiente_id += 1


def _parche(id_: int, miembros: list[Recurso]) -> Parche:
    x = sum(recurso.x for recurso in miembros) / len(miembros)
    y = sum(recurso.y for recurso in miembros) / len(miembros)
    radio = max(distancia(x, y, recurso.x, recurso.y) for recurso in miembros)
    return Parche(
        id=id_,
        tipo=miembros[0].tipo,
        x=x,
        y=y,
        radio=radio,
        fuentes=[recurso.id for recurso in miembros],
    )


def _miembros(mundo: Mundo, parche: Parche) -> list[Recurso]:
    """Las fuentes del parche que siguen existiendo, en orden de `id`."""
    ids = set(parche.fuentes)
    return [recurso for recurso in mundo.recursos if recurso.id in ids]


def _reubicar(mundo: Mundo, parche: Parche, miembros: list[Recurso]) -> bool:
    """Traslada el parche a una zona nueva y lo rellena. False si no la encuentra.

    La zona nueva es del tipo de terreno que le toca a la comida —bosque para
    las bayas, hierba para la caza—, está a `DISTANCIA_MINIMA_MIGRACION` o más
    del centro viejo, tiene que caer en casillas pisables (nunca agua ni fuera
    del mapa) y no puede apilar una fuente sobre otra del mismo tipo
    (`DISTANCIA_ENTRE_FUENTES`).

    El orden de las casillas se sortea con `Mundo.azar` y se toma la primera
    que cumple: determinista por semilla y sin el fallo probabilístico de
    probar cuarenta al azar. El filtro se mide fuente a fuente —no parche a
    parche— a propósito: las bayas viven repartidas por los pocos tiles de
    bosque del mapa, y exigir holgura alrededor de cada mata dejaba la
    migración de bayas en cero. Apilar dos matas en una casilla es el único
    solape que importa. Cada fuente conserva su desplazamiento respecto al
    centro: el parche mantiene forma y radio.
    """
    terreno = TipoTile.BOSQUE if parche.tipo == TipoRecurso.BAYAS else TipoTile.HIERBA
    candidatas = [
        (x, y)
        for y, fila in enumerate(mundo.tiles)
        for x, tipo in enumerate(fila)
        if tipo == terreno
    ]
    if not candidatas:
        return False
    mundo.azar.shuffle(candidatas)
    desplazamientos = [
        (recurso.x - int(round(parche.x)), recurso.y - int(round(parche.y))) for recurso in miembros
    ]
    ids = set(parche.fuentes)
    otros = [
        (recurso.x, recurso.y)
        for recurso in mundo.recursos
        if recurso.tipo == parche.tipo and recurso.id not in ids
    ]
    for centro_x, centro_y in candidatas:
        if distancia(centro_x, centro_y, parche.x, parche.y) < DISTANCIA_MINIMA_MIGRACION:
            continue
        destino = [(centro_x + dx, centro_y + dy) for dx, dy in desplazamientos]
        if not all(mundo.pisable(x, y) for x, y in destino):
            continue
        if any(
            distancia(x, y, otro_x, otro_y) < DISTANCIA_ENTRE_FUENTES
            for x, y in destino
            for otro_x, otro_y in otros
        ):
            continue
        for recurso, (x, y) in zip(miembros, destino, strict=True):
            recurso.x, recurso.y = x, y
            recurso.cantidad = recurso.capacidad
        parche.x, parche.y = float(centro_x), float(centro_y)
        return True
    return False


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
