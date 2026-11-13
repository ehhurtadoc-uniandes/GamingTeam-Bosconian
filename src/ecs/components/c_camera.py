import pygame


class CCamera:
    """Cámara que mira un punto del mundo y lo muestra en el centro de su viewport.

    viewport: rectángulo de la pantalla donde se dibuja el mundo (el resto es HUD).
    center: punto del mundo que queda en el centro del viewport.
    last_move: cuánto se movió en el último paso; el fondo de estrellas lo usa para el parallax.
    """

    def __init__(self, viewport: pygame.Rect, world_size: pygame.Vector2,
                 center: pygame.Vector2) -> None:
        self.viewport = pygame.Rect(viewport)
        self.world_size = pygame.Vector2(world_size)
        self.center = pygame.Vector2(center)
        self.last_move = pygame.Vector2(0, 0)
