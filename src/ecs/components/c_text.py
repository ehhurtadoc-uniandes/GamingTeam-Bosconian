from enum import Enum

import pygame


class TextAlignment(Enum):
    LEFT = 0
    CENTER = 1
    RIGHT = 2


class CText:
    """Texto de interfaz. Para cambiarlo basta con modificar text, color o font; system_text lo vuelve a dibujar.

    anchor es el punto de la pantalla donde se alinea el texto: su borde izquierdo, su centro
    o su borde derecho según alignment, y siempre su borde superior. system_text recalcula
    CTransform.pos a partir de anchor en cada frame, así que para mover un texto hay que
    cambiar anchor, no CTransform.pos.
    """

    def __init__(self, text: str, font: pygame.font.Font, color: pygame.Color,
                 anchor: pygame.Vector2, alignment: TextAlignment = TextAlignment.LEFT) -> None:
        self.text = text
        self.font = font
        self.color = color
        self.anchor = anchor
        self.alignment = alignment
        self.rendered: tuple[str, pygame.Color, pygame.font.Font] | None = None

    def render_key(self) -> tuple[str, pygame.Color, pygame.font.Font]:
        """Lo que define cómo se ve el texto. El color se copia para detectar cambios hechos en sitio."""
        return self.text, pygame.Color(self.color), self.font
