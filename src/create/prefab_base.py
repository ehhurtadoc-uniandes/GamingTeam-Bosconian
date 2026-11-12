"""Creación de las bases enemigas (LC-BAS-02/03/04/05, RF-09)."""
import random

import esper
import pygame

from src.ecs.components.c_base import BaseOrientation, CBase
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_turret import CTurret
from src.ecs.components.tags.c_tag_base import CTagBase, CTagBaseCore, CTagBaseTurret
from src.engine.service_locator import ServiceLocator

TURRETS_PER_BASE = 6


def parse_orientation(value: str) -> BaseOrientation:
    """Convierte el texto del JSON en BaseOrientation, con un error claro si no es válido."""
    try:
        return BaseOrientation(value)
    except ValueError as error:
        valid = ", ".join(o.value for o in BaseOrientation)
        raise ValueError(f"orientación de base inválida '{value}' (válidas: {valid})") from error


def rotate_offset(offset: pygame.Vector2, orientation: BaseOrientation) -> pygame.Vector2:
    """Desplazamiento respecto al centro según la orientación.

    base.json describe la base horizontal; la vertical es la misma disposición
    rotada 90° en sentido horario: (x, y) -> (-y, x).
    """
    if orientation == BaseOrientation.VERTICAL:
        return pygame.Vector2(-offset.y, offset.x)
    return pygame.Vector2(offset)


def create_bases(world: esper.World, base_info: dict, level_info: dict,
                 rng: random.Random | None = None) -> list[int]:
    """Crea todas las bases de level_info["bases"]. Devuelve las entidades base.

    rng sortea el ritmo de cada torreta; con una semilla las pruebas son reproducibles.
    """
    bases = []
    for index, entry in enumerate(level_info.get("bases", [])):
        try:
            orientation = parse_orientation(entry["orientation"])
        except (KeyError, ValueError) as error:
            raise ValueError(f"nivel: base #{index}: {error}") from error
        pos = entry["pos"]
        bases.append(create_base(world, base_info, pygame.Vector2(pos["x"], pos["y"]), orientation, rng))
    return bases


def create_base(world: esper.World, base_info: dict, center: pygame.Vector2,
                orientation: BaseOrientation, rng: random.Random | None = None) -> int:
    """Crea una base con centro en center (coordenadas de mundo): cuerpo, seis torretas y núcleo.

    base_info es assets/cfg/base.json. Ninguna pieza lleva CVelocity, así que los
    sistemas de movimiento y steering no las desplazan.
    """
    offsets = base_info["turret_offsets"]
    if len(offsets) != TURRETS_PER_BASE:
        raise ValueError(f"base.json: turret_offsets debe tener {TURRETS_PER_BASE} entradas, "
                         f"tiene {len(offsets)}")

    # El cuerpo se crea primero para que se dibuje debajo de las piezas.
    base = world.create_entity()
    _add_piece(world, base, base_info["body"], center, pygame.Vector2(0, 0), orientation)
    world.add_component(base, CTagBase())

    turrets = []
    for offset in offsets:
        turret = world.create_entity()
        _add_piece(world, turret, base_info["turret"], center,
                   pygame.Vector2(offset["x"], offset["y"]), orientation)
        world.add_component(turret, CTagBaseTurret(base))
        world.add_component(turret, _turret_state(world, turret, base_info["turret"], orientation, rng))
        turrets.append(turret)

    core_info = base_info["core"]
    core = world.create_entity()
    core_offset = core_info.get("offset", {"x": 0, "y": 0})
    _add_piece(world, core, core_info, center,
               pygame.Vector2(core_offset["x"], core_offset["y"]), orientation)
    world.add_component(core, CTagBaseCore(base))

    world.add_component(base, CBase(orientation, turrets, core))
    return base


def _turret_state(world: esper.World, turret: int, turret_info: dict,
                  orientation: BaseOrientation, rng: random.Random | None) -> CTurret:
    """CTurret con un intervalo sorteado en fire_interval y un desfase inicial al azar.

    La torreta se crea cerrada, con el aspecto de turret_info (color o image);
    abierta usa open_color u open_image.
    """
    rng = rng or random
    interval_info = turret_info["fire_interval"]
    if not 0 < interval_info["min"] <= interval_info["max"]:
        raise ValueError("base.json: turret.fire_interval necesita 0 < min <= max")
    interval = rng.uniform(interval_info["min"], interval_info["max"])
    open_info = dict(turret_info)
    open_info.pop("image", None)
    if "open_image" in turret_info:
        open_info["image"] = turret_info["open_image"]
    else:
        open_info["color"] = turret_info["open_color"]
    closed_surf = world.component_for_entity(turret, CSurface).surf
    open_surf = _piece_surface(open_info, orientation).surf
    return CTurret(turret_info["activation_distance"], interval, rng.uniform(0, interval),
                   closed_surf, open_surf)


def _add_piece(world: esper.World, entity: int, piece_info: dict, center: pygame.Vector2,
               offset: pygame.Vector2, orientation: BaseOrientation) -> None:
    """Agrega CSurface y CTransform a una pieza, rotada según la orientación.

    Si piece_info trae "image" se usa ese sprite; si no, un rectángulo del color
    configurado (mientras no estén los sprites). CTransform.pos es la esquina
    superior izquierda, como en el resto del juego.
    """
    surface = _piece_surface(piece_info, orientation)
    pos = center + rotate_offset(offset, orientation) - pygame.Vector2(surface.area.size) / 2
    world.add_component(entity, CTransform(pos))
    world.add_component(entity, surface)


def _piece_surface(piece_info: dict, orientation: BaseOrientation) -> CSurface:
    if "image" in piece_info:
        image = ServiceLocator.images_service.get(piece_info["image"])
        if orientation == BaseOrientation.VERTICAL:
            image = pygame.transform.rotate(image, -90)
        return CSurface.from_surface(image)
    size = pygame.Vector2(piece_info["size"]["w"], piece_info["size"]["h"])
    if orientation == BaseOrientation.VERTICAL:
        size = pygame.Vector2(size.y, size.x)
    color = piece_info["color"]
    return CSurface(size, pygame.Color(color["r"], color["g"], color["b"]))
