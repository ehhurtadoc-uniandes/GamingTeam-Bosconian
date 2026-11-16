"""Minimapa: el mundo completo en pequeño, con las bases y el jugador."""
import esper
import pygame

from src.ecs.components.c_minimap import CMinimap
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_base import CTagBase
from src.ecs.components.tags.c_tag_player import CTagPlayer
from src.utils.wrap import wrap_position


def to_minimap(world_pos: pygame.Vector2, world_size: pygame.Vector2, size: tuple[int, int]) -> pygame.Vector2:
    """Escala una posición del mundo al tamaño del minimapa (relativa a su esquina).

    Una posición que se pasó de un borde del mundo aparece por el lado opuesto (LC-MIN-02).
    """
    pos = pygame.Vector2(world_pos)
    wrap_position(pos, world_size)
    return pygame.Vector2(pos.x * size[0] / world_size.x, pos.y * size[1] / world_size.y)


def system_minimap(world: esper.World, delta_time: float, world_size: pygame.Vector2) -> None:
    """Redibuja la superficie del minimapa: fondo, bases y jugador.

    Se reutiliza siempre la misma superficie (no se crea una nueva cada frame). Las bases
    destruidas ya no existen, así que desaparecen solas. El jugador parpadea.
    """
    bases = [_center(c_t, c_s) for _, (c_t, c_s, _) in world.get_components(CTransform, CSurface, CTagBase)]
    players = [_center(c_t, c_s) for _, (c_t, c_s, _) in world.get_components(CTransform, CSurface, CTagPlayer)]
    c_s: CSurface
    c_minimap: CMinimap
    for _, (c_s, c_minimap) in world.get_components(CSurface, CMinimap):
        c_minimap.blink_time += delta_time
        size = c_s.surf.get_size()
        c_s.surf.fill(c_minimap.bg_color)
        for center in bases:
            _draw_dot(c_s.surf, to_minimap(center, world_size, size), c_minimap.dot_size, c_minimap.base_color)
        if int(c_minimap.blink_time / c_minimap.player_blink) % 2 == 0:
            for center in players:
                _draw_dot(c_s.surf, to_minimap(center, world_size, size), c_minimap.dot_size,
                          c_minimap.player_color)


def _center(c_t: CTransform, c_s: CSurface) -> pygame.Vector2:
    return c_t.pos + pygame.Vector2(c_s.area.size) / 2


def _draw_dot(surface: pygame.Surface, center: pygame.Vector2, size: int, color: pygame.Color) -> None:
    surface.fill(color, pygame.Rect(int(center.x - size / 2), int(center.y - size / 2), size, size))
