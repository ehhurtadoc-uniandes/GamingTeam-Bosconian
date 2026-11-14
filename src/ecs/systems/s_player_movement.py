import esper
import pygame

from src.ecs.components.c_player_movement import CPlayerMovement
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.tags.c_tag_player import CTagPlayer
from src.engine.service_locator import ServiceLocator


def snap_to_eight_directions(input_direction: pygame.Vector2) -> pygame.Vector2:
    """Lleva cada eje a -1, 0 o 1 para que el movimiento quede en 8 direcciones (LC-JUG-02).

    Los ejes con magnitud menor a la zona muerta (ConstantsService.player_dead_zone) se ignoran (drift de joystick).
    """
    def axis(value: float) -> int:
        if abs(value) < ServiceLocator.constants_service.player_dead_zone:
            return 0
        return 1 if value > 0 else -1
    return pygame.Vector2(axis(input_direction.x), axis(input_direction.y))


def system_player_direction(world: esper.World, input_direction: pygame.Vector2) -> None:
    snapped = snap_to_eight_directions(input_direction)
    if snapped.length_squared() == 0:
        return
    new_direction = snapped.normalize()
    c_pm: CPlayerMovement
    for _, (c_pm, _) in world.get_components(CPlayerMovement, CTagPlayer):
        c_pm.direction = pygame.Vector2(new_direction)


def system_player_acceleration(world: esper.World, delta_time: float) -> None:
    components = world.get_components(CVelocity, CPlayerMovement, CTagPlayer)
    c_v: CVelocity
    c_pm: CPlayerMovement
    for _, (c_v, c_pm, _) in components:
        c_pm.speed = min(c_pm.max_speed, c_pm.speed + c_pm.acceleration * delta_time)
        c_v.vel = c_pm.direction * c_pm.speed
