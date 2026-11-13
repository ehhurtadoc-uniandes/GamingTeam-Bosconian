"""Cálculos para un mundo con wraparound (RF-06).

El mundo es "toroidal": lo que sale por un borde aparece por el opuesto. Todas las
áreas usan estas funciones para medir distancias, así nada se rompe cerca del borde.
"""
import math

import pygame


def wrapped_delta(origin: pygame.Vector2, target: pygame.Vector2,
                  world_size: pygame.Vector2 | None = None) -> pygame.Vector2:
    """Vector de origin a target.

    Si se da world_size, se devuelve el camino más corto, que puede cruzar un borde.
    Ejemplo en un mundo de 100 de ancho: de x=95 a x=5 hay +10, no -90.
    """
    delta = target - origin
    if world_size is not None:
        if abs(delta.x) > world_size.x / 2:
            delta.x -= math.copysign(world_size.x, delta.x)
        if abs(delta.y) > world_size.y / 2:
            delta.y -= math.copysign(world_size.y, delta.y)
    return delta


def wrap_position(pos: pygame.Vector2, world_size: pygame.Vector2) -> None:
    """Deja pos dentro del mundo (entre 0 y el tamaño), dando la vuelta por los bordes."""
    pos.x %= world_size.x
    pos.y %= world_size.y


def world_size_from_config(world_info: dict) -> pygame.Vector2:
    """Tamaño del mundo a partir de world.json."""
    size = world_info["size"]
    return pygame.Vector2(size["w"], size["h"])
