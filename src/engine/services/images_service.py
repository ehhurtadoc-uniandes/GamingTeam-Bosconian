from typing import Callable

import pygame


class ImagesService:
    def __init__(self) -> None:
        self._images: dict[str, pygame.Surface] = {}

    def get(self, path: str) -> pygame.Surface:
        """Devuelve la imagen de path, cargándola solo la primera vez."""
        if path not in self._images:
            image = pygame.image.load(path)
            self._images[path] = image.convert_alpha() if pygame.display.get_surface() else image
        return self._images[path]

    def get_or_create(self, key: str, create: Callable[[], pygame.Surface]) -> pygame.Surface:
        """Devuelve la superficie guardada con key, creándola con create solo la primera vez."""
        if key not in self._images:
            self._images[key] = create()
        return self._images[key]
