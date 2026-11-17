import math

import esper

from src.ecs.components.c_directional_sprite import CDirectionalSprite
from src.ecs.components.c_player_movement import CPlayerMovement
from src.ecs.components.c_surface import CSurface


def direction_index(direction_x: float, direction_y: float, frame_count: int) -> int:
    angle = math.degrees(math.atan2(direction_x, -direction_y)) % 360
    return round(angle / (360 / frame_count)) % frame_count


def system_player_sprite(world: esper.World) -> None:
    c_s: CSurface
    c_pm: CPlayerMovement
    c_ds: CDirectionalSprite
    for _, (c_s, c_pm, c_ds) in world.get_components(CSurface, CPlayerMovement, CDirectionalSprite):
        index = direction_index(c_pm.direction.x, c_pm.direction.y, len(c_ds.frames))
        if index != c_ds.current:
            c_ds.current = index
            c_s.surf = c_ds.frames[index]
            c_s.area = c_s.surf.get_rect()
