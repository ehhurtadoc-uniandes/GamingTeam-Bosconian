import pygame


class CPlayerMovement:
    def __init__(self, movement_info: dict) -> None:
        start = movement_info["start_direction"]
        self.direction = pygame.Vector2(start["x"], start["y"]).normalize()
        self.speed: float = movement_info["initial_speed"]
        self.max_speed: float = movement_info["max_speed"]
        self.acceleration: float = movement_info["acceleration"]
