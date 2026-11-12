import esper
import pygame

from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_text import CText, TextAlignment
from src.ecs.components.c_transform import CTransform


def aligned_position(anchor: pygame.Vector2, width: float, alignment: TextAlignment) -> pygame.Vector2:
    """Esquina superior izquierda de un texto de ese ancho alineado en anchor."""
    if alignment == TextAlignment.CENTER:
        return pygame.Vector2(anchor.x - width / 2, anchor.y)
    if alignment == TextAlignment.RIGHT:
        return pygame.Vector2(anchor.x - width, anchor.y)
    return pygame.Vector2(anchor)


def system_text(world: esper.World) -> None:
    """Vuelve a dibujar los textos que cambiaron y los ubica según su alineación."""
    components = world.get_components(CText, CSurface, CTransform)
    c_text: CText
    c_s: CSurface
    c_t: CTransform
    for _, (c_text, c_s, c_t) in components:
        current = (c_text.text, pygame.Color(c_text.color))
        if c_text.rendered != current:
            c_s.surf = c_text.font.render(c_text.text, False, c_text.color)
            c_s.area = c_s.surf.get_rect()
            c_text.rendered = current
        c_t.pos = aligned_position(c_text.anchor, c_s.area.width, c_text.alignment)
