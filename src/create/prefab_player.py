import esper
import pygame

from src.create.prefab_hitbox import add_hitbox
from src.create.prefab_square import create_square
from src.ecs.components.c_directional_sprite import CDirectionalSprite
from src.ecs.components.c_hitbox import CollisionLayer
from src.ecs.components.c_player_ability import CPlayerAbility
from src.ecs.components.c_player_movement import CPlayerMovement
from src.ecs.components.c_player_weapon import CPlayerWeapon
from src.ecs.components.c_special_shot import CSpecialShot
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.tags.c_tag_player import CTagPlayer
from src.ecs.systems.s_player_sprite import direction_index
from src.engine.service_locator import ServiceLocator

SPRITE_DIRECTIONS = 8


def build_directional_frame(image: pygame.Surface, index: int, canvas_size: tuple[int, int]) -> pygame.Surface:
    """image girada index * 45° en sentido horario, centrada en un lienzo de canvas_size.

    Lanza ValueError si la rotación no cabe en el lienzo: así una imagen más
    grande no queda recortada sin que nadie lo note.
    """
    angle = index * 360 / SPRITE_DIRECTIONS
    rotated = pygame.transform.rotate(image, -angle)
    if rotated.get_width() > canvas_size[0] or rotated.get_height() > canvas_size[1]:
        raise ValueError(f"La imagen de {image.get_size()} girada {angle:g}° mide {rotated.get_size()} "
                         f"y no cabe en el lienzo de {canvas_size}; agrandar size en la config")
    frame = pygame.Surface(canvas_size, pygame.SRCALPHA)
    frame.blit(rotated, rotated.get_rect(center=frame.get_rect().center))
    return frame


def build_directional_frames(image: pygame.Surface, canvas_size: tuple[int, int]) -> list[pygame.Surface]:
    return [build_directional_frame(image, i, canvas_size) for i in range(SPRITE_DIRECTIONS)]


def get_directional_frames(image_path: str, canvas_size: tuple[int, int]) -> list[pygame.Surface]:
    """Los cuadros de image_path, generados una sola vez y guardados en el servicio de imágenes."""
    images = ServiceLocator.images_service
    key = f"{image_path}#dir@{canvas_size[0]}x{canvas_size[1]}"
    return [images.get_or_create(f"{key}/{i}",
                                 lambda i=i: build_directional_frame(images.get(image_path), i, canvas_size))
            for i in range(SPRITE_DIRECTIONS)]


def create_player(world: esper.World, player_info: dict, pos: pygame.Vector2,
                  special_shot: bool = False) -> int:
    movement = CPlayerMovement(player_info["movement"])
    size = player_info["size"]
    if "image" in player_info:
        frames = get_directional_frames(player_info["image"], (size["w"], size["h"]))
        sprite = CDirectionalSprite(frames)
        sprite.current = direction_index(movement.direction.x, movement.direction.y, len(frames))
        entity = world.create_entity()
        world.add_component(entity, CTransform(pygame.Vector2(pos)))
        world.add_component(entity, CVelocity(pygame.Vector2(0, 0)))
        world.add_component(entity, CSurface.from_surface(frames[sprite.current]))
        world.add_component(entity, sprite)
    else:
        entity = create_square(world, size, player_info["color"], pos)
    add_hitbox(world, entity, player_info, CollisionLayer.PLAYER)
    world.add_component(entity, movement)
    world.add_component(entity, CPlayerWeapon(player_info["weapon"]))
    if "ability" in player_info:
        world.add_component(entity, CPlayerAbility(player_info["ability"]))
    if special_shot:
        world.add_component(entity, CSpecialShot(player_info["special_shot"]))
    world.add_component(entity, CTagPlayer())
    return entity
