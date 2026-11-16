from enum import Enum


class ObstacleKind(Enum):
    ROCK = "rock"
    SOLID_ROCK = "solid_rock"
    MINE = "mine"


class CObstacle:
    """Obstáculo del mundo: roca, roca indestructible o mina.

    destructible: si una bala lo destruye. points: puntos para el jugador al destruirlo.
    Su caja de colisión es el CHitBox de la misma entidad (capa OBSTACLE).
    """

    def __init__(self, kind: ObstacleKind, destructible: bool, points: int) -> None:
        self.kind = kind
        self.destructible = destructible
        self.points = points
