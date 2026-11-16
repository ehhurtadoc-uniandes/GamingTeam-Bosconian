import esper

from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_surface import CSurface


def set_frame(c_s: CSurface, c_anim: CAnimation) -> None:
    """Deja el área de la superficie en el cuadro actual de la tira."""
    frame_width = c_s.surf.get_width() // c_anim.number_frames
    c_s.area.w = frame_width
    c_s.area.x = frame_width * c_anim.current_frame


def system_animation(world: esper.World, delta_time: float) -> None:
    """Avanza los cuadros de todas las animaciones según su framerate."""
    components = world.get_components(CSurface, CAnimation)
    c_s: CSurface
    c_anim: CAnimation
    for _, (c_s, c_anim) in components:
        if c_anim.finished:
            continue
        c_anim.time_left -= delta_time
        while c_anim.time_left <= 0 and not c_anim.finished:
            c_anim.time_left += c_anim.frame_time
            if c_anim.current_frame < c_anim.number_frames - 1:
                c_anim.current_frame += 1
            elif c_anim.loop:
                c_anim.current_frame = 0
            else:
                c_anim.finished = True
        set_frame(c_s, c_anim)
