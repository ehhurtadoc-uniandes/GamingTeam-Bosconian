import esper
import pygame

from src.ecs.components.c_lives_counter import CLivesCounter
from src.ecs.components.c_lives_icons import CLivesIcons
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_text import CText
from src.engine.service_locator import ServiceLocator


def lives_icons_surface(count: int, c_icons: CLivesIcons) -> pygame.Surface:
    """Superficie con count íconos en fila, separados por spacing."""
    step = c_icons.icon_size.x + c_icons.spacing
    width = max(0, count * step - c_icons.spacing)
    surface = pygame.Surface((width, c_icons.icon_size.y), pygame.SRCALPHA)
    for i in range(count):
        surface.fill(c_icons.color, pygame.Rect((i * step, 0), c_icons.icon_size))
    return surface


def system_lives_hud(world: esper.World) -> None:
    """Muestra las vidas de reserva: hasta max_visible íconos y, si hay más, el total en número."""
    lives = ServiceLocator.game_state_service.lives
    c_icons: CLivesIcons
    c_s: CSurface
    for _, (c_icons, c_s) in world.get_components(CLivesIcons, CSurface):
        count = min(lives, c_icons.max_visible)
        if c_icons.shown != count:
            c_s.surf = lives_icons_surface(count, c_icons)
            c_s.area = c_s.surf.get_rect()
            c_icons.shown = count
    c_counter: CLivesCounter
    c_text: CText
    for _, (c_counter, c_text) in world.get_components(CLivesCounter, CText):
        c_text.text = str(lives) if lives > c_counter.max_visible else ""
