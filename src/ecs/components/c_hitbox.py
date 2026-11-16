from enum import Enum

import pygame


class CollisionLayer(Enum):
    PLAYER = "PLAYER"
    ENEMY = "ENEMY"
    PLAYER_BULLET = "PLAYER_BULLET"
    ENEMY_BULLET = "ENEMY_BULLET"
    BASE = "BASE"
    BASE_TURRET = "BASE_TURRET"
    BASE_CORE = "BASE_CORE"
    OBSTACLE = "OBSTACLE"


class CHitBox:
    def __init__(self, size: pygame.Vector2, offset: pygame.Vector2, layer: CollisionLayer) -> None:
        self.size = pygame.Vector2(size)
        self.offset = pygame.Vector2(offset)
        self.layer = layer
