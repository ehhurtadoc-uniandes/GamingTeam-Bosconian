import esper
import pygame

from src.ecs.components.c_player_movement import CPlayerMovement
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.tags.c_tag_player import CTagPlayer


def create_player(world: esper.World, player_info: dict, pos: pygame.Vector2) -> int:
    size = player_info["size"]
    color = player_info["color"]
    surface = CSurface(pygame.Vector2(size["w"], size["h"]),
                       pygame.Color(color["r"], color["g"], color["b"]))
    entity = world.create_entity()
    world.add_component(entity, CTransform(pygame.Vector2(pos)))
    world.add_component(entity, CVelocity(pygame.Vector2(0, 0)))
    world.add_component(entity, surface)
    world.add_component(entity, CPlayerMovement(player_info["movement"]))
    world.add_component(entity, CTagPlayer())
    return entity
