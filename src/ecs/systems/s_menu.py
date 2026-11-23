"""Selección en los menús de opciones (#33)."""
import esper

from src.ecs.components.c_menu import CMenu
from src.ecs.components.c_menu_item import CMenuItem
from src.ecs.components.c_text import CText
from src.engine.service_locator import ServiceLocator


def move_selection(selected: int, step: int, count: int) -> int:
    """Mueve la selección step lugares; al pasar de la última vuelve a la primera y al revés."""
    return (selected + step) % count


def move_menu_selection(world: esper.World, step: int) -> None:
    """Mueve la opción elegida del menú de la escena, con el sonido de menú (#38)."""
    menu = get_menu(world)
    menu.selected = move_selection(menu.selected, step, menu.count)
    ServiceLocator.sounds_service.play_effect("MENU_MOVE")


def get_menu(world: esper.World) -> CMenu:
    """El menú de la escena; cada escena tiene a lo sumo uno."""
    return world.get_component(CMenu)[0][1]


def selected_action(world: esper.World) -> str:
    """Acción (del JSON) de la opción elegida."""
    menu = get_menu(world)
    for _, c_item in world.get_component(CMenuItem):
        if c_item.index == menu.selected:
            return c_item.action
    raise ValueError("menú sin opción elegida")


def system_menu_highlight(world: esper.World) -> None:
    """Pinta la opción elegida con selected_color y las demás con color."""
    menu = get_menu(world)
    c_item: CMenuItem
    c_text: CText
    for _, (c_item, c_text) in world.get_components(CMenuItem, CText):
        c_text.color = menu.selected_color if c_item.index == menu.selected else menu.color
