import esper
import pygame

from src.ecs.components.c_lifetime import CLifetime
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform


def system_lifetime(world: esper.World, delta_time: float,
                    screen_rect: pygame.Rect | None = None) -> None:
    """Borra las entidades con CLifetime al cumplir su tiempo o al salir de screen_rect.

    Pensado para balas. screen_rect es el área visible en coordenadas de mundo;
    mientras no esté la cámara (#6) es el rectángulo de la ventana. El borrado es
    diferido: la entidad desaparece al final del paso (Scene.simulate).
    """
    components = world.get_components(CTransform, CSurface, CLifetime)
    c_t: CTransform
    c_s: CSurface
    c_l: CLifetime
    for entity, (c_t, c_s, c_l) in components:
        c_l.remaining -= delta_time
        expired = c_l.remaining <= 0
        offscreen = (screen_rect is not None
                     and not screen_rect.colliderect(pygame.Rect(c_t.pos, c_s.area.size)))
        if expired or offscreen:
            world.delete_entity(entity)
