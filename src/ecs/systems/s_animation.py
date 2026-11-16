import esper

from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_surface import CSurface


def system_animation(world: esper.World, delta_time: float) -> None:
    c_s: CSurface
    c_a: CAnimation
    for _, (c_s, c_a) in world.get_components(CSurface, CAnimation):
        c_a.elapsed += delta_time
        index = min(int(c_a.elapsed / c_a.frame_duration), len(c_a.frames) - 1)
        c_s.surf = c_a.frames[index]
        c_s.area = c_s.surf.get_rect()
