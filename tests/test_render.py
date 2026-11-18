"""Render sin ventana: driver dummy, Surface del tamaño del mundo y PNG de humo."""

from __future__ import annotations

from pathlib import Path

import pygame
import pytest


@pytest.fixture
def pygame_dummy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fija el driver dummy y reinicia el display solo para este test."""
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    pygame.display.quit()
    pygame.display.init()


def test_dibujar_frame_devuelve_surface_con_varios_colores(
    pygame_dummy: None, tmp_path: Path
) -> None:
    from tribal.core import mundo as modulo_mundo
    from tribal.sim import Simulacion
    from tribal.ui import render

    simulacion = Simulacion(modulo_mundo.crear(seed=1, individuos=10))
    for _ in range(120):
        simulacion.step()

    superficie = render.dibujar_frame(simulacion.mundo)

    assert isinstance(superficie, pygame.Surface)
    assert superficie.get_size() == render.tamano_ventana(simulacion.mundo)
    colores = {
        superficie.get_at((x, y))[:3]
        for x in range(0, superficie.get_width(), 3)
        for y in range(0, superficie.get_height(), 3)
    }
    assert len(colores) >= 4

    destino = tmp_path / "fase0.png"
    pygame.image.save(superficie, str(destino))
    assert destino.stat().st_size > 0


def test_bucle_pinta_un_frame_por_tick(pygame_dummy: None, monkeypatch: pytest.MonkeyPatch) -> None:
    from tribal.core import mundo as modulo_mundo
    from tribal.sim import Simulacion
    from tribal.ui import app, render

    simulacion = Simulacion(modulo_mundo.crear(seed=1, individuos=8))
    pintados: list[pygame.Surface] = []
    dibujar_frame = render.dibujar_frame

    def espia(mundo: modulo_mundo.Mundo) -> pygame.Surface:
        superficie = dibujar_frame(mundo)
        pintados.append(superficie)
        return superficie

    monkeypatch.setattr(render, "dibujar_frame", espia)

    app.bucle(simulacion, ticks_max=5)

    assert simulacion.mundo.tick == 5
    assert pintados
    assert pintados[-1].get_size() == render.tamano_ventana(simulacion.mundo)
    colores = {
        pintados[-1].get_at((x, y))[:3]
        for x in range(0, pintados[-1].get_width(), 4)
        for y in range(0, pintados[-1].get_height(), 4)
    }
    assert len(colores) >= 4
