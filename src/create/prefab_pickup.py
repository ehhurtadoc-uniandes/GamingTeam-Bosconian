import esper
import pygame

from src.create.prefab_hitbox import add_hitbox
from src.ecs.components.c_hitbox import CollisionLayer
from src.ecs.components.c_lifetime import CLifetime
from src.ecs.components.c_pickup import CPickup
from src.ecs.components.c_pickup_spawner import CPickupSpawner
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.engine.service_locator import ServiceLocator


def create_pickup(world: esper.World, pickup_info: dict, center: pygame.Vector2) -> int:
    image = ServiceLocator.images_service.get(pickup_info["image"])
    c_s = CSurface.from_surface(image)
    pos = pygame.Vector2(center) - pygame.Vector2(c_s.area.size) / 2
    pickup = world.create_entity(CTransform(pos), c_s, CPickup(), CLifetime(pickup_info["lifetime"]))
    add_hitbox(world, pickup, pickup_info, CollisionLayer.PICKUP)
    return pickup


def create_pickup_spawner(world: esper.World, level_info: dict) -> int | None:
    pickup_level = level_info.get("pickup")
    if not pickup_level:
        return None
    return world.create_entity(CPickupSpawner(pickup_level["interval"], pickup_level["chance"]))
