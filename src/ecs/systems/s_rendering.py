import esper
import pygame

from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_ui import CTagUI


def system_rendering(world: esper.World, screen: pygame.Surface) -> None:
    """Dibuja cada entidad en su posición: primero el mundo y encima la interfaz (CTagUI)."""
    components = world.get_components(CTransform, CSurface)
    c_t: CTransform
    c_s: CSurface
    ui = []
    for entity, (c_t, c_s) in components:
        if world.has_component(entity, CTagUI):
            ui.append((c_t, c_s))
        else:
            screen.blit(c_s.surf, c_t.pos, area=c_s.area)
    for c_t, c_s in ui:
        screen.blit(c_s.surf, c_t.pos, area=c_s.area)
