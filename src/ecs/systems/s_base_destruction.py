"""Balas del jugador contra las bases: torretas y núcleo (LC-BAS-01, LC-BAS-07, #21)."""
from collections import defaultdict

import esper
import pygame

from src.create.prefab_explosion import destroy_with_explosion
from src.ecs.components.c_base import BaseOrientation, CBase
from src.ecs.components.c_base_part import CBasePart
from src.ecs.components.c_hitbox import CHitBox, CollisionLayer
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_alert import record_base_destroyed
from src.ecs.systems.s_collision import hitbox_center, system_collision
from src.engine.service_locator import ServiceLocator
from src.utils.wrap import wrapped_delta


BULLET_CORE_PAIR = (CollisionLayer.PLAYER_BULLET, CollisionLayer.BASE_CORE)
BULLET_TURRET_PAIR = (CollisionLayer.PLAYER_BULLET, CollisionLayer.BASE_TURRET)


def heading_hits_core(velocity: pygame.Vector2, orientation: BaseOrientation) -> bool:
    """True si la bala viaja sobre todo a lo largo del eje de la base (LC-BAS-07.2).

    Horizontal: |vel.x| > |vel.y|. Vertical: |vel.y| > |vel.x|. El sentido da igual;
    una diagonal exacta o una velocidad cero no cuentan.
    """
    if orientation == BaseOrientation.HORIZONTAL:
        return abs(velocity.x) > abs(velocity.y)
    return abs(velocity.y) > abs(velocity.x)


def destroy_base(world: esper.World, base: int, points_info: dict) -> int:
    """Destruye la base entera: cuerpo, núcleo y torretas que queden, cada pieza con su explosión.

    Devuelve los puntos del premio de la base (points_info["base"]). Es idempotente:
    si la base ya se destruyó en este paso devuelve 0 y no crea más explosiones.
    Cada destrucción real queda registrada para la alerta (#29), que la procesa al
    comienzo del paso siguiente.
    """
    if not world.entity_exists(base):
        return 0
    record_base_destroyed(world)
    c_base = world.component_for_entity(base, CBase)
    for piece in [*c_base.turrets, c_base.core]:
        if world.entity_exists(piece):
            destroy_with_explosion(world, piece)
    c_base.turrets.clear()
    destroy_with_explosion(world, base)
    return points_info["base"]


def hit_turret(world: esper.World, turret: int, points_info: dict) -> int:
    """Destruye una torreta y la saca de su base. Si era la última, destruye también la base.

    Devuelve los puntos ganados: los de la torreta y, si la base cayó, también los de la base.
    """
    base = world.component_for_entity(turret, CBasePart).base
    destroy_with_explosion(world, turret)
    points = points_info["turret"]
    if world.entity_exists(base):
        c_base = world.component_for_entity(base, CBase)
        if turret in c_base.turrets:
            c_base.turrets.remove(turret)
        if not c_base.turrets:
            points += destroy_base(world, base, points_info)
    return points


def _closest(world: esper.World, bullet_center: pygame.Vector2, pieces: list[int],
             world_size: pygame.Vector2 | None) -> int:
    """La pieza cuyo centro está más cerca del de la bala; en empate, la de menor id."""
    def key(piece: int) -> tuple[float, int]:
        center = hitbox_center(world.component_for_entity(piece, CTransform),
                               world.component_for_entity(piece, CHitBox))
        return wrapped_delta(bullet_center, center, world_size).length_squared(), piece
    return min(pieces, key=key)


def system_player_bullet_base(world: esper.World, points_info: dict,
                              world_size: pygame.Vector2 | None = None) -> None:
    """Las balas del jugador destruyen torretas y núcleos de las bases y suman sus puntos.

    points_info es la sección "points" de base.json. Cada bala afecta a una sola pieza,
    con esta prioridad entre las que toca en el mismo paso:
    1. Un núcleo al que llega con rumbo válido: cae la base completa (points["base"]).
    2. La torreta más cercana a su centro: cae esa torreta (points["turret"]) y, si era
       la última, también la base.
    3. Un núcleo con otro rumbo: la bala se gasta sin dañar nada.

    Una bala ya gastada o una pieza ya destruida no reaccionan otra vez. Si todas las
    piezas que tocaba ya cayeron en este paso, la bala no se gasta. Con world_size
    funciona con bases partidas por los bordes del mundo.
    """
    collisions = system_collision(world, [BULLET_CORE_PAIR, BULLET_TURRET_PAIR], world_size)
    cores: dict[int, list[int]] = defaultdict(list)
    turrets: dict[int, list[int]] = defaultdict(list)
    for bullet, core in collisions[BULLET_CORE_PAIR]:
        cores[bullet].append(core)
    for bullet, turret in collisions[BULLET_TURRET_PAIR]:
        turrets[bullet].append(turret)

    for bullet in sorted(cores.keys() | turrets.keys()):
        if not world.entity_exists(bullet):
            continue
        bullet_center = hitbox_center(world.component_for_entity(bullet, CTransform),
                                      world.component_for_entity(bullet, CHitBox))
        velocity = world.component_for_entity(bullet, CVelocity).vel \
            if world.has_component(bullet, CVelocity) else pygame.Vector2(0, 0)
        live_cores = [core for core in cores[bullet] if world.entity_exists(core)]
        live_turrets = [turret for turret in turrets[bullet] if world.entity_exists(turret)]
        valid_cores = [core for core in live_cores
                       if heading_hits_core(velocity, _orientation_of(world, core))]
        points = 0
        if valid_cores:
            core = _closest(world, bullet_center, valid_cores, world_size)
            points = destroy_base(world, world.component_for_entity(core, CBasePart).base, points_info)
        elif live_turrets:
            points = hit_turret(world, _closest(world, bullet_center, live_turrets, world_size), points_info)
        elif not live_cores:
            continue
        world.delete_entity(bullet)
        ServiceLocator.game_state_service.add_score(points)


def _orientation_of(world: esper.World, piece: int) -> BaseOrientation:
    base = world.component_for_entity(piece, CBasePart).base
    return world.component_for_entity(base, CBase).orientation
