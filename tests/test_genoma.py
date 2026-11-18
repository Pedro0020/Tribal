"""Genoma: rasgos, herencia acotada y determinista, y media que se mantiene."""

from __future__ import annotations

import random
import statistics

from tribal.core import mundo as modulo_mundo
from tribal.core.genoma import (
    DIVERGENCIA_MAX,
    DIVERGENCIA_MIN,
    MUTACION,
    RASGO_MAX,
    RASGO_MIN,
    RASGOS,
    Genoma,
    heredar,
)
from tribal.sim import run

#: Los siete rasgos funcionales; `divergencia` tiene su propio rango.
FUNCIONALES = RASGOS[:-1]
#: Rasgos que en F1-001 estrenan varianza en la generación fundadora.
NUEVOS = ("fuerza", "resistencia", "inteligencia", "salud")


def test_los_ocho_rasgos_con_defaults_neutros() -> None:
    genoma = Genoma()

    for rasgo in FUNCIONALES:
        assert getattr(genoma, rasgo) == 1.0
    assert genoma.divergencia == 0.5
    assert set(RASGOS) == set(Genoma.__dataclass_fields__)


def test_cien_nacimientos_quedan_en_rango_y_la_media_se_mantiene() -> None:
    # `fuerza` tiene una media de 0.6 a propósito: con una mutación absoluta de
    # 0.05 la cota relativa (0.6 * 5 % = 0.03) se rompe y el test cae.
    rng = random.Random(7)
    madre = Genoma(
        velocidad=1.2,
        metabolismo=0.9,
        longevidad=1.1,
        fuerza=0.58,
        resistencia=1.05,
        inteligencia=1.25,
        salud=0.95,
        divergencia=0.7,
    )
    padre = Genoma(
        velocidad=0.8,
        metabolismo=1.1,
        longevidad=1.3,
        fuerza=0.62,
        resistencia=1.25,
        inteligencia=0.75,
        salud=1.05,
        divergencia=0.3,
    )

    hijos = [heredar(madre, padre, rng) for _ in range(100)]

    for hijo in hijos:
        for rasgo in FUNCIONALES:
            valor = getattr(hijo, rasgo)
            media = (getattr(madre, rasgo) + getattr(padre, rasgo)) / 2.0
            assert RASGO_MIN <= valor <= RASGO_MAX
            assert abs(valor - media) <= media * MUTACION + 1e-12
        assert DIVERGENCIA_MIN <= hijo.divergencia <= DIVERGENCIA_MAX

    for rasgo in FUNCIONALES:
        media_padres = (getattr(madre, rasgo) + getattr(padre, rasgo)) / 2.0
        media_hijos = statistics.fmean(getattr(hijo, rasgo) for hijo in hijos)
        assert abs(media_hijos - media_padres) < 0.03
    media_divergencia = (madre.divergencia + padre.divergencia) / 2.0
    assert abs(statistics.fmean(hijo.divergencia for hijo in hijos) - media_divergencia) < 0.02


def test_el_clamp_de_rango_actua_en_los_bordes() -> None:
    # Con la media en 1.47, un 5 % relativo deja al hijo en 1.5435: sin el
    # clamp final se sale de [0.5, 1.5]. Con la media en 0.53, una mutación
    # absoluta de 0.05 baja de 0.5.
    rng = random.Random(13)

    for alta, baja in ((1.46, 1.48), (0.52, 0.54)):
        madre = Genoma(fuerza=alta)
        padre = Genoma(fuerza=baja)
        media = (alta + baja) / 2.0
        for _ in range(100):
            hijo = heredar(madre, padre, rng)
            assert RASGO_MIN <= hijo.fuerza <= RASGO_MAX
            assert abs(hijo.fuerza - media) <= media * MUTACION + 1e-12


def test_la_mutacion_es_determinista_por_semilla() -> None:
    def diez(seed: int) -> list[Genoma]:
        azar = random.Random(seed)
        return [heredar(Genoma(), Genoma(), azar) for _ in range(10)]

    assert diez(3) == diez(3)
    assert diez(3) != diez(4)


def test_dos_corridas_dan_los_mismos_genomas() -> None:
    def genomas(seed: int) -> list[tuple[int, Genoma]]:
        simulacion = run(ticks=900, seed=seed, headless=True)
        return [(individuo.id, individuo.genoma) for individuo in simulacion.mundo.individuos]

    assert genomas(11) == genomas(11)
    assert genomas(11) != genomas(12)


def test_los_fundadores_tienen_varianza_y_es_determinista() -> None:
    mundo = modulo_mundo.crear(seed=42, individuos=12)
    otro = modulo_mundo.crear(seed=42, individuos=12)

    assert [individuo.genoma for individuo in mundo.individuos] == [
        individuo.genoma for individuo in otro.individuos
    ]
    for rasgo in NUEVOS:
        valores = {getattr(individuo.genoma, rasgo) for individuo in mundo.individuos}
        assert len(valores) > 1
        assert all(RASGO_MIN <= valor <= RASGO_MAX for valor in valores)
    divergencias = {individuo.genoma.divergencia for individuo in mundo.individuos}
    assert len(divergencias) > 1
    assert all(DIVERGENCIA_MIN <= valor <= DIVERGENCIA_MAX for valor in divergencias)
