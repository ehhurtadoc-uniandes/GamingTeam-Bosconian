import esper
import pygame

from src.create.prefab_hitbox import add_hitbox
from src.create.prefab_square import create_square
from src.ecs.components.c_directional_sprite import CDirectionalSprite
from src.ecs.components.c_hitbox import CollisionLayer
from src.ecs.components.c_player_movement import CPlayerMovement
from src.ecs.components.c_player_weapon import CPlayerWeapon
from src.ecs.components.c_surface import CSurface
from src.ecs.components.tags.c_tag_player import CTagPlayer
from src.ecs.systems.s_player_sprite import direction_index
from src.engine.service_locator import ServiceLocator

SPRITE_DIRECTIONS = 8


def build_directional_frames(image: pygame.Surface, canvas_size: tuple[int, int]) -> list[pygame.Surface]:
    frames = []
    for i in range(SPRITE_DIRECTIONS):
        rotated = pygame.transform.rotate(image, -i * 360 / SPRITE_DIRECTIONS)
        frame = pygame.Surface(canvas_size, pygame.SRCALPHA)
        frame.blit(rotated, rotated.get_rect(center=frame.get_rect().center))
        frames.append(frame)
    return frames


def create_player(world: esper.World, player_info: dict, pos: pygame.Vector2) -> int:
    entity = create_square(world, player_info["size"], player_info["color"], pos)
    movement = CPlayerMovement(player_info["movement"])
    if "image" in player_info:
        image = ServiceLocator.images_service.get(player_info["image"])
        size = player_info["size"]
        frames = build_directional_frames(image, (size["w"], size["h"]))
        sprite = CDirectionalSprite(frames)
        sprite.current = direction_index(movement.direction.x, movement.direction.y, len(frames))
        world.add_component(entity, CSurface.from_surface(frames[sprite.current]))
        world.add_component(entity, sprite)
    add_hitbox(world, entity, player_info, CollisionLayer.PLAYER)
    world.add_component(entity, movement)
    world.add_component(entity, CPlayerWeapon(player_info["weapon"]))
    world.add_component(entity, CTagPlayer())
    return entity
