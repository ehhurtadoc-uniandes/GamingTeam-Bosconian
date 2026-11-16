import esper
import pygame

from src.ecs.components.c_hitbox import CollisionLayer
from src.ecs.systems.s_collision import system_collision

ENEMY_BULLET_PAIR = (CollisionLayer.ENEMY_BULLET, CollisionLayer.ENEMY)


def system_enemy_bullet_collision(world: esper.World, world_size: pygame.Vector2 | None = None) -> None:
    for bullet, enemy in system_collision(world, [ENEMY_BULLET_PAIR], world_size)[ENEMY_BULLET_PAIR]:
        if world.entity_exists(bullet) and world.entity_exists(enemy):
            world.delete_entity(enemy)
            world.delete_entity(bullet)
