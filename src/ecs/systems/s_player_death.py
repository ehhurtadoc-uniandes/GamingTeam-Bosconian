import esper
import pygame

from src.create.prefab_explosion import create_explosion_for, destroy_with_explosion
from src.ecs.components.c_hitbox import CollisionLayer
from src.ecs.components.c_player_dead import CPlayerDead
from src.ecs.components.c_player_invulnerable import CPlayerInvulnerable
from src.ecs.components.c_player_movement import CPlayerMovement
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.tags.c_tag_hidden import CTagHidden
from src.ecs.components.tags.c_tag_player import CTagPlayer
from src.ecs.systems.s_collision import system_collision
from src.ecs.systems.s_obstacles import hit_obstacle
from src.engine.service_locator import ServiceLocator


def is_vulnerable(world: esper.World, player: int) -> bool:
    return (world.entity_exists(player)
            and not world.has_component(player, CPlayerDead)
            and not world.has_component(player, CPlayerInvulnerable))


def kill_player(world: esper.World, player: int, respawn_info: dict) -> None:
    create_explosion_for(world, player)
    game_over = not ServiceLocator.game_state_service.lose_life()
    world.add_component(player, CPlayerDead(respawn_info["delay"], game_over))
    world.add_component(player, CTagHidden())
    if world.has_component(player, CVelocity):
        world.component_for_entity(player, CVelocity).vel = pygame.Vector2(0, 0)
    world.component_for_entity(player, CPlayerMovement).speed = 0.0


def system_player_death(world: esper.World, respawn_info: dict, obstacles_info: dict,
                        world_size: pygame.Vector2 | None = None) -> None:
    """El jugador vulnerable que choca con un enemigo, una bala enemiga o un obstáculo muere (LC-COL-04).

    Lo que lo mató también se destruye: enemigos y balas con explosión, y el obstáculo
    como si le hubiera pegado una bala (hit_obstacle): la roca se rompe, la mina explota
    y la roca indestructible sigue ahí. Así no queda nada encima del punto del choque.
    No suma puntos: chocar no es derribar.
    """
    constants = ServiceLocator.constants_service
    pairs = [(CollisionLayer.PLAYER, layer) for layer in constants.player_death_layers]
    collisions = system_collision(world, pairs, world_size)
    for pair in pairs:
        for player, other in collisions[pair]:
            if not is_vulnerable(world, player) or not world.entity_exists(other):
                continue
            kill_player(world, player, respawn_info)
            if pair[1] == CollisionLayer.OBSTACLE:
                hit_obstacle(world, other, obstacles_info)
            elif pair[1] in constants.player_kills_layers:
                destroy_with_explosion(world, other)


def system_player_respawn(world: esper.World, delta_time: float, respawn_info: dict,
                          spawn_pos: pygame.Vector2) -> bool:
    """Pasado el retraso, el jugador muerto reaparece invulnerable en spawn_pos (el inicio del nivel).

    Reaparece en el inicio y no donde murió porque el nivel no pone obstáculos ahí.
    Devuelve True si murió sin vidas de reserva y ya pasó el retraso: la partida terminó.
    """
    game_over = False
    c_dead: CPlayerDead
    for player, (c_dead, _) in world.get_components(CPlayerDead, CTagPlayer):
        c_dead.remaining -= delta_time
        if c_dead.remaining > 0:
            continue
        if c_dead.game_over:
            game_over = True
            continue
        world.component_for_entity(player, CTransform).pos.update(spawn_pos)
        world.remove_component(player, CPlayerDead)
        world.remove_component(player, CTagHidden)
        world.add_component(player, CPlayerInvulnerable(respawn_info["invulnerable_time"]))
    return game_over


def system_player_invulnerability(world: esper.World, delta_time: float, respawn_info: dict) -> None:
    c_inv: CPlayerInvulnerable
    for player, (c_inv, _) in world.get_components(CPlayerInvulnerable, CTagPlayer):
        c_inv.elapsed += delta_time
        has_hidden = world.has_component(player, CTagHidden)
        if c_inv.elapsed >= c_inv.duration:
            world.remove_component(player, CPlayerInvulnerable)
            if has_hidden:
                world.remove_component(player, CTagHidden)
            continue
        blink_off = int(c_inv.elapsed / respawn_info["blink_interval"]) % 2 == 1
        if blink_off and not has_hidden:
            world.add_component(player, CTagHidden())
        elif not blink_off and has_hidden:
            world.remove_component(player, CTagHidden)
