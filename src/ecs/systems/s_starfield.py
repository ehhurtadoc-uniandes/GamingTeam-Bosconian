"""Fondo de estrellas con color, parpadeo y parallax."""
import random

import esper
import pygame

from src.ecs.components.c_camera import CCamera
from src.ecs.components.c_star import CStar
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform


def system_starfield(world: esper.World, delta_time: float, camera: CCamera, blink_info: dict) -> None:
    """Mueve las estrellas al contrario de la cámara y las hace parpadear.

    Parallax: cada estrella se mueve solo una fracción (parallax) de lo que se movió
    la cámara, así parece que está más lejos que el resto del mundo. Va después de
    system_camera, que calcula camera.last_move. El parpadeo es system_star_blink.
    """
    view = camera.viewport
    c_t: CTransform
    c_star: CStar
    for _, (c_t, c_star) in world.get_components(CTransform, CStar):
        c_t.pos -= camera.last_move * c_star.parallax
        # Si sale del viewport, entra por el lado opuesto.
        c_t.pos.x = view.left + (c_t.pos.x - view.left) % view.width
        c_t.pos.y = view.top + (c_t.pos.y - view.top) % view.height
    system_star_blink(world, delta_time, blink_info)


def system_starfield_fall(world: esper.World, delta_time: float, fall_speed: float,
                          view: pygame.Rect, blink_info: dict) -> None:
    """Estrellas de los menús: bajan y parpadean (LC-EST-04).

    Cada estrella baja a fall_speed * parallax px/s, así las capas lejanas bajan más lento.
    Al salir por abajo vuelven a entrar por arriba.
    """
    c_t: CTransform
    c_star: CStar
    for _, (c_t, c_star) in world.get_components(CTransform, CStar):
        c_t.pos.y += fall_speed * c_star.parallax * delta_time
        c_t.pos.y = view.top + (c_t.pos.y - view.top) % view.height
    system_star_blink(world, delta_time, blink_info)


def system_star_blink(world: esper.World, delta_time: float, blink_info: dict) -> None:
    """Las estrellas brillan lentamente: su transparencia sube de 0 a 255 y baja, a una
    velocidad fija (blink_info["speed"], en alpha por segundo) pero cada una a su tiempo (LC-EST-02).

    Sola, deja las estrellas quietas pero brillando (pausa).
    """
    speed = blink_info["speed"]
    c_s: CSurface
    c_star: CStar
    for _, (c_s, c_star) in world.get_components(CSurface, CStar):
        c_star.alpha += speed * delta_time if c_star.rising else -speed * delta_time
        if c_star.alpha >= 255:
            c_star.alpha, c_star.rising = 255, False
        elif c_star.alpha <= 0:
            c_star.alpha, c_star.rising = 0, True
        # La transparencia va en la superficie: así system_rendering no necesita saber de estrellas.
        c_s.surf.set_alpha(int(c_star.alpha))
