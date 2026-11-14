"""Aparición de enemigos durante el nivel (LC-ENE-01, #28).

Los enemigos salen al azar por cualquiera de los cuatro lados, justo fuera de lo
que ve la cámara, para que entren a la pantalla en vez de aparecer de golpe.
Cuántos y cada cuánto lo define el bloque "spawner" de cada nivel.
"""
import random

import esper
import pygame

from src.create.prefab_enemy import create_enemy
from src.ecs.components.c_camera import CCamera
from src.ecs.components.c_enemy_spawner import CEnemySpawner
from src.ecs.components.c_enemy import CEnemy, EnemyType
from src.ecs.systems.s_camera import view_top_left
from src.utils.wrap import wrap_position


def pick_enemy_type(weights: dict[EnemyType, float], rng: random.Random | None = None) -> EnemyType:
    """Elige un tipo al azar con probabilidad proporcional a su peso."""
    rng = rng or random
    types = list(weights)
    return rng.choices(types, weights=[weights[t] for t in types])[0]


def offscreen_offset(view_size: pygame.Vector2, size: pygame.Vector2, margin: float,
                     rng: random.Random | None = None) -> pygame.Vector2:
    """Posición al azar justo fuera de la vista, relativa a su esquina superior izquierda.

    Queda a margin píxeles del borde por un lado elegido al azar, con el cuerpo
    del enemigo (size) completamente afuera, y en cualquier punto a lo largo de ese lado.
    """
    rng = rng or random
    side = rng.choice(("top", "bottom", "left", "right"))
    if side in ("top", "bottom"):
        x = rng.uniform(-size.x, view_size.x)
        y = -size.y - margin if side == "top" else view_size.y + margin
        return pygame.Vector2(x, y)
    y = rng.uniform(-size.y, view_size.y)
    x = -size.x - margin if side == "left" else view_size.x + margin
    return pygame.Vector2(x, y)


def system_enemy_spawner(world: esper.World, delta_time: float, camera: CCamera,
                         enemies_info: dict, margin: float,
                         rng: random.Random | None = None) -> list[int]:
    """Cuenta el tiempo de cada CEnemySpawner y crea un enemigo cuando toca.

    enemies_info es assets/cfg/enemies.json y margin sale de spawner.json.
    Devuelve los enemigos creados en este paso. Va antes de system_enemy_state para
    que el enemigo nuevo ya decida su estado en el mismo paso.
    """
    rng = rng or random
    created = []
    for _, c_sp in world.get_component(CEnemySpawner):
        if not c_sp.active:
            continue
        c_sp.time_to_spawn -= delta_time * c_sp.rate_multiplier
        if c_sp.time_to_spawn > 0:
            continue
        c_sp.time_to_spawn += c_sp.interval
        if len(world.get_component(CEnemy)) >= c_sp.max_alive:
            continue
        enemy_type = pick_enemy_type(c_sp.weights, rng)
        size_info = enemies_info[enemy_type.value]["size"]
        size = pygame.Vector2(size_info["w"], size_info["h"])
        view_size = pygame.Vector2(camera.viewport.size)
        pos = view_top_left(camera) + offscreen_offset(view_size, size, margin, rng)
        wrap_position(pos, camera.world_size)
        created.append(create_enemy(world, enemies_info, pos, enemy_type, c_sp.wander_scale))
    return created
