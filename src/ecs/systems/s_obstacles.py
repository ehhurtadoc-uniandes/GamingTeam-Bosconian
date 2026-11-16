"""Choques con obstáculos y explosión de las minas."""
import esper
import pygame

from src.create.prefab_obstacle import create_mine_blast
from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_enemy import CEnemy
from src.ecs.components.c_hitbox import CollisionLayer
from src.ecs.components.c_mine_blast import CMineBlast
from src.ecs.components.c_obstacle import CObstacle, ObstacleKind
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.systems.s_collision import system_collision
from src.engine.service_locator import ServiceLocator
from src.utils.wrap import wrapped_delta


BULLET_OBSTACLE_PAIR = (CollisionLayer.PLAYER_BULLET, CollisionLayer.OBSTACLE)


def hit_obstacle(world: esper.World, obstacle: int, obstacles_info: dict) -> int:
    """Le pegaron al obstáculo. Devuelve los puntos que gana el jugador.

    - Roca: se destruye.
    - Roca indestructible: no le pasa nada.
    - Mina: se destruye y deja una explosión que mata lo que esté cerca.
    """
    c_obs = world.component_for_entity(obstacle, CObstacle)
    if not c_obs.destructible:
        return 0
    if c_obs.kind == ObstacleKind.MINE:
        c_t = world.component_for_entity(obstacle, CTransform)
        c_s = world.component_for_entity(obstacle, CSurface)
        create_mine_blast(world, obstacles_info["mine"]["blast"], c_t.pos + pygame.Vector2(c_s.area.size) / 2)
    world.delete_entity(obstacle)
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
