import esper
import pygame

from src.ecs.components.c_minimap import CMinimap
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_hide_on_pause import CTagHideOnPause
from src.ecs.components.tags.c_tag_ui import CTagUI


def create_minimap(world: esper.World, minimap_info: dict) -> int:
    """Crea el minimapa: interfaz que se esconde en pausa. system_minimap redibuja su superficie."""
    r = minimap_info["rect"]
    c_minimap = CMinimap(minimap_info)
    surface = CSurface(pygame.Vector2(r["w"], r["h"]), c_minimap.bg_color)
    return world.create_entity(CTransform(pygame.Vector2(r["x"], r["y"])), surface, c_minimap,
                               CTagUI(), CTagHideOnPause())
