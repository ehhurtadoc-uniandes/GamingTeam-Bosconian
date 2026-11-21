"""Las balas del jugador destruyen enemigos y suman su puntaje (LC-TEN-01/02/03)."""
import esper
import pygame

from src.create.prefab_explosion import destroy_with_explosion
from src.ecs.components.c_enemy import CEnemy
from src.ecs.components.c_hitbox import CollisionLayer
from src.ecs.systems.s_collision import system_collision
from src.engine.service_locator import ServiceLocator

BULLET_ENEMY_PAIR = (CollisionLayer.PLAYER_BULLET, CollisionLayer.ENEMY)


def system_player_bullet_enemy(world: esper.World, world_size: pygame.Vector2 | None = None) -> None:
    """Una bala del jugador que toca a un enemigo lo destruye con explosión y se borra.

    Suma CEnemy.points (50, 60 o 70 según el tipo, desde enemies.json); add_score
    actualiza el HI-SCORE. La explosión conserva la velocidad del enemigo (LC-COL-06).
    Solo aquí se suman puntos por enemigos: los que mueren por una torreta o una mina
    no dan puntos.

    Se comparan las hitbox, no los sprites, y con world_size también cruzando los
    bordes del mundo. Una bala mata a un solo enemigo y un enemigo da puntos una sola
    vez: delete_entity deja entity_exists en False en el acto, así que una bala o un
    enemigo ya gastados en este paso (o en un sistema anterior) se saltan.
    """
    for bullet, enemy in system_collision(world, [BULLET_ENEMY_PAIR], world_size)[BULLET_ENEMY_PAIR]:
        if world.entity_exists(bullet) and world.entity_exists(enemy):
            points = world.component_for_entity(enemy, CEnemy).points
            destroy_with_explosion(world, enemy)
            world.delete_entity(bullet)
            ServiceLocator.game_state_service.add_score(points)
