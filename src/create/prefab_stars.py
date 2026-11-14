import random

import esper
import pygame

from src.ecs.components.c_star import CStar
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_background import CTagBackground


def create_starfield(world: esper.World, stars_info: dict, viewport: pygame.Rect) -> list[int]:
    """Crea las estrellas del fondo repartidas al azar dentro del viewport.

    Las estrellas solo cubren lo que se ve (no todo el mundo): cuando una sale del
    viewport, system_starfield la pasa al lado opuesto.
    """
    layers = stars_info["layers"]
    weights = [layer["weight"] for layer in layers]
    size = pygame.Vector2(stars_info["size"], stars_info["size"])
    stars = []
    for _ in range(stars_info["count"]):
        layer = random.choices(layers, weights)[0]
        c = random.choice(stars_info["colors"])
        pos = pygame.Vector2(random.uniform(viewport.left, viewport.right),
                             random.uniform(viewport.top, viewport.bottom))
        blink = stars_info["blink"]["on"]
        star = CStar(layer["parallax"], random.uniform(blink["min"], blink["max"]))
        stars.append(world.create_entity(CTransform(pos), CSurface(size, pygame.Color(c["r"], c["g"], c["b"])),
                                         star, CTagBackground()))
    return stars
