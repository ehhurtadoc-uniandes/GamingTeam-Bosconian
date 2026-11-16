import esper
import pygame

from src.ecs.components.c_hitbox import CollisionLayer
from src.ecs.systems.s_collision import system_collision

ENEMY_BULLET_PAIR = (CollisionLayer.ENEMY_BULLET, CollisionLayer.ENEMY)


def system_enemy_bullet_collision(world: esper.World, world_size: pygame.Vector2 | None = None) -> None:
    """Un enemigo que choca con una bala de torreta muere, y la bala también (LC-BAS-05.1).

    No suma puntos: no lo mató el jugador. Solo se cruzan las capas ENEMY_BULLET
    y ENEMY, así que las balas atraviesan las bases. Se comparan las hitbox, no los
    sprites, y con world_size también cruzando los bordes del mundo. La explosión
    llegará con #16.

    delete_entity marca la entidad como muerta en el acto (entity_exists da False),
    aunque se borre al final del paso. Así una bala que ya mató a un enemigo no mata
    a otro, y una que venció en system_lifetime no choca.
    """
    for bullet, enemy in system_collision(world, [ENEMY_BULLET_PAIR], world_size)[ENEMY_BULLET_PAIR]:
        if world.entity_exists(bullet) and world.entity_exists(enemy):
            world.delete_entity(enemy)
            world.delete_entity(bullet)
