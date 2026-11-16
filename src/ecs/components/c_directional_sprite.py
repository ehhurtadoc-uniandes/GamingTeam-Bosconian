import pygame


class CDirectionalSprite:
    def __init__(self, frames: list[pygame.Surface]) -> None:
        self.frames = frames
        self.current = 0
