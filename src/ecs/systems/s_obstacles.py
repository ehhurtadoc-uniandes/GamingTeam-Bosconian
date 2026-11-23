"""Choques con obstáculos y explosión de las minas."""
import esper
import pygame

from src.create.prefab_explosion import destroy_with_explosion
from src.create.prefab_obstacle import create_mine_blast
from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_enemy import CEnemy
from src.ecs.components.c_hitbox import CHitBox, CollisionLayer
from src.ecs.components.c_mine_blast import CMineBlast
from src.ecs.components.c_obstacle import CObstacle, ObstacleKind
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_collision import hitbox_center, system_collision
from src.ecs.systems.s_enemy_bounce import contact_normal, reflect
from src.engine.service_locator import ServiceLocator
from src.utils.wrap import wrapped_delta


BULLET_OBSTACLE_PAIR = (CollisionLayer.PLAYER_BULLET, CollisionLayer.OBSTACLE)
ENEMY_OBSTACLE_PAIR = (CollisionLayer.ENEMY, CollisionLayer.OBSTACLE)
ENEMY_BULLET_OBSTACLE_PAIR = (CollisionLayer.ENEMY_BULLET, CollisionLayer.OBSTACLE)
OBSTACLE_BASE_PAIR = (CollisionLayer.OBSTACLE, CollisionLayer.BASE)


def hit_obstacle(world: esper.World, obstacle: int, obstacles_info: dict) -> int:
    """Le pegaron al obstáculo. Devuelve los puntos que gana el jugador.

    - Roca: explota y desaparece (LC-COL-05: toda colisión provoca una explosión).
    - Roca indestructible: no le pasa nada (LC-OBS-03.2).
    - Mina: desaparece y deja una explosión que mata lo que esté cerca (LC-OBS-02.2).
    """
    c_obs = world.component_for_entity(obstacle, CObstacle)
    if not c_obs.destructible:
        return 0
    if c_obs.kind == ObstacleKind.MINE:
        c_t = world.component_for_entity(obstacle, CTransform)
        c_s = world.component_for_entity(obstacle, CSurface)
        create_mine_blast(world, obstacles_info["mine"]["blast"], c_t.pos + pygame.Vector2(c_s.area.size) / 2)
        world.delete_entity(obstacle)
    else:
        destroy_with_explosion(world, obstacle)
    return c_obs.points


def system_player_bullet_obstacle(world: esper.World, obstacles_info: dict,
                                  world_size: pygame.Vector2 | None = None) -> None:
    """Una bala del jugador que toca un obstáculo se borra (la absorbe incluso una roca
    indestructible) y el obstáculo reacciona según su tipo. Los puntos van al puntaje.

    Se comparan las hitbox (capas PLAYER_BULLET y OBSTACLE), no los sprites, y con
    world_size también cruzando los bordes del mundo: un obstáculo puede quedar partido
    por un borde y la bala llegarle desde el otro lado.
    """
    for bullet, obstacle in system_collision(world, [BULLET_OBSTACLE_PAIR], world_size)[BULLET_OBSTACLE_PAIR]:
        # Una bala ya gastada no rompe otro obstáculo, ni un obstáculo roto absorbe otra bala.
        if world.entity_exists(bullet) and world.entity_exists(obstacle):
            world.delete_entity(bullet)
            ServiceLocator.game_state_service.add_score(hit_obstacle(world, obstacle, obstacles_info))


def system_enemy_obstacle(world: esper.World, obstacles_info: dict,
                          world_size: pygame.Vector2 | None = None) -> None:
    """Choques de enemigos y balas enemigas con los obstáculos (LC-OBS-04 y LC-OBS-03.3).

    - Un enemigo que toca un obstáculo explota, y el obstáculo reacciona como con una bala:
      la roca se rompe, la mina explota y la roca indestructible sigue. No suma puntos:
      no lo derribó el jugador.
    - Una bala de torreta que toca un obstáculo se borra (el obstáculo la detiene).
    """
    collisions = system_collision(world, [ENEMY_OBSTACLE_PAIR, ENEMY_BULLET_OBSTACLE_PAIR], world_size)
    for enemy, obstacle in collisions[ENEMY_OBSTACLE_PAIR]:
        if world.entity_exists(enemy) and world.entity_exists(obstacle):
            destroy_with_explosion(world, enemy)
            hit_obstacle(world, obstacle, obstacles_info)
    for bullet, obstacle in collisions[ENEMY_BULLET_OBSTACLE_PAIR]:
        if world.entity_exists(bullet) and world.entity_exists(obstacle):
            world.delete_entity(bullet)


def system_obstacle_bounce(world: esper.World, world_size: pygame.Vector2 | None = None) -> None:
    """Las rocas indestructibles rebotan contra las bases sin destruirlas (LC-OBS-03.3).

    Solo rebotan los obstáculos que se mueven (tienen CVelocity). Se usan el mismo
    contact_normal y reflect del rebote de los enemigos: se saca a la roca de la base
    y se refleja su velocidad.
    """
    for obstacle, base in system_collision(world, [OBSTACLE_BASE_PAIR], world_size)[OBSTACLE_BASE_PAIR]:
        if not world.has_component(obstacle, CVelocity):
            continue
        c_t = world.component_for_entity(obstacle, CTransform)
        c_h = world.component_for_entity(obstacle, CHitBox)
        b_t = world.component_for_entity(base, CTransform)
        b_h = world.component_for_entity(base, CHitBox)
        contact = contact_normal(hitbox_center(c_t, c_h), c_h.size, hitbox_center(b_t, b_h), b_h.size,
                                 world_size)
        if contact is None:
            continue
        normal, overlap = contact
        c_v = world.component_for_entity(obstacle, CVelocity)
        c_v.vel = reflect(c_v.vel, normal)
        c_t.pos -= normal * overlap


def system_mine_blast(world: esper.World, world_size: pygame.Vector2,
                      player_center: pygame.Vector2) -> bool:
    """Mientras una mina explota, mata a los enemigos que estén dentro de su radio.

    Devuelve True si el jugador está dentro de alguna explosión, para que el área del
    jugador lo haga morir. Al terminar la animación la explosión se borra.
    """
    player_hit = False
    for blast, (c_t, c_s, c_anim, c_blast) in world.get_components(CTransform, CSurface, CAnimation,
                                                                   CMineBlast):
        center = c_t.pos + pygame.Vector2(c_s.area.size) / 2
        for enemy, (e_t, e_s, _) in world.get_components(CTransform, CSurface, CEnemy):
            enemy_center = e_t.pos + pygame.Vector2(e_s.area.size) / 2
            if world.entity_exists(enemy) and \
                    wrapped_delta(center, enemy_center, world_size).length() < c_blast.radius:
                world.delete_entity(enemy)
        if wrapped_delta(center, player_center, world_size).length() < c_blast.radius:
            player_hit = True
        if c_anim.finished:
            world.delete_entity(blast)
    return player_hit
