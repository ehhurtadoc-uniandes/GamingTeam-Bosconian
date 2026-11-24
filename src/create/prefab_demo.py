import esper
import pygame

from src.create.prefab_player_bullet import bullet_angle, get_bullet_image
from src.ecs.components.c_demo_gun import CDemoGun
from src.ecs.components.c_lifetime import CLifetime
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.tags.c_tag_demo_bullet import CTagDemoBullet
from src.ecs.components.tags.c_tag_demo_target import CTagDemoTarget
from src.engine.service_locator import ServiceLocator


def create_demo_player(world: esper.World, player_info: dict, bullet_info: dict) -> int:
    image = ServiceLocator.images_service.get(player_info["image"])
    center = pygame.Vector2(player_info["center"]["x"], player_info["center"]["y"])
    pos = center - pygame.Vector2(image.get_size()) / 2
    return world.create_entity(CTransform(pos), CSurface.from_surface(image),
                               CDemoGun(player_info["fire_interval"], bullet_info))


def create_demo_target(world: esper.World, target_info: dict) -> int:
    velocity = pygame.Vector2(target_info["velocity"]["x"], target_info["velocity"]["y"])
    pos = pygame.Vector2(target_info["pos"]["x"], target_info["pos"]["y"])
    if "angle" in target_info:
        angle = target_info["angle"]
    else:
        angle = (bullet_angle(velocity) + 90) % 360 if velocity.length() > 0 else 0
    image = get_bullet_image(target_info["image"], angle)
    return world.create_entity(CTransform(pos), CVelocity(velocity), CSurface.from_surface(image),
                               CTagDemoTarget())


def create_demo_bullet(world: esper.World, bullet_info: dict, center: pygame.Vector2) -> int:
    image = get_bullet_image(bullet_info["image"], bullet_angle(pygame.Vector2(0, -1)))
    pos = pygame.Vector2(center) - pygame.Vector2(image.get_size()) / 2
    return world.create_entity(CTransform(pos), CVelocity(pygame.Vector2(0, -bullet_info["speed"])),
                               CSurface.from_surface(image), CLifetime(bullet_info["lifetime"]),
                               CTagDemoBullet())
