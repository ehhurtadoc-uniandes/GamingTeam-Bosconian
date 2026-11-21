import esper
import pygame

from src.ecs.components.c_hitbox import CHitBox, CollisionLayer
from src.ecs.components.c_leaving_base import CLeavingBase
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_collision import hitbox_center, system_collision
from src.utils.wrap import wrapped_delta

ENEMY_ENEMY_PAIR = (CollisionLayer.ENEMY, CollisionLayer.ENEMY)
ENEMY_BASE_PAIR = (CollisionLayer.ENEMY, CollisionLayer.BASE)
# Pasadas de detección y separación por paso; suficiente para grupos chicos sin costo excesivo.
MAX_PASSES = 4


def contact_normal(center_a: pygame.Vector2, size_a: pygame.Vector2, center_b: pygame.Vector2,
                   size_b: pygame.Vector2, world_size: pygame.Vector2 | None = None
                   ) -> tuple[pygame.Vector2, float] | None:
    delta = wrapped_delta(center_a, center_b, world_size)
    overlap_x = (size_a.x + size_b.x) / 2 - abs(delta.x)
    overlap_y = (size_a.y + size_b.y) / 2 - abs(delta.y)
    if overlap_x <= 0 or overlap_y <= 0:
        return None
    if overlap_x < overlap_y:
        return pygame.Vector2(1 if delta.x >= 0 else -1, 0), overlap_x
    return pygame.Vector2(0, 1 if delta.y >= 0 else -1), overlap_y


def reflect(velocity: pygame.Vector2, normal_towards_obstacle: pygame.Vector2) -> pygame.Vector2:
    approach = velocity.dot(normal_towards_obstacle)
    if approach <= 0:
        return pygame.Vector2(velocity)
    return velocity - 2 * approach * normal_towards_obstacle


def _bounce(world: esper.World, first: int, second: int, second_is_movable: bool,
            world_size: pygame.Vector2 | None) -> None:
    c_t_a = world.component_for_entity(first, CTransform)
    c_h_a = world.component_for_entity(first, CHitBox)
    c_t_b = world.component_for_entity(second, CTransform)
    c_h_b = world.component_for_entity(second, CHitBox)
    contact = contact_normal(hitbox_center(c_t_a, c_h_a), c_h_a.size,
                             hitbox_center(c_t_b, c_h_b), c_h_b.size, world_size)
    if contact is None:
        return
    normal, overlap = contact
    c_v_a = world.component_for_entity(first, CVelocity)
    c_v_a.vel = reflect(c_v_a.vel, normal)
    if second_is_movable:
        c_t_a.pos -= normal * overlap / 2
        c_t_b.pos += normal * overlap / 2
        c_v_b = world.component_for_entity(second, CVelocity)
        c_v_b.vel = reflect(c_v_b.vel, -normal)
    else:
        c_t_a.pos -= normal * overlap


def system_enemy_bounce(world: esper.World, world_size: pygame.Vector2 | None = None,
                        max_passes: int = MAX_PASSES) -> None:
    """Los enemigos rebotan entre sí y contra el cuerpo de las bases (LC-COL-03).

    Separar una pareja puede meter a un enemigo en otro o en una base que no estaban
    en la lista de choques. Por eso se vuelve a detectar y resolver hasta que no
    quede ningún solape, con un máximo de max_passes pasadas por paso.

    Un enemigo con CLeavingBase (el E que sale de un núcleo) no rebota contra su propia
    base; en cuanto deja de tocarla se le quita CLeavingBase y vuelve a rebotar como todos.
    """
    leaving = {enemy: c_lb.base for enemy, c_lb in world.get_component(CLeavingBase)}
    for pass_index in range(max_passes):
        collisions = system_collision(world, [ENEMY_ENEMY_PAIR, ENEMY_BASE_PAIR], world_size)
        base_pairs = [(enemy, base) for enemy, base in collisions[ENEMY_BASE_PAIR]
                      if leaving.get(enemy) != base]
        if pass_index == 0:
            _finish_leaving(world, leaving, collisions[ENEMY_BASE_PAIR])
        if not collisions[ENEMY_ENEMY_PAIR] and not base_pairs:
            return
        for enemy_a, enemy_b in collisions[ENEMY_ENEMY_PAIR]:
            _bounce(world, enemy_a, enemy_b, True, world_size)
        # Las bases van al final: como no se mueven, su corrección es la que queda.
        for enemy, base in base_pairs:
            _bounce(world, enemy, base, False, world_size)


def _finish_leaving(world: esper.World, leaving: dict[int, int],
                    base_pairs: list[tuple[int, int]]) -> None:
    """Quita CLeavingBase a los enemigos que ya no tocan la base de la que salieron."""
    touching = set(base_pairs)
    for enemy, base in list(leaving.items()):
        if (enemy, base) not in touching:
            world.remove_component(enemy, CLeavingBase)
            del leaving[enemy]
