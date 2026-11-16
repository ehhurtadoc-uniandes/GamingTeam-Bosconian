import esper
import pygame

from src.create.prefab_hitbox import add_hitbox
from src.create.prefab_square import create_square
from src.ecs.components.c_hitbox import CollisionLayer
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.tags.c_tag_offscreen_despawn import CTagOffscreenDespawn
from src.ecs.components.tags.c_tag_player_bullet import CTagPlayerBullet


def create_player_bullet(world: esper.World, bullet_info: dict, center: pygame.Vector2,
                         direction: pygame.Vector2) -> int:
    size = bullet_info["size"]
    pos = pygame.Vector2(center) - pygame.Vector2(size["w"], size["h"]) / 2
    bullet = create_square(world, size, bullet_info["color"], pos)
    world.component_for_entity(bullet, CVelocity).vel = pygame.Vector2(direction).normalize() * bullet_info["speed"]
    add_hitbox(world, bullet, bullet_info, CollisionLayer.PLAYER_BULLET)
    world.add_component(bullet, CTagOffscreenDespawn())
    world.add_component(bullet, CTagPlayerBullet())
    return bullet
