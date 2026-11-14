import esper
import pygame

from src.ecs.components.c_camera import CCamera
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_offscreen_despawn import CTagOffscreenDespawn
from src.ecs.systems.s_camera import is_visible


def system_offscreen_despawn(world: esper.World, screen_rect: pygame.Rect | None = None,
                             camera: CCamera | None = None) -> None:
    """Borra las entidades con CTagOffscreenDespawn que salieron del área de juego.

    Con camera, el área de juego es lo que ve la cámara (respetando el wraparound), no la
    ventana entera: el HUD y las barras no cuentan. Sin camera se usa screen_rect.
    El borrado es diferido: la entidad desaparece al final del paso (Scene.simulate).
    """
    components = world.get_components(CTransform, CSurface, CTagOffscreenDespawn)
    c_t: CTransform
    c_s: CSurface
    for entity, (c_t, c_s, _) in components:
        if camera is not None:
            offscreen = not is_visible(camera, c_t.pos, c_s.area.size)
        else:
            offscreen = (screen_rect is not None
                         and not screen_rect.colliderect(pygame.Rect(c_t.pos, c_s.area.size)))
        if offscreen:
            world.delete_entity(entity)
