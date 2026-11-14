import pygame


class CLivesIcons:
    """Íconos de las vidas de reserva en el HUD. shown es cuántos están dibujados ahora."""

    def __init__(self, icons_info: dict, max_visible: int) -> None:
        size = icons_info["size"]
        color = icons_info["color"]
        self.icon_size = pygame.Vector2(size["w"], size["h"])
        self.color = pygame.Color(color["r"], color["g"], color["b"])
        self.spacing: int = icons_info["spacing"]
        self.max_visible = max_visible
        self.shown: int | None = None
