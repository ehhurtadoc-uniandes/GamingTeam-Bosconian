"""Creación de las balas de las torretas de base (LC-BAS-05)."""
import esper
import pygame

from src.ecs.components.c_lifetime import CLifetime
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.tags.c_tag_enemy import CTagEnemyBullet
from src.engine.service_locator import ServiceLocator


def create_turret_bullet(world: esper.World, bullet_info: dict, center: pygame.Vector2,
                         direction: pygame.Vector2) -> int:
    """Crea una bala con centro en center que avanza en línea recta según direction.

    bullet_info es la sección "bullet" de assets/cfg/base.json: size y color (o
    image), speed en px/s y lifetime en segundos. direction no necesita estar
    normalizada, pero no puede ser cero.
    """
    if "image" in bullet_info:
        surface = CSurface.from_surface(ServiceLocator.images_service.get(bullet_info["image"]))
    else:
        size = bullet_info["size"]
        color = bullet_info["color"]
        surface = CSurface(pygame.Vector2(size["w"], size["h"]),
                           pygame.Color(color["r"], color["g"], color["b"]))
    pos = pygame.Vector2(center) - pygame.Vector2(surface.area.size) / 2
    vel = pygame.Vector2(direction).normalize() * bullet_info["speed"]

    bullet = world.create_entity()
    world.add_component(bullet, CTransform(pos))
    world.add_component(bullet, CVelocity(vel))
    world.add_component(bullet, surface)
    world.add_component(bullet, CLifetime(bullet_info["lifetime"]))
    world.add_component(bullet, CTagEnemyBullet())
    return bullet
