"""Creación de entidades del área Enemigos e IA."""
import esper
import pygame

from src.create.prefab_square import create_square
from src.ecs.components.c_steering import CSteering
from src.ecs.components.tags.c_tag_enemy import CTagEnemy, EnemyType


def create_enemy(world: esper.World, enemy_info: dict, pos: pygame.Vector2,
                 enemy_type: EnemyType = EnemyType.I) -> int:
    """Crea un enemigo que persigue usando steering.

    enemy_info sale de assets/cfg/enemies.json. Mientras no estén los sprites,
    se dibuja como un cuadrado del color configurado.
    """
    entity = create_square(world, enemy_info["size"], enemy_info["color"], pos)
    world.add_component(entity, CSteering(enemy_info["steering"]))
    world.add_component(entity, CTagEnemy(enemy_type))
    return entity
