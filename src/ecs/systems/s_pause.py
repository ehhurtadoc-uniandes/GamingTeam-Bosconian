"""Visibilidad de las entidades durante la pausa (LC-ESC-04.3)."""
import esper

from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_background import CTagBackground
from src.ecs.components.tags.c_tag_hidden import CTagHidden
from src.ecs.components.tags.c_tag_hidden_by_pause import CTagHiddenByPause
from src.ecs.components.tags.c_tag_hide_on_pause import CTagHideOnPause
from src.ecs.components.tags.c_tag_ui import CTagUI


def hides_on_pause(world: esper.World, entity: int) -> bool:
    """El mundo se esconde en pausa; el fondo no y la interfaz solo si lleva CTagHideOnPause."""
    if world.has_component(entity, CTagBackground):
        return False
    if world.has_component(entity, CTagUI):
        return world.has_component(entity, CTagHideOnPause)
    return True


def system_pause_visibility(world: esper.World, paused: bool) -> None:
    """Al pausar esconde jugador, enemigos, bases, balas y minimapa; al reanudar los vuelve a mostrar.

    Solo cambia CTagHidden: las entidades siguen ahí con su estado, así que al
    reanudar todo sigue exactamente donde estaba. Al reanudar solo se muestra lo que
    escondió la pausa (CTagHiddenByPause), no lo que ya estaba escondido por otra razón.
    """
    if not paused:
        for entity, _ in world.get_component(CTagHiddenByPause):
            world.remove_component(entity, CTagHiddenByPause)
            world.remove_component(entity, CTagHidden)
        return
    for entity, _ in world.get_components(CTransform, CSurface):
        if hides_on_pause(world, entity) and not world.has_component(entity, CTagHidden):
            world.add_component(entity, CTagHidden())
            world.add_component(entity, CTagHiddenByPause())
