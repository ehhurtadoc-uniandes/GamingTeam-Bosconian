import pygame


class TextsService:
    """Guarda los textos ya renderizados para no llamar a Font.render en cada frame.

    Sirve para textos que se repiten (etiquetas de depuración, ayudas). Cada combinación
    de fuente, texto y color se renderiza una sola vez. Los textos de interfaz que
    cambian seguido (como el puntaje) usan CText, que guarda su propia superficie.
    """

    def __init__(self) -> None:
        self._texts: dict[tuple[pygame.font.Font, str, tuple[int, int, int, int]], pygame.Surface] = {}

    def get(self, font: pygame.font.Font, text: str, color: pygame.Color) -> pygame.Surface:
        key = (font, text, tuple(color))
        if key not in self._texts:
            self._texts[key] = font.render(text, False, color)
        return self._texts[key]

    def clear(self) -> None:
        """Vacía la caché. Hay que llamarlo antes de reiniciar pygame, igual que FontsService.clear."""
        self._texts.clear()
