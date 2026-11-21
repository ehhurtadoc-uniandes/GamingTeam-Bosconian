"""Obstáculos del mundo: rocas, rocas indestructibles y minas."""
import random

import esper
import pygame

from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_hitbox import CHitBox, CollisionLayer
from src.ecs.components.c_mine_blast import CMineBlast
from src.ecs.components.c_obstacle import CObstacle, ObstacleKind
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_animation import set_frame
from src.engine.service_locator import ServiceLocator
from src.utils.wrap import wrapped_delta


def create_obstacle(world: esper.World, obstacles_info: dict, kind: ObstacleKind,
                    center: pygame.Vector2, rng: random.Random) -> int:
    """Crea un obstáculo con centro en center (coordenadas de mundo).

    Rocas y minas son quietas. Si el tipo trae "speed" (la roca indestructible, LC-OBS-03.1),
    se mueve a esa rapidez en una dirección al azar; el wraparound la hace dar la vuelta al mundo.

    rng es el azar del nivel (con su semilla), para que la imagen elegida también salga
    siempre igual en ese nivel.

    La hitbox (capa OBSTACLE) es el sprite recortado "hitbox_margin" píxeles por cada lado.
    Es un margen y no un tamaño fijo porque las imágenes de un mismo tipo miden distinto.
    """
    info = obstacles_info[kind.value]
    image = ServiceLocator.images_service.get(rng.choice(info["images"]))
    c_s = CSurface.from_surface(image)
    entity = world.create_entity(c_s, CObstacle(kind, info["destructible"], info["points"]))
    if "animation" in info:
        anim = info["animation"]
        c_anim = CAnimation(anim["number_frames"], anim["framerate"])
        set_frame(c_s, c_anim)
        world.add_component(entity, c_anim)
    # Después de set_frame: el tamaño del sprite es el de un cuadro, no el de la tira completa.
    sprite_size = pygame.Vector2(c_s.area.size)
    margin = pygame.Vector2(info["hitbox_margin"], info["hitbox_margin"])
    world.add_component(entity, CHitBox(sprite_size - 2 * margin, margin, CollisionLayer.OBSTACLE))
    world.add_component(entity, CTransform(center - sprite_size / 2))
    if "speed" in info:
        direction = pygame.Vector2(1, 0).rotate(rng.uniform(0, 360))
        world.add_component(entity, CVelocity(direction * info["speed"]))
    return entity


def create_obstacles(world: esper.World, obstacles_info: dict, level_info: dict,
                     world_size: pygame.Vector2, avoid: list[pygame.Vector2]) -> list[int]:
    """Reparte al azar los obstáculos que pide level_info["obstacles"].

    Ninguno queda a menos de min_distance de los puntos de avoid (bases, inicio del
    jugador) ni de otro obstáculo. Con la misma "seed" el nivel siempre sale igual.
    """
    level_obstacles = level_info.get("obstacles")
    if not level_obstacles:
        return []
    rng = random.Random(level_obstacles.get("seed"))
    min_distance = level_obstacles.get("min_distance", 32)
    taken = [pygame.Vector2(p) for p in avoid]
    created = []
    for kind in ObstacleKind:
        for _ in range(level_obstacles.get(kind.value, 0)):
            center = _free_position(rng, world_size, taken, min_distance)
            taken.append(center)
            created.append(create_obstacle(world, obstacles_info, kind, center, rng))
    return created


def _free_position(rng: random.Random, world_size: pygame.Vector2, taken: list[pygame.Vector2],
                   min_distance: float) -> pygame.Vector2:
    """Posición al azar lejos de lo que ya está ocupado, midiendo con wraparound."""
    for _ in range(ServiceLocator.constants_service.obstacle_place_tries):
        pos = pygame.Vector2(rng.uniform(0, world_size.x), rng.uniform(0, world_size.y))
        if all(wrapped_delta(pos, other, world_size).length() >= min_distance for other in taken):
            return pos
    return pos  # mundo muy lleno: se acepta la última


def create_mine_blast(world: esper.World, blast_info: dict, center: pygame.Vector2) -> int:
    """Explosión de una mina centrada en center. Se borra sola al terminar su animación."""
    image = ServiceLocator.images_service.get(blast_info["image"])
    anim = blast_info["animation"]
    c_s = CSurface.from_surface(image)
    c_anim = CAnimation(anim["number_frames"], anim["framerate"], loop=False)
    set_frame(c_s, c_anim)
    pos = center - pygame.Vector2(c_s.area.size) / 2
    return world.create_entity(CTransform(pos), c_s, c_anim, CMineBlast(blast_info["radius"]))
