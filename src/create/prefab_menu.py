"""Creación de menús de opciones (#33)."""
import esper
import pygame

from src.create.prefab_text import create_interface_text
from src.ecs.components.c_menu import CMenu
from src.ecs.components.c_menu_item import CMenuItem
from src.ecs.components.c_text import CText


def create_menu(world: esper.World, menu_info: dict, values: dict | None = None) -> int:
    """Crea el menú y una línea de texto por opción, separadas por line_height.

    values llena los campos del texto de cada opción, p. ej. {"level": 1} en "RONDA {level}".
    """
    menu = world.create_entity(CMenu(menu_info))
    anchor = menu_info["anchor"]
    for index, option in enumerate(menu_info["options"]):
        text_info = dict(menu_info, anchor={"x": anchor["x"], "y": anchor["y"] + index * menu_info["line_height"]})
        item = create_interface_text(world, option["text"].format(**(values or {})), text_info)
        world.add_component(item, CMenuItem(index, option["action"], option["text"]))
    return menu


def create_text_lines(world: esper.World, lines_info: dict) -> list[int]:
    """Crea un texto por línea de lines_info["text"], separadas por line_height (instrucciones, créditos)."""
    anchor = lines_info["anchor"]
    entities = []
    for index, line in enumerate(lines_info["text"]):
        text_info = dict(lines_info, anchor={"x": anchor["x"], "y": anchor["y"] + index * lines_info["line_height"]})
        entities.append(create_interface_text(world, line, text_info))
    return entities


def update_menu_values(world: esper.World, values: dict) -> None:
    """Vuelve a llenar los campos de las opciones (p. ej. al cambiar de ronda); system_text redibuja."""
    c_item: CMenuItem
    c_text: CText
    for _, (c_item, c_text) in world.get_components(CMenuItem, CText):
        c_text.text = c_item.template.format(**values)
