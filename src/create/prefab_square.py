"""Creación de entidades base dibujadas como cuadrados (mientras no hay sprites)."""
import esper
import pygame

from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity


def create_square(world: esper.World, size: dict, color: dict, pos: pygame.Vector2) -> int:
    """Crea una entidad con CTransform, CVelocity en reposo y un CSurface del tamaño y color dados."""
    surface = CSurface(pygame.Vector2(size["w"], size["h"]),
                       pygame.Color(color["r"], color["g"], color["b"]))
    entity = world.create_entity()
    world.add_component(entity, CTransform(pygame.Vector2(pos)))
    world.add_component(entity, CVelocity(pygame.Vector2(0, 0)))
    world.add_component(entity, surface)
    return entity
