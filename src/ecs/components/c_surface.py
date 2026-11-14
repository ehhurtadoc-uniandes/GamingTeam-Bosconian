import pygame


class CSurface:
    def __init__(self, size: pygame.Vector2, color: pygame.Color) -> None:
        self.surf = pygame.Surface(size)
        self.surf.fill(color)
        self.area = self.surf.get_rect()

    @classmethod
    def from_surface(cls, surface: pygame.Surface) -> "CSurface":
        """CSurface a partir de una imagen ya cargada (por ejemplo, un sprite)."""
        c_surf = cls(pygame.Vector2(0, 0), pygame.Color(0, 0, 0))
        c_surf.surf = surface
        c_surf.area = surface.get_rect()
        return c_surf

    @classmethod
    def from_text(cls, text: str, font: pygame.font.Font, color: pygame.Color) -> "CSurface":
        """CSurface con el texto dibujado. Sin antialiasing, para que la fuente pixel se vea nítida."""
        return cls.from_surface(font.render(text, False, color))
