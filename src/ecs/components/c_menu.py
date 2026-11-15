import pygame


class CMenu:
    """Menú de opciones (#33): cuál está elegida y con qué colores se marcan.

    Cada opción es una entidad de texto con CMenuItem. selected es el índice de la elegida.
    """

    def __init__(self, menu_info: dict) -> None:
        self.count: int = len(menu_info["options"])
        color = menu_info["color"]
        selected_color = menu_info["selected_color"]
        self.color = pygame.Color(color["r"], color["g"], color["b"])
        self.selected_color = pygame.Color(selected_color["r"], selected_color["g"], selected_color["b"])
        self.selected = 0
