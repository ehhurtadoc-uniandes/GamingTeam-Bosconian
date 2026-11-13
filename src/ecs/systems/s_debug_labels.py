"""Etiquetas de depuración para ver el tipo y el estado de cada enemigo."""
import esper
import pygame

from src.ecs.components.c_camera import CCamera
from src.ecs.components.c_enemy_state import CEnemyState
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_enemy import CTagEnemy
from src.ecs.systems.s_camera import world_to_screen


def enemy_label(c_tag: CTagEnemy, c_es: CEnemyState) -> str:
    """Texto de la etiqueta, por ejemplo "I CHASE"."""
    return f"{c_tag.enemy_type.value} {c_es.state.value}"


def system_enemy_labels(world: esper.World, screen: pygame.Surface, font: pygame.font.Font,
                        color: pygame.Color, camera: CCamera | None = None) -> None:
    """Dibuja sobre cada enemigo su tipo y su estado, centrado encima de la nave.

    Con camera, la etiqueta sigue a la nave en pantalla.
    """
    components = world.get_components(CTransform, CSurface, CTagEnemy, CEnemyState)
    c_t: CTransform
    c_s: CSurface
    c_tag: CTagEnemy
    c_es: CEnemyState
    for _, (c_t, c_s, c_tag, c_es) in components:
        text = font.render(enemy_label(c_tag, c_es), False, color)
        pos = world_to_screen(camera, c_t.pos) if camera is not None else c_t.pos
        rect = text.get_rect(midbottom=(pos.x + c_s.area.width / 2, pos.y - 1))
        screen.blit(text, rect)
