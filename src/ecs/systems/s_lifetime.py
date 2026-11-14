import esper

from src.ecs.components.c_lifetime import CLifetime


def system_lifetime(world: esper.World, delta_time: float) -> None:
    """Borra las entidades con CLifetime cuando se les acaba el tiempo.

    El borrado es diferido: la entidad desaparece al final del paso (Scene.simulate).
    """
    c_l: CLifetime
    for entity, c_l in world.get_component(CLifetime):
        c_l.remaining -= delta_time
        if c_l.remaining <= 0:
            world.delete_entity(entity)
