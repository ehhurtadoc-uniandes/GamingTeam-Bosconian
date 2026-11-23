import math

import esper
import pygame

from src.create.prefab_hitbox import add_hitbox
from src.create.prefab_square import create_square
from src.ecs.components.c_hitbox import CollisionLayer
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.tags.c_tag_offscreen_despawn import CTagOffscreenDespawn
from src.ecs.components.tags.c_tag_player_bullet import CTagPlayerBullet
from src.engine.service_locator import ServiceLocator


def bullet_angle(direction: pygame.Vector2) -> int:
    return round(math.degrees(math.atan2(direction.y, direction.x))) % 360


def get_bullet_image(image_path: str, angle: int) -> pygame.Surface:
    images = ServiceLocator.images_service
    return images.get_or_create(f"{image_path}#rot{angle}",
                                lambda: pygame.transform.rotate(images.get(image_path), -angle))


def create_player_bullet(world: esper.World, bullet_info: dict, center: pygame.Vector2,
                         direction: pygame.Vector2) -> int:
    direction = pygame.Vector2(direction).normalize()
    if "image" in bullet_info:
        image = get_bullet_image(bullet_info["image"], bullet_angle(direction))
        bullet = world.create_entity()
        world.add_component(bullet, CTransform(pygame.Vector2(center) - pygame.Vector2(image.get_size()) / 2))
        world.add_component(bullet, CVelocity(pygame.Vector2(0, 0)))
        world.add_component(bullet, CSurface.from_surface(image))
    else:
        size = bullet_info["size"]
        pos = pygame.Vector2(center) - pygame.Vector2(size["w"], size["h"]) / 2
        bullet = create_square(world, size, bullet_info["color"], pos)
    world.component_for_entity(bullet, CVelocity).vel = direction * bullet_info["speed"]
    add_hitbox(world, bullet, bullet_info, CollisionLayer.PLAYER_BULLET)
    world.add_component(bullet, CTagOffscreenDespawn())
    world.add_component(bullet, CTagPlayerBullet())
    return bullet
