import esper
import pygame

from src.ecs.components.c_player_movement import CPlayerMovement
from src.ecs.components.c_velocity import CVelocity


def system_player_direction(world: esper.World, input_direction: pygame.Vector2) -> None:
    if input_direction.length_squared() == 0:
        return
    new_direction = input_direction.normalize()
    c_pm: CPlayerMovement
    for _, c_pm in world.get_component(CPlayerMovement):
        c_pm.direction = pygame.Vector2(new_direction)


def system_player_acceleration(world: esper.World, delta_time: float) -> None:
    components = world.get_components(CVelocity, CPlayerMovement)
    c_v: CVelocity
    c_pm: CPlayerMovement
    for _, (c_v, c_pm) in components:
        c_pm.speed = min(c_pm.max_speed, c_pm.speed + c_pm.acceleration * delta_time)
        c_v.vel = c_pm.direction * c_pm.speed
