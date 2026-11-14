import esper
import pygame

from src.ecs.components.c_lifetime import CLifetime
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_camera import CCamera
from src.ecs.components.c_transform import CTransform
from src.ecs.systems.s_camera import is_visible


def system_lifetime(world: esper.World, delta_time: float,
                    screen_rect: pygame.Rect | None = None, camera: CCamera | None = None) -> None:
    """Borra las entidades con CLifetime al cumplir su tiempo o al salir de screen_rect.

    Pensado para balas. Con camera, "salir de la pantalla" es salir de lo que ve
    la cámara (respetando el wraparound). Sin camera se usa screen_rect como área
    visible. El borrado es diferido: la entidad desaparece al final del paso (Scene.simulate).
    """
    components = world.get_components(CTransform, CSurface, CLifetime)
    c_t: CTransform
    c_s: CSurface
    c_l: CLifetime
    for entity, (c_t, c_s, c_l) in components:
        c_l.remaining -= delta_time
        expired = c_l.remaining <= 0
        if camera is not None:
            offscreen = not is_visible(camera, c_t.pos, c_s.area.size)
        else:
            offscreen = (screen_rect is not None
                         and not screen_rect.colliderect(pygame.Rect(c_t.pos, c_s.area.size)))
        if expired or offscreen:
            world.delete_entity(entity)
