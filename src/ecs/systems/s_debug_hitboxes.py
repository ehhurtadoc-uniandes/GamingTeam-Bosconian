import esper
import pygame

from src.ecs.components.c_camera import CCamera
from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_transform import CTransform
from src.ecs.systems.s_camera import world_to_screen


def system_debug_hitboxes(world: esper.World, screen: pygame.Surface, color: pygame.Color,
                          camera: CCamera | None = None) -> None:
    if camera is not None:
        screen.set_clip(camera.viewport)
    c_t: CTransform
    c_h: CHitBox
    for _, (c_t, c_h) in world.get_components(CTransform, CHitBox):
        pos = c_t.pos + c_h.offset
        if camera is not None:
            pos = world_to_screen(camera, pos)
        pygame.draw.rect(screen, color, pygame.Rect(pos, c_h.size), 1)
    screen.set_clip(None)
