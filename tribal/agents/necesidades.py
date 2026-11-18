"""
Necesidades: evolución por tick y umbrales de urgencia.

La sed sube más rápido que la energía, y la salud solo cae cuando alguna de
las dos llega al límite. Cuando la salud llega a 0 el individuo muere; de eso
se encarga `tribal.sim`, no este módulo.
"""

from __future__ import annotations

from tribal.core.modelos import Genoma, Necesidades

#: Puntos de sed por tick (y de energía, que se gasta más despacio).
SED_POR_TICK = 0.16
ENERGIA_POR_TICK = 0.15
#: Salud que se pierde por tick mientras sed o energía están al límite.
DANO_SALUD = 0.6
#: Recuperación de salud por tick cuando las necesidades están cubiertas.
RECUPERACION_SALUD = 0.02
#: Umbrales de la política por defecto.
UMBRAL_SED = 60.0
UMBRAL_ENERGIA = 45.0
UMBRAL_AGOTAMIENTO = 10.0
UMBRAL_SALUD = 20.0


def evolucionar(
    necesidades: Necesidades,
    genoma: Genoma,
    tasa_sed: float = SED_POR_TICK,
    tasa_energia: float = ENERGIA_POR_TICK,
    tasa_salud: float = DANO_SALUD,
) -> None:
    """Un tick de homeostasis. El metabolismo del genoma escala el desgaste.

    Las tasas llegan de `SimConfig`; los defaults son los de Fase 0 para quien
    llame a este módulo sin configuración.
    """
    necesidades.sed = min(100.0, necesidades.sed + tasa_sed * genoma.metabolismo)
    necesidades.energia = max(0.0, necesidades.energia - tasa_energia * genoma.metabolismo)
    if necesidades.sed >= 100.0 or necesidades.energia <= 0.0:
        necesidades.salud = max(0.0, necesidades.salud - tasa_salud * genoma.metabolismo)
    else:
        necesidades.salud = min(100.0, necesidades.salud + RECUPERACION_SALUD)


def sed_critica(necesidades: Necesidades) -> bool:
    return necesidades.sed >= UMBRAL_SED


def energia_baja(necesidades: Necesidades) -> bool:
    return necesidades.energia <= UMBRAL_ENERGIA


def agotado(necesidades: Necesidades) -> bool:
    """Sin energía para seguir caminando: toca parar, aunque haya hambre."""
    return necesidades.energia <= UMBRAL_AGOTAMIENTO


def salud_critica(necesidades: Necesidades) -> bool:
    return necesidades.salud <= UMBRAL_SALUD
