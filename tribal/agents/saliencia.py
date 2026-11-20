"""
Saliencia: el peso narrativo que un individuo ha **ganado** (concepto §10b).

No es un rasgo del genoma ni se parece a `divergencia` (§9b): la divergencia es
temperamento —cómo de lejos se desvía alguien del grupo— y la saliencia es
historia —cuánto protagonismo ha acumulado por sus actos—. Un conformista que
guarda la tradición puede ser más saliente que el divergente cuyas ideas nunca
cuajaron, y al revés. Por eso este módulo no lee `genoma`: solo suma hitos y
deja que el tiempo los gaste.

La saliencia decide **quién piensa** cuando el presupuesto de LLM no llega a
todos los dilemas del tick (`Simulacion._encolar_dilema`): los de más peso
narrativo entran primero en la cola y los demás siguen por instinto.
"""

from __future__ import annotations

from tribal.core.modelos import Individuo

#: Cuánto sube la saliencia cada tipo de hito. Los motivos son eventos del
#: motor, nunca el temperamento: descubrir un cruce pesa más que enseñar una
#: técnica, y sobrevivir a una crisis se premia en bloque y por superviviente.
SUBIDA: dict[str, float] = {
    "primer_nodo": 1.0,
    "combinacion": 1.5,
    "tradicion": 1.0,
    # Efecto cultural de una tradición viva: el descubrimiento de esa rama
    # pesa un poco más en la memoria del grupo.
    "tradicion_practica": 0.25,
    "ensenanza": 0.4,
    "rescate": 0.6,
    "crisis": 0.5,
}
#: Factor de decaimiento por tick: un hito de 1.0 tarda ~693 ticks en valer 0.5.
#: Es determinista, sin azar, para que dos corridas con la misma semilla midan
#: exactamente la misma historia.
DECAIMIENTO = 0.999
#: Techo del peso narrativo: la saliencia separa a unos de otros, no los hace
#: infinitamente distintos ni desborda el presupuesto de la cola.
SALIENCIA_MAX = 10.0
#: Ticks seguidos de crisis que hay que sobrevivir para ganar el hito "crisis".
TICKS_CRISIS = 600


def subir(individuo: Individuo, motivo: str) -> None:
    """Suma el peso de un hito, con techo. Un motivo desconocido es un error."""
    if motivo not in SUBIDA:
        raise ValueError(f"motivo de saliencia desconocido: {motivo!r}")
    individuo.saliencia = min(SALIENCIA_MAX, individuo.saliencia + SUBIDA[motivo])


def decaer(individuo: Individuo) -> None:
    """Un tick de olvido: el protagonismo se gana, pero no se conserva solo."""
    individuo.saliencia *= DECAIMIENTO
