"""Paso de nivel (LC-ESC-04.4, #26)."""
import esper

from src.ecs.components.tags.c_tag_base import CTagBase


def level_cleared(world: esper.World) -> bool:
    """True si ya no queda ninguna base: el nivel se pasa al eliminarlas todas.

    Una base destruida se borra entera (destroy_base), así que basta con mirar los cuerpos.
    entity_exists descarta las que se borraron en este mismo paso y siguen en la base de datos.
    """
    return not any(world.entity_exists(base) for base, _ in world.get_component(CTagBase))
