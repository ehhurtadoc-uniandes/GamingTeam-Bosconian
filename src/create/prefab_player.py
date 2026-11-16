import esper
import pygame

from src.create.prefab_hitbox import add_hitbox
from src.create.prefab_square import create_square
from src.ecs.components.c_hitbox import CollisionLayer
from src.ecs.components.c_player_movement import CPlayerMovement
from src.ecs.components.c_player_weapon import CPlayerWeapon
from src.ecs.components.c_special_shot import CSpecialShot
from src.ecs.components.tags.c_tag_player import CTagPlayer


def create_player(world: esper.World, player_info: dict, pos: pygame.Vector2,
                  special_shot: bool = False) -> int:
    entity = create_square(world, player_info["size"], player_info["color"], pos)
    add_hitbox(world, entity, player_info, CollisionLayer.PLAYER)
    world.add_component(entity, CPlayerMovement(player_info["movement"]))
    world.add_component(entity, CPlayerWeapon(player_info["weapon"]))
    if special_shot:
        world.add_component(entity, CSpecialShot(player_info["special_shot"]))
    world.add_component(entity, CTagPlayer())
    return entity
