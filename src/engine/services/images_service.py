import pygame


class ImagesService:
    def __init__(self) -> None:
        self._images: dict[str, pygame.Surface] = {}

    def get(self, path: str) -> pygame.Surface:
        """Devuelve la imagen de path, cargándola solo la primera vez."""
        if path not in self._images:
            self._images[path] = pygame.image.load(path).convert_alpha()
        return self._images[path]
