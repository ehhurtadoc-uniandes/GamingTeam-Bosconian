import pygame


class CMinimap:
    """Datos del minimapa (de minimap.json). Su superficie es el CSurface de la misma entidad.

    blink_time acumula el tiempo para que el punto del jugador parpadee.
    """

    def __init__(self, minimap_info: dict) -> None:
        self.bg_color = _color(minimap_info["bg_color"])
        self.base_color = _color(minimap_info["base_color"])
        self.player_color = _color(minimap_info["player_color"])
        self.dot_size = minimap_info["dot_size"]
        self.player_blink = minimap_info["player_blink"]
        self.blink_time = 0.0


def _color(c: dict) -> pygame.Color:
    return pygame.Color(c["r"], c["g"], c["b"])
