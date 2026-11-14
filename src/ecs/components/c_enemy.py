from enum import Enum


class EnemyType(Enum):
    I = "I"
    P = "P"
    E = "E"


class CEnemy:
    """Nave enemiga: su tipo y lo que suma al destruirla (lo lee el sistema de puntaje)."""

    def __init__(self, enemy_type: EnemyType, points: int = 0) -> None:
        self.enemy_type = enemy_type
        self.points = points
