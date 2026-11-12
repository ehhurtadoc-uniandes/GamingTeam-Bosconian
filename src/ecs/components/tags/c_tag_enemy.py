from enum import Enum


class CTagEnemy:
    """Marca una nave enemiga. points es lo que suma al destruirla (lo lee el sistema de puntaje)."""

    def __init__(self, enemy_type: "EnemyType", points: int = 0) -> None:
        self.enemy_type = enemy_type
        self.points = points


class EnemyType(Enum):
    I = "I"
    P = "P"
    E = "E"


class CTagEnemyBullet:
    """Marca una bala disparada por una torreta de base (LC-BAS-05).

    Mata a los enemigos con que choca (LC-BAS-05.1); #22 la hará chocar con el jugador.
    """
