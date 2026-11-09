import esper

from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity


def system_movement(world: esper.World, delta_time: float) -> None:
    """Actualiza la posición de las entidades según su velocidad."""
    components = world.get_components(CTransform, CVelocity)
    c_t: CTransform
    c_v: CVelocity
    for _, (c_t, c_v) in components:
        c_t.pos += c_v.vel * delta_time
