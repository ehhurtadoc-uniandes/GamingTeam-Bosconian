import esper
import pygame

from src.ecs.components.c_hitbox import CHitBox, CollisionLayer
from src.ecs.components.c_surface import CSurface


def add_hitbox(world: esper.World, entity: int, info: dict, layer: CollisionLayer,
               rotated: bool = False) -> None:
    sprite_size = pygame.Vector2(world.component_for_entity(entity, CSurface).area.size)
    hitbox_info = info.get("hitbox")
    if hitbox_info is None:
        size = sprite_size
        center_shift = pygame.Vector2(0, 0)
    else:
        size = pygame.Vector2(hitbox_info["size"]["w"], hitbox_info["size"]["h"])
        shift = hitbox_info.get("offset", {"x": 0, "y": 0})
        center_shift = pygame.Vector2(shift["x"], shift["y"])
        if rotated:
            size = pygame.Vector2(size.y, size.x)
            center_shift = pygame.Vector2(-center_shift.y, center_shift.x)
    offset = sprite_size / 2 + center_shift - size / 2
    world.add_component(entity, CHitBox(size, offset, layer))
