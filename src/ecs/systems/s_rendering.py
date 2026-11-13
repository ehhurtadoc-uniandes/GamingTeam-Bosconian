import esper
import pygame

from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_background import CTagBackground
from src.ecs.components.tags.c_tag_ui import CTagUI
from src.ecs.systems.s_camera import get_camera, world_to_screen


def system_rendering(world: esper.World, screen: pygame.Surface) -> None:
    """Dibuja en tres capas: fondo (CTagBackground), mundo y encima la interfaz (CTagUI).

    Si la escena tiene cámara, el mundo se dibuja relativo a ella, recortado a su
    viewport y sin dibujar lo que no se ve (culling). El fondo y la interfaz están
    en coordenadas de pantalla y la cámara no los mueve.
    """
    camera = get_camera(world)
    components = world.get_components(CTransform, CSurface)
    c_t: CTransform
    c_s: CSurface
    background = []
    world_items = []
    ui = []
    for entity, (c_t, c_s) in components:
        if world.has_component(entity, CTagUI):
            ui.append((c_t, c_s))
        elif world.has_component(entity, CTagBackground):
            background.append((c_t, c_s))
        else:
            world_items.append((c_t, c_s))

    if camera is not None:
        screen.set_clip(camera.viewport)
    for c_t, c_s in background:
        screen.blit(c_s.surf, c_t.pos, area=c_s.area)
    for c_t, c_s in world_items:
        if camera is None:
            screen.blit(c_s.surf, c_t.pos, area=c_s.area)
            continue
        screen_pos = world_to_screen(camera, c_t.pos)
        if camera.viewport.colliderect(pygame.Rect(screen_pos, c_s.area.size)):
            screen.blit(c_s.surf, screen_pos, area=c_s.area)
    screen.set_clip(None)

    for c_t, c_s in ui:
        screen.blit(c_s.surf, c_t.pos, area=c_s.area)
