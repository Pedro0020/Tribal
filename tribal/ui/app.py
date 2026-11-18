"""
Bucle de ventana: un `sim.step()` y un dibujo por frame, a 60 fps.

`Clock.tick(60)` limita el ritmo durmiendo lo que sobra, no esperando a nada
externo: si un frame tarda más, el reloj lo deja pasar. Nada aquí puede
bloquear la simulación.
"""

from __future__ import annotations

import pygame

from tribal.sim import Simulacion
from tribal.ui import render

FPS = 60


def bucle(simulacion: Simulacion, ticks_max: int = 0) -> None:
    """Corre la simulación en ventana hasta ESC, cierre, o `ticks_max` ticks."""
    pygame.display.init()
    pygame.font.init()
    pantalla = pygame.display.set_mode(render.tamano_ventana(simulacion.mundo))
    pygame.display.set_caption("Tribal (Fase 0)")
    reloj = pygame.time.Clock()

    frames = 0
    try:
        while True:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    return
                if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                    return

            simulacion.step()
            frames += 1
            if ticks_max and frames >= ticks_max:
                return

            pantalla.blit(render.dibujar_frame(simulacion.mundo), (0, 0))
            pygame.display.flip()
            reloj.tick(FPS)
    finally:
        pygame.display.quit()
