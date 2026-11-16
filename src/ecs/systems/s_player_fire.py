import esper
import pygame

from src.create.prefab_player_bullet import create_player_bullet
from src.ecs.components.c_player_movement import CPlayerMovement
from src.ecs.components.c_player_weapon import CPlayerWeapon
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_player import CTagPlayer


def system_player_weapon_cooldown(world: esper.World, delta_time: float) -> None:
    c_w: CPlayerWeapon
    for _, c_w in world.get_component(CPlayerWeapon):
        c_w.time_left = max(0.0, c_w.time_left - delta_time)


def system_player_fire(world: esper.World) -> None:
    components = world.get_components(CTransform, CSurface, CPlayerMovement, CPlayerWeapon, CTagPlayer)
    c_t: CTransform
    c_s: CSurface
    c_pm: CPlayerMovement
    c_w: CPlayerWeapon
    for _, (c_t, c_s, c_pm, c_w, _) in components:
        if c_w.time_left > 0:
            continue
        center = c_t.pos + pygame.Vector2(c_s.area.size) / 2
        create_player_bullet(world, c_w.bullet_info, center, c_pm.direction)
        create_player_bullet(world, c_w.bullet_info, center, -c_pm.direction)
        c_w.time_left = c_w.fire_cooldown
