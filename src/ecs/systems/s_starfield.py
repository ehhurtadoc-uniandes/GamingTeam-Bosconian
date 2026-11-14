"""Fondo de estrellas con color, parpadeo y parallax."""
import random

import esper

from src.ecs.components.c_camera import CCamera
from src.ecs.components.c_star import CStar
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform


def system_starfield(world: esper.World, delta_time: float, camera: CCamera, blink_info: dict) -> None:
    """Mueve las estrellas al contrario de la cámara y las hace parpadear.

    Parallax: cada estrella se mueve solo una fracción (parallax) de lo que se movió
    la cámara, así parece que está más lejos que el resto del mundo. Va después de
    system_camera, que calcula camera.last_move.
    """
    view = camera.viewport
    components = world.get_components(CTransform, CSurface, CStar)
    c_t: CTransform
    c_s: CSurface
    c_star: CStar
    for _, (c_t, c_s, c_star) in components:
        c_t.pos -= camera.last_move * c_star.parallax
        # Si sale del viewport, entra por el lado opuesto.
        c_t.pos.x = view.left + (c_t.pos.x - view.left) % view.width
        c_t.pos.y = view.top + (c_t.pos.y - view.top) % view.height

        c_star.time_left -= delta_time
        if c_star.time_left <= 0:
            c_star.visible = not c_star.visible
            times = blink_info["on"] if c_star.visible else blink_info["off"]
            c_star.time_left = random.uniform(times["min"], times["max"])
            # Apagar es dejarla transparente: así system_rendering no necesita saber de estrellas.
            c_s.surf.set_alpha(255 if c_star.visible else 0)
