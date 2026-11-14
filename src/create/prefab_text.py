"""Creación de textos de interfaz."""
import esper
import pygame

from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_text import CText, TextAlignment
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_ui import CTagUI
from src.ecs.systems.s_text import aligned_position


def create_text(world: esper.World, text: str, font: pygame.font.Font, color: pygame.Color,
                anchor: pygame.Vector2, alignment: TextAlignment = TextAlignment.LEFT) -> int:
    """Crea un texto de interfaz alineado en anchor (coordenadas de pantalla)."""
    c_text = CText(text, font, pygame.Color(color), pygame.Vector2(anchor), alignment)
    c_surface = CSurface.from_text(text, font, c_text.color)
    c_text.rendered = c_text.render_key()
    pos = aligned_position(c_text.anchor, c_surface.area.width, alignment)
    return world.create_entity(CTransform(pos), c_surface, c_text, CTagUI())
