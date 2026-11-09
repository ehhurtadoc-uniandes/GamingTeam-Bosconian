import pygame

DEFAULT_DIRECTION = pygame.Vector2(0, -1)


class CPlayerMovement:
    """Parámetros de movimiento del jugador (LC-JUG-01/02).

    - max_speed: velocidad máxima (px/s).
    - acceleration: aumento de velocidad por segundo (px/s²).
    - initial_speed: velocidad al aparecer; se limita a max_speed.
    - start_direction: dirección inicial; si es cero se usa hacia arriba.
    """

    def __init__(self, movement_info: dict) -> None:
        start = movement_info.get("start_direction", {})
        direction = pygame.Vector2(start.get("x", 0), start.get("y", 0))
        if direction.length_squared() == 0:
            direction = pygame.Vector2(DEFAULT_DIRECTION)
        self.direction = direction.normalize()
        self.max_speed: float = movement_info["max_speed"]
        self.acceleration: float = movement_info.get("acceleration", 0.0)
        self.speed: float = min(movement_info.get("initial_speed", 0.0), self.max_speed)
