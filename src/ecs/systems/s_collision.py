from collections import defaultdict

import esper
import pygame

from src.ecs.components.c_hitbox import CHitBox, CollisionLayer
from src.ecs.components.c_transform import CTransform
from src.utils.wrap import wrapped_delta


def hitbox_center(c_t: CTransform, c_h: CHitBox) -> pygame.Vector2:
    return c_t.pos + c_h.offset + c_h.size / 2


def hitboxes_overlap(center_a: pygame.Vector2, size_a: pygame.Vector2,
                     center_b: pygame.Vector2, size_b: pygame.Vector2,
                     world_size: pygame.Vector2 | None = None) -> bool:
    delta = wrapped_delta(center_a, center_b, world_size)
    return abs(delta.x) < (size_a.x + size_b.x) / 2 and abs(delta.y) < (size_a.y + size_b.y) / 2


def system_collision(world: esper.World, pairs: list[tuple[CollisionLayer, CollisionLayer]],
                     world_size: pygame.Vector2 | None = None
                     ) -> dict[tuple[CollisionLayer, CollisionLayer], list[tuple[int, int]]]:
    by_layer: dict[CollisionLayer, list[tuple[int, pygame.Vector2, pygame.Vector2]]] = defaultdict(list)
    c_t: CTransform
    c_h: CHitBox
    for entity, (c_t, c_h) in world.get_components(CTransform, CHitBox):
        if world.entity_exists(entity):
            by_layer[c_h.layer].append((entity, hitbox_center(c_t, c_h), c_h.size))

    collisions: dict[tuple[CollisionLayer, CollisionLayer], list[tuple[int, int]]] = {}
    for layer_a, layer_b in pairs:
        found = []
        for entity_a, center_a, size_a in by_layer[layer_a]:
            for entity_b, center_b, size_b in by_layer[layer_b]:
                if entity_a == entity_b or (layer_a == layer_b and entity_a > entity_b):
                    continue
                if hitboxes_overlap(center_a, size_a, center_b, size_b, world_size):
                    found.append((entity_a, entity_b))
        collisions[(layer_a, layer_b)] = found
    return collisions
