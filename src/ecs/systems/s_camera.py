"""Cámara que sigue al jugador en un mundo con wraparound."""
import esper
import pygame

from src.ecs.components.c_camera import CCamera
from src.utils.wrap import wrap_position, wrapped_delta


def get_camera(world: esper.World) -> CCamera | None:
    """La cámara de la escena, o None si la escena no tiene (p. ej. un menú)."""
    for _, c_cam in world.get_component(CCamera):
        return c_cam
    return None


def system_camera(world: esper.World, target_center: pygame.Vector2) -> None:
    """Centra la cámara en target_center (el centro del jugador).

    Va después de system_wraparound, cuando el jugador ya está en su posición final del paso.
    """
    for _, c_cam in world.get_component(CCamera):
        new_center = pygame.Vector2(target_center)
        wrap_position(new_center, c_cam.world_size)
        # Por el camino corto: si el jugador cruzó un borde, la cámara se movió poquito, no todo el mundo.
        c_cam.last_move = wrapped_delta(c_cam.center, new_center, c_cam.world_size)
        c_cam.center = new_center


def world_to_screen(c_cam: CCamera, world_pos: pygame.Vector2) -> pygame.Vector2:
    """Convierte una posición del mundo a la pantalla.

    Se usa wrapped_delta para que un objeto "del otro lado" del borde aparezca
    pegado a la cámara y no a un mundo de distancia.
    """
    return pygame.Vector2(c_cam.viewport.center) + wrapped_delta(c_cam.center, world_pos, c_cam.world_size)


def is_visible(c_cam: CCamera, world_pos: pygame.Vector2, size: tuple[float, float]) -> bool:
    """True si un rectángulo del mundo (esquina superior izquierda y tamaño) se ve en el viewport."""
    screen_pos = world_to_screen(c_cam, world_pos)
    return c_cam.viewport.colliderect(pygame.Rect(screen_pos, size))


def view_top_left(c_cam: CCamera) -> pygame.Vector2:
    """Esquina superior izquierda de lo que se ve, en coordenadas de mundo."""
    pos = c_cam.center - pygame.Vector2(c_cam.viewport.size) / 2
    wrap_position(pos, c_cam.world_size)
    return pos
