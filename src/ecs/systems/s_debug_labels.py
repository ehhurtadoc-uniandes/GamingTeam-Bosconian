"""Etiquetas de depuración para ver el tipo y el estado de cada enemigo."""
import esper
import pygame

from src.ecs.components.c_enemy_state import CEnemyState
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_enemy import CTagEnemy


def enemy_label(c_tag: CTagEnemy, c_es: CEnemyState) -> str:
    """Texto de la etiqueta, por ejemplo "I CHASE"."""
    return f"{c_tag.enemy_type.value} {c_es.state.value}"


def system_enemy_labels(world: esper.World, screen: pygame.Surface, font: pygame.font.Font,
                        color: pygame.Color) -> None:
    """Dibuja sobre cada enemigo su tipo y su estado, centrado encima de la nave."""
    components = world.get_components(CTransform, CSurface, CTagEnemy, CEnemyState)
    c_t: CTransform
    c_s: CSurface
    c_tag: CTagEnemy
    c_es: CEnemyState
    for _, (c_t, c_s, c_tag, c_es) in components:
        text = font.render(enemy_label(c_tag, c_es), False, color)
        rect = text.get_rect(midbottom=(c_t.pos.x + c_s.area.width / 2, c_t.pos.y - 1))
        screen.blit(text, rect)
