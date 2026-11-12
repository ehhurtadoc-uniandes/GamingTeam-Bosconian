import esper
import pygame

from src.create.prefab_square import create_square
from src.ecs.components.c_player_movement import CPlayerMovement
from src.ecs.components.tags.c_tag_player import CTagPlayer


def create_player(world: esper.World, player_info: dict, pos: pygame.Vector2) -> int:
    entity = create_square(world, player_info["size"], player_info["color"], pos)
    world.add_component(entity, CPlayerMovement(player_info["movement"]))
    world.add_component(entity, CTagPlayer())
    return entity
