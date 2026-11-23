"""Creación de textos de interfaz."""
import esper
import pygame

from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_text import CText, TextAlignment
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_ui import CTagUI
from src.ecs.systems.s_text import aligned_position
from src.engine.service_locator import ServiceLocator


def create_text(world: esper.World, text: str, font: pygame.font.Font, color: pygame.Color,
                anchor: pygame.Vector2, alignment: TextAlignment = TextAlignment.LEFT) -> int:
    """Crea un texto de interfaz alineado en anchor (coordenadas de pantalla)."""
    c_text = CText(text, font, pygame.Color(color), pygame.Vector2(anchor), alignment)
    c_surface = CSurface.from_text(text, font, c_text.color)
    c_text.rendered = c_text.render_key()
    pos = aligned_position(c_text.anchor, c_surface.area.width, alignment)
    return world.create_entity(CTransform(pos), c_surface, c_text, CTagUI())


def create_interface_text(world: esper.World, text: str, text_info: dict) -> int:
    """Texto de interfaz con la fuente de interface.json; text_info trae anchor, alignment y color del JSON.

    Si text_info trae "font_size", se usa ese tamaño en vez del de interface.json.
    """
    interface = ServiceLocator.configs_service.get(ServiceLocator.constants_service.interface_config)
    font = ServiceLocator.fonts_service.get(interface["font"], text_info.get("font_size", interface["font_size"]))
    color = text_info["color"]
    anchor = text_info["anchor"]
    return create_text(world, text, font, pygame.Color(color["r"], color["g"], color["b"]),
                       pygame.Vector2(anchor["x"], anchor["y"]), TextAlignment[text_info["alignment"]])
