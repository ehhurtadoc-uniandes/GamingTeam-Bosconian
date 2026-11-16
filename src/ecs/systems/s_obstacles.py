"""Choques con obstáculos y explosión de las minas."""
import esper
import pygame

from src.create.prefab_obstacle import create_mine_blast
from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_enemy import CEnemy
from src.ecs.components.c_mine_blast import CMineBlast
from src.ecs.components.c_obstacle import CObstacle, ObstacleKind
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_player_bullet import CTagPlayerBullet
from src.engine.service_locator import ServiceLocator
from src.utils.wrap import wrapped_delta


def obstacle_hitbox(c_t: CTransform, c_s: CSurface, c_obs: CObstacle) -> pygame.Rect:
    """Rectángulo de choque: el sprite recortado hitbox_margin píxeles por lado."""
    rect = pygame.Rect(c_t.pos, c_s.area.size)
    return rect.inflate(-2 * c_obs.hitbox_margin, -2 * c_obs.hitbox_margin)


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


def system_player_bullet_obstacle(world: esper.World, obstacles_info: dict) -> None:
    """Una bala del jugador que toca un obstáculo se borra (la absorbe incluso una roca
    indestructible) y el obstáculo reacciona según su tipo. Los puntos van al puntaje.

    Sin wrapped_delta: las balas mueren al salir de la cámara, así que nunca comparan
    posiciones a lados opuestos del borde del mundo.
    """
    bullets = [(bullet, pygame.Rect(c_t.pos, c_s.area.size))
               for bullet, (c_t, c_s, _) in world.get_components(CTransform, CSurface, CTagPlayerBullet)]
    for obstacle, (c_t, c_s, c_obs) in world.get_components(CTransform, CSurface, CObstacle):
        hitbox = obstacle_hitbox(c_t, c_s, c_obs)
        for bullet, bullet_rect in bullets:
            if world.entity_exists(bullet) and hitbox.colliderect(bullet_rect):
                world.delete_entity(bullet)
                ServiceLocator.game_state_service.add_score(hit_obstacle(world, obstacle, obstacles_info))
                break


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
