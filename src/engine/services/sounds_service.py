import pygame


class SoundsService:
    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}

    def get(self, path: str) -> pygame.mixer.Sound:
        """Devuelve el sonido de path, cargándolo solo la primera vez."""
        if path not in self._sounds:
            self._sounds[path] = pygame.mixer.Sound(path)
        return self._sounds[path]

    def play(self, path: str) -> None:
        self.get(path).play()
