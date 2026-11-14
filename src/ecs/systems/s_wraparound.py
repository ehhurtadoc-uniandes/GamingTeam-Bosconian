import esper
import pygame

from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.utils.wrap import wrap_position


def system_wraparound(world: esper.World, world_size: pygame.Vector2) -> None:
    components = world.get_components(CTransform, CVelocity)
    c_t: CTransform
    for _, (c_t, _) in components:
        wrap_position(c_t.pos, world_size)
