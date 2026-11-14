import random

import esper
import pygame

from src.ecs.components.c_star import CStar
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_background import CTagBackground


def create_starfield(world: esper.World, stars_info: dict, viewport: pygame.Rect,
                     rng: random.Random | None = None) -> list[int]:
    """Crea las estrellas del fondo repartidas al azar dentro del viewport.

    Las estrellas solo cubren lo que se ve (no todo el mundo): cuando una sale del
    viewport, system_starfield la pasa al lado opuesto.
    """
    rng = rng or random
    layers = stars_info["layers"]
    weights = [layer["weight"] for layer in layers]
    size = pygame.Vector2(stars_info["size"], stars_info["size"])
    stars = []
    for _ in range(stars_info["count"]):
        layer = rng.choices(layers, weights)[0]
        c = rng.choice(stars_info["colors"])
        pos = pygame.Vector2(rng.uniform(viewport.left, viewport.right),
                             rng.uniform(viewport.top, viewport.bottom))
        blink = stars_info["blink"]["on"]
        star = CStar(layer["parallax"], rng.uniform(blink["min"], blink["max"]))
        stars.append(world.create_entity(CTransform(pos), CSurface(size, pygame.Color(c["r"], c["g"], c["b"])),
                                         star, CTagBackground()))
    return stars
