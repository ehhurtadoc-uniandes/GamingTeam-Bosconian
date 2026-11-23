"""HitBox: el rectángulo de colisión de una entidad, aparte de su sprite (LC-COL-02)."""
from enum import Enum

import pygame


class CollisionLayer(Enum):
    """Qué es una entidad para las colisiones. system_collision cruza capas, no entidades sueltas."""

    PLAYER = "PLAYER"
    ENEMY = "ENEMY"
    PLAYER_BULLET = "PLAYER_BULLET"
    ENEMY_BULLET = "ENEMY_BULLET"
    BASE = "BASE"
    BASE_TURRET = "BASE_TURRET"
    BASE_CORE = "BASE_CORE"
    OBSTACLE = "OBSTACLE"
    PICKUP = "PICKUP"


class CHitBox:
    """Rectángulo de colisión de una entidad.

    size: ancho y alto de la caja.
    offset: de CTransform.pos (la esquina superior izquierda del sprite) a la esquina de la caja.
    layer: capa con la que system_collision decide contra qué se prueba.
    """

    def __init__(self, size: pygame.Vector2, offset: pygame.Vector2, layer: CollisionLayer) -> None:
        self.size = pygame.Vector2(size)
        self.offset = pygame.Vector2(offset)
        self.layer = layer
