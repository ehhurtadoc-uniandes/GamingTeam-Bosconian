import math
import random

import esper
import pygame

from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_explosion_burst import CExplosionBurst
from src.ecs.components.c_lifetime import CLifetime
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.tags.c_tag_player import CTagPlayer
from src.engine.service_locator import ServiceLocator


def build_frames(explosion_info: dict) -> list[pygame.Surface]:
    width = explosion_info["size"]["w"]
    height = explosion_info["size"]["h"]
    if "image" in explosion_info:
        sheet = ServiceLocator.images_service.get(explosion_info["image"])
        return [sheet.subsurface(pygame.Rect(i * width, 0, width, height))
                for i in range(sheet.get_width() // width)]
    frames = []
    for frame_info in explosion_info["frames"]:
        frame = pygame.Surface((width, height), pygame.SRCALPHA)
        side = frame_info["size"]
        color = frame_info["color"]
        rect = pygame.Rect(0, 0, side["w"], side["h"])
        rect.center = (width // 2, height // 2)
        frame.fill((color["r"], color["g"], color["b"]), rect)
        frames.append(frame)
    return frames


def create_explosion(world: esper.World, explosion_info: dict, center: pygame.Vector2,
                     velocity: pygame.Vector2) -> int:
    frames = build_frames(explosion_info)
    animation = CAnimation(frames, explosion_info["frame_duration"])
    surface = CSurface.from_surface(frames[0])
    explosion = world.create_entity()
    world.add_component(explosion, CTransform(pygame.Vector2(center) - pygame.Vector2(surface.area.size) / 2))
    world.add_component(explosion, CVelocity(pygame.Vector2(velocity)))
    world.add_component(explosion, surface)
    world.add_component(explosion, animation)
    world.add_component(explosion, CLifetime(animation.total_duration))
    return explosion


def create_explosion_burst(world: esper.World, explosion_info: dict, burst_info: dict,
                           center: pygame.Vector2, velocity: pygame.Vector2) -> int:
    pending = [(0.0, pygame.Vector2(0, 0))]
    for _ in range(burst_info["count"] - 1):
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(0, burst_info["radius"])
        pending.append((random.uniform(0, burst_info["time_spread"]),
                        pygame.Vector2(math.cos(angle), math.sin(angle)) * distance))
    burst = world.create_entity()
    world.add_component(burst, CTransform(pygame.Vector2(center)))
    world.add_component(burst, CVelocity(pygame.Vector2(velocity)))
    world.add_component(burst, CExplosionBurst(explosion_info, pending))
    return burst


def create_explosion_for(world: esper.World, entity: int) -> int:
    configs = ServiceLocator.configs_service.get(ServiceLocator.constants_service.explosions_config)
    c_t = world.component_for_entity(entity, CTransform)
    c_s = world.component_for_entity(entity, CSurface)
    center = c_t.pos + pygame.Vector2(c_s.area.size) / 2
    velocity = world.component_for_entity(entity, CVelocity).vel if world.has_component(entity, CVelocity) \
        else pygame.Vector2(0, 0)
    if world.has_component(entity, CTagPlayer):
        return create_explosion_burst(world, configs["explosion"], configs["player_burst"], center, velocity)
    return create_explosion(world, configs["explosion"], center, velocity)


def destroy_with_explosion(world: esper.World, entity: int) -> None:
    create_explosion_for(world, entity)
    world.delete_entity(entity)
