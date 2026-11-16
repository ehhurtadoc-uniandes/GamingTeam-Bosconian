"""Creación de la HitBox de una entidad a partir de su configuración (LC-COL-02)."""
import esper
import pygame

from src.ecs.components.c_hitbox import CHitBox, CollisionLayer
from src.ecs.components.c_surface import CSurface


def add_hitbox(world: esper.World, entity: int, info: dict, layer: CollisionLayer,
               rotated: bool = False) -> None:
    """Agrega a entity un CHitBox centrado en su sprite. La entidad ya debe tener CSurface.

    info es la configuración de la entidad. Su sección "hitbox" es opcional:
    "size" es el tamaño de la caja y "offset" (opcional) mueve su centro respecto
    al centro del sprite. Sin esa sección, la caja es del tamaño del sprite.

    rotated es para las piezas de una base vertical: el JSON describe la pieza
    horizontal, así que el tamaño y el offset se rotan 90° en sentido horario,
    igual que rotate_offset en prefab_base.
    """
    sprite_size = pygame.Vector2(world.component_for_entity(entity, CSurface).area.size)
    hitbox_info = info.get("hitbox")
    if hitbox_info is None:
        size = sprite_size
        center_shift = pygame.Vector2(0, 0)
    else:
        size = pygame.Vector2(hitbox_info["size"]["w"], hitbox_info["size"]["h"])
        shift = hitbox_info.get("offset", {"x": 0, "y": 0})
        center_shift = pygame.Vector2(shift["x"], shift["y"])
        if rotated:
            size = pygame.Vector2(size.y, size.x)
            center_shift = pygame.Vector2(-center_shift.y, center_shift.x)
    offset = sprite_size / 2 + center_shift - size / 2
    world.add_component(entity, CHitBox(size, offset, layer))
