"""Etiquetas de depuración para ver el tipo y el estado de cada enemigo."""
import esper
import pygame

from src.ecs.components.c_camera import CCamera
from src.ecs.components.c_enemy import CEnemy
from src.ecs.components.c_enemy_state import CEnemyState
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.systems.s_camera import world_to_screen
from src.engine.service_locator import ServiceLocator


def enemy_label(c_en: CEnemy, c_es: CEnemyState) -> str:
    """Texto de la etiqueta, por ejemplo "I CHASE"."""
    return f"{c_en.enemy_type.value} {c_es.state.value}"


def system_enemy_labels(world: esper.World, screen: pygame.Surface, font: pygame.font.Font,
                        color: pygame.Color, camera: CCamera | None = None) -> None:
    """Dibuja sobre cada enemigo su tipo y su estado, centrado encima de la nave.

    Con camera, la etiqueta sigue a la nave en pantalla y no se dibuja fuera del área
    de juego. Las superficies salen de TextsService: hay pocas combinaciones de tipo y
    estado, así que cada una se renderiza una sola vez.
    """
    if camera is not None:
        screen.set_clip(camera.viewport)
    components = world.get_components(CTransform, CSurface, CEnemy, CEnemyState)
    c_t: CTransform
    c_s: CSurface
    c_en: CEnemy
    c_es: CEnemyState
    for _, (c_t, c_s, c_en, c_es) in components:
        text = ServiceLocator.texts_service.get(font, enemy_label(c_en, c_es), color)
        pos = world_to_screen(camera, c_t.pos) if camera is not None else c_t.pos
        rect = text.get_rect(midbottom=(pos.x + c_s.area.width / 2, pos.y - 1))
        screen.blit(text, rect)
    screen.set_clip(None)
