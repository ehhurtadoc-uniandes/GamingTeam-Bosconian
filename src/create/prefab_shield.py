import esper
import pygame

from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_shield_aura import CTagShieldAura
from src.engine.service_locator import ServiceLocator


def create_shield_aura(world: esper.World, image_path: str, center: pygame.Vector2) -> int:
    image = ServiceLocator.images_service.get(image_path)
    c_s = CSurface.from_surface(image)
    pos = pygame.Vector2(center) - pygame.Vector2(c_s.area.size) / 2
    return world.create_entity(CTransform(pos), c_s, CTagShieldAura())
