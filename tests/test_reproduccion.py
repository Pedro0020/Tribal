"""FIX-ENERGIA: la reproducción conserva la energía, sin inyección neta.

Un nacimiento no puede crear energía: la cría nace con lo que la madre paga, y
la crisis no cambia ni el umbral ni el coste — si no, la sequía sería el régimen
favorable y la población crecería por subsidio reproductivo (concepto §13).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tribal.config import SimConfig
from tribal.core import mundo as modulo_mundo
from tribal.core.modelos import Individuo, Mundo
from tribal.sim import ENERGIA_CRIA, UMBRAL_REPRODUCCION, Simulacion, crear

RAIZ = Path(__file__).resolve().parents[1]
#: Ventana del test de población: la misma que el resto de la puerta F1.
TICKS = 8000
SEMILLAS = (1, 2, 3)
#: La simulación es caótica: dos corridas gemelas divergen en cuanto una consume
#: el azar de otra forma. El margen descarta el subsidio (una crisis *más*
#: fértil), no la décima de diferencia que deja el ruido de la semilla.
MARGEN_RUIDO = 1.10


def _pareja(simulacion: Simulacion, energia: float) -> tuple[Individuo, Individuo]:
    """Una madre y un padre adultos, sin cooldown, juntos y con esa energía."""
    madre = next(i for i in simulacion.mundo.individuos if i.sexo == "f")
    padre = next(i for i in simulacion.mundo.individuos if i.sexo == "m")
    for individuo in (madre, padre):
        individuo.edad = individuo.madurez
        individuo.cooldown_reproduccion = 0
        individuo.necesidades.energia = energia
    padre.x, padre.y = madre.x, madre.y
    return madre, padre


def _energia_total(mundo: Mundo) -> float:
    return sum(individuo.necesidades.energia for individuo in mundo.individuos)


def test_la_cria_nace_con_lo_que_paga_la_madre() -> None:
    """70/70, justo por encima del umbral: la madre pierde 50 exactos."""
    simulacion = crear(1, 12)
    madre, padre = _pareja(simulacion, 70.0)
    antes = madre.necesidades.energia + padre.necesidades.energia

    simulacion._reproducir()

    assert simulacion.nacimientos == 1
    hijo = simulacion.mundo.individuos[-1]
    assert hijo.necesidades.energia <= ENERGIA_CRIA
    assert madre.necesidades.energia == pytest.approx(70.0 - ENERGIA_CRIA)
    assert madre.necesidades.energia + padre.necesidades.energia + hijo.necesidades.energia <= (
        antes
    )


def test_la_madre_no_paga_mas_de_lo_que_tiene() -> None:
    """Sin pasar por el umbral, la cría recibe lo que hay: la energía no se crea."""
    simulacion = crear(1, 12)
    madre, padre = _pareja(simulacion, 30.0)
    antes = _energia_total(simulacion.mundo)

    simulacion._nacer(madre, padre)

    hijo = simulacion.mundo.individuos[-1]
    assert madre.necesidades.energia == pytest.approx(0.0)
    assert hijo.necesidades.energia == pytest.approx(30.0)
    assert _energia_total(simulacion.mundo) == pytest.approx(antes)


def test_una_pareja_sin_energia_suficiente_no_cria() -> None:
    """Por debajo del umbral no hay hijo, y el umbral es el mismo en crisis."""
    for crisis in (False, True):
        simulacion = crear(1, 12, config=SimConfig(seed=1, individuos=12, crisis=crisis))
        madre, padre = _pareja(simulacion, UMBRAL_REPRODUCCION - 1.0)

        simulacion._reproducir()

        assert simulacion.nacimientos == 0
        assert simulacion._puede_reproducir(madre) is False
        assert simulacion._puede_reproducir(padre) is False


def test_la_crisis_no_tiene_umbral_de_reproduccion_propio() -> None:
    """Guarda de código (como la de la divergencia): el régimen no toca criar."""
    fuente = (RAIZ / "tribal" / "sim.py").read_text(encoding="utf-8")
    arbol = ast.parse(fuente)

    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign | ast.AnnAssign):
            for destino in nodo.targets if isinstance(nodo, ast.Assign) else [nodo.target]:
                nombre = getattr(destino, "id", "")
                assert not ("UMBRAL" in nombre.upper() and "CRISIS" in nombre.upper()), (
                    f"reaparece un umbral de reproducción por régimen: {nombre}"
                )

    funciones = {nodo.name: nodo for nodo in ast.walk(arbol) if isinstance(nodo, ast.FunctionDef)}
    for nombre in ("_umbral_reproduccion", "_puede_reproducir", "_reproducir", "_nacer"):
        for referencia_nodo in ast.walk(funciones[nombre]):
            referencia = (
                getattr(referencia_nodo, "id", None) or getattr(referencia_nodo, "attr", None) or ""
            )
            assert "crisis" not in referencia.lower(), (
                f"{nombre} lee {referencia}: criar no puede depender del régimen"
            )


class _SimulacionAuditada(Simulacion):
    """Simulación que anota la energía neta que crea cada nacimiento."""

    def __init__(self, mundo: Mundo, config: SimConfig) -> None:
        super().__init__(mundo, config)
        self.balance: list[float] = []

    def _nacer(self, madre: Individuo, padre: Individuo) -> None:
        antes = _energia_total(self.mundo)
        super()._nacer(madre, padre)
        self.balance.append(_energia_total(self.mundo) - antes)


def _partida(seed: int, *, crisis: bool) -> tuple[int, int, list[float]]:
    """Nacimientos, persona-ticks y balance de cada nacimiento en 8000 ticks."""
    config = SimConfig(seed=seed, individuos=12, crisis=crisis)
    simulacion = _SimulacionAuditada(modulo_mundo.crear(seed, 12, config=config), config)
    persona_ticks = 0
    for _ in range(TICKS):
        simulacion.step()
        persona_ticks += simulacion.poblacion
    return simulacion.nacimientos, persona_ticks, simulacion.balance


def test_la_crisis_no_es_mas_fertil_que_la_calma() -> None:
    """En una sequía no nacen más crías por persona-tick que en calma."""
    tasa: dict[bool, float] = {}
    for crisis in (False, True):
        nacimientos = persona_ticks = 0
        for seed in SEMILLAS:
            partida, ticks_persona, balance = _partida(seed, crisis=crisis)
            assert all(abs(delta) < 1e-9 for delta in balance), (
                f"seed={seed} crisis={crisis}: un nacimiento inyectó energía"
            )
            nacimientos += partida
            persona_ticks += ticks_persona
        tasa[crisis] = nacimientos / persona_ticks * 1000

    assert tasa[True] <= tasa[False] * MARGEN_RUIDO, (
        f"la crisis es más fértil: {tasa[True]:.3f} contra {tasa[False]:.3f} "
        f"nacimientos por 1000 persona-ticks"
    )
