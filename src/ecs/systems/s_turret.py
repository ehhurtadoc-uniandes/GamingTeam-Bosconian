"""Torretas de base que se abren y disparan al jugador cercano (LC-BAS-05)."""
import esper
import pygame

from src.create.prefab_bullet import create_turret_bullet
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_turret import CTurret, TurretState
from src.ecs.systems.s_steering import wrapped_delta


def system_turret(world: esper.World, delta_time: float, player_center: pygame.Vector2,
                  bullet_info: dict, world_size: pygame.Vector2 | None = None) -> None:
    """Abre o cierra cada torreta según la distancia al jugador y dispara las abiertas.

    La distancia se mide entre centros y, con world_size, por el camino más corto
    cruzando los bordes (wraparound, el mismo cálculo que system_steering). Debe
    ir antes de system_movement para que la bala nueva avance en el mismo frame.
    """
    components = world.get_components(CTransform, CSurface, CTurret)
    c_t: CTransform
    c_s: CSurface
    c_tu: CTurret
    for _, (c_t, c_s, c_tu) in components:
        center = c_t.pos + pygame.Vector2(c_s.area.size) / 2
        to_player = wrapped_delta(center, player_center, world_size)
        is_near = to_player.length_squared() < c_tu.activation_distance ** 2
        if is_near and c_tu.state == TurretState.CLOSED:
            _set_state(c_tu, c_s, TurretState.OPEN)
        elif not is_near and c_tu.state == TurretState.OPEN:
            _set_state(c_tu, c_s, TurretState.CLOSED)

        if c_tu.state != TurretState.OPEN:
            continue
        c_tu.time_to_fire -= delta_time
        if c_tu.time_to_fire > 0:
            continue
        # Un solo disparo por frame aunque delta_time sea mayor que el intervalo.
        c_tu.time_to_fire = max(c_tu.time_to_fire + c_tu.fire_interval, 0.0)
        if to_player.length_squared() > 0:
            create_turret_bullet(world, bullet_info, center, to_player)


def _set_state(c_tu: CTurret, c_s: CSurface, state: TurretState) -> None:
    c_tu.state = state
    c_s.surf = c_tu.open_surf if state == TurretState.OPEN else c_tu.closed_surf
    c_s.area = c_s.surf.get_rect()
