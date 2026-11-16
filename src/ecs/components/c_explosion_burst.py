import pygame


class CExplosionBurst:
    def __init__(self, explosion_info: dict, pending: list[tuple[float, pygame.Vector2]]) -> None:
        self.explosion_info = explosion_info
        self.pending = pending
        self.elapsed = 0.0
