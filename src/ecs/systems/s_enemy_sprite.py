import esper

from src.ecs.components.c_directional_sprite import CDirectionalSprite
from src.ecs.components.c_enemy import CEnemy
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_player_sprite import direction_index


def system_enemy_sprite(world: esper.World) -> None:
    c_s: CSurface
    c_v: CVelocity
    c_ds: CDirectionalSprite
    for _, (c_s, c_v, c_ds, _) in world.get_components(CSurface, CVelocity, CDirectionalSprite, CEnemy):
        if c_v.vel.length_squared() == 0:
            continue
        index = direction_index(c_v.vel.x, c_v.vel.y, len(c_ds.frames))
        if index != c_ds.current:
            c_ds.current = index
            c_s.surf = c_ds.frames[index]
            c_s.area = c_s.surf.get_rect()
