import pygame


class CAnimation:
    def __init__(self, frames: list[pygame.Surface], frame_duration: float) -> None:
        self.frames = frames
        self.frame_duration = frame_duration
        self.elapsed = 0.0

    @property
    def total_duration(self) -> float:
        return len(self.frames) * self.frame_duration
