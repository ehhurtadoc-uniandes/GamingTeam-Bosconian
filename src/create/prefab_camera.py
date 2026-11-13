import esper
import pygame

from src.ecs.components.c_camera import CCamera


def create_camera(world: esper.World, camera_info: dict, world_size: pygame.Vector2,
                  center: pygame.Vector2) -> int:
    """Crea la cámara con el viewport de world.json, mirando a center."""
    v = camera_info["viewport"]
    viewport = pygame.Rect(v["x"], v["y"], v["w"], v["h"])
    return world.create_entity(CCamera(viewport, world_size, center))
