import esper
import pygame

from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_ui import CTagUI
from src.engine.service_locator import ServiceLocator


def create_logo(world: esper.World, logo_info: dict) -> int:
    """Imagen del título centrada en x sobre anchor; y es el borde de arriba."""
    image = ServiceLocator.images_service.get(logo_info["image"])
    anchor = logo_info["anchor"]
    pos = pygame.Vector2(anchor["x"] - image.get_width() / 2, anchor["y"])
    return world.create_entity(CTransform(pos), CSurface.from_surface(image), CTagUI())
