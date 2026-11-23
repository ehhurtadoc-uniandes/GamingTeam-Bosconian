import esper

from src.ecs.components.c_blink import CBlink
from src.ecs.components.c_surface import CSurface


def system_blink(world: esper.World, delta_time: float) -> None:
    c_b: CBlink
    c_s: CSurface
    for _, (c_b, c_s) in world.get_components(CBlink, CSurface):
        c_b.time += delta_time
        if c_b.time >= c_b.interval:
            c_b.time -= c_b.interval
            c_b.visible = not c_b.visible
        # Cada cuadro, porque system_text puede cambiar la superficie del texto.
        c_s.surf.set_alpha(255 if c_b.visible else 0)
