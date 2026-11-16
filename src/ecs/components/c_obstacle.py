from enum import Enum


class ObstacleKind(Enum):
    ROCK = "rock"
    SOLID_ROCK = "solid_rock"
    MINE = "mine"


class CObstacle:
    """Obstáculo del mundo: roca, roca indestructible o mina.

    destructible: si una bala lo destruye. points: puntos para el jugador al destruirlo.
    hitbox_margin: cuántos píxeles se recorta el sprite por cada lado para la colisión.
    """

    def __init__(self, kind: ObstacleKind, destructible: bool, points: int, hitbox_margin: int) -> None:
        self.kind = kind
        self.destructible = destructible
        self.points = points
        self.hitbox_margin = hitbox_margin
