"""Creación de entidades del área Enemigos e IA."""
import esper
import pygame

from src.ecs.components.c_steering import CSteering
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.tags.c_tag_enemy import CTagEnemy, EnemyType


def create_enemy(world: esper.World, enemy_info: dict, pos: pygame.Vector2,
                 enemy_type: EnemyType = EnemyType.I) -> int:
    """Crea un enemigo que persigue usando steering.

    enemy_info sale de assets/cfg/enemies.json. Mientras no estén los sprites,
    se dibuja como un cuadrado del color configurado.
    """
    size = enemy_info["size"]
    color = enemy_info["color"]
    surface = CSurface(pygame.Vector2(size["w"], size["h"]),
                       pygame.Color(color["r"], color["g"], color["b"]))
    entity = world.create_entity()
    world.add_component(entity, CTransform(pygame.Vector2(pos)))
    world.add_component(entity, CVelocity(pygame.Vector2(0, 0)))
    world.add_component(entity, surface)
    world.add_component(entity, CSteering(enemy_info["steering"]))
    world.add_component(entity, CTagEnemy(enemy_type))
    return entity
