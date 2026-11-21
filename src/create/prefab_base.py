"""Creación de las bases enemigas (LC-BAS-02/03/04/05/06, RF-09)."""
import random

import esper
import pygame

from src.create.prefab_hitbox import add_hitbox
from src.ecs.components.c_base import BaseOrientation, CBase
from src.ecs.components.c_base_core import CBaseCore, CoreMode, CoreState
from src.ecs.components.c_base_part import CBasePart
from src.ecs.components.c_hitbox import CollisionLayer
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_turret import CTurret
from src.ecs.components.tags.c_tag_base import CTagBase, CTagBaseCore, CTagBaseTurret
from src.engine.service_locator import ServiceLocator

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


def parse_core_mode(level_info: dict) -> CoreMode:
    """Modo del núcleo del nivel ("core": {"mode": ...}). Sin el bloque o sin mode, STATIC."""
    core = level_info.get("core", {})
    if not isinstance(core, dict):
        raise ValueError("nivel: core debe ser un objeto, p. ej. {\"mode\": \"static\"}")
    value = core.get("mode", CoreMode.STATIC.value)
    try:
        return CoreMode(value)
    except ValueError as error:
        valid = ", ".join(m.value for m in CoreMode)
        raise ValueError(f"nivel: core.mode inválido '{value}' (válidos: {valid})") from error


def core_durations(core_info: dict) -> dict[CoreState, float]:
    """Duraciones en segundos de cada estado (base.json > core.durations), todas mayores que 0."""
    durations = core_info.get("durations")
    if not isinstance(durations, dict):
        raise ValueError("base.json: core.durations falta o no es un objeto")
    result = {}
    for state in CoreState:
        value = durations.get(state.value)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise ValueError(f"base.json: core.durations.{state.value} debe ser un número "
                             f"mayor que 0 (es {value!r})")
        result[state] = float(value)
    return result


def core_looks(core_info: dict) -> dict[CoreState, dict]:
    """Configuración visual de cada estado, lista para _piece_surface.

    Cada entrada de core.states trae "image" o "color" (y "size" opcional); lo que no
    trae se toma de core (tamaño, hitbox). Sin core.states, todos los estados usan el
    aspecto de core, como antes de #27.
    """
    common = {k: v for k, v in core_info.items() if k not in ("states", "durations", "image", "color")}
    states = core_info.get("states")
    if states is None:
        return {state: core_info for state in CoreState}
    if not isinstance(states, dict):
        raise ValueError("base.json: core.states debe ser un objeto")
    looks = {}
    for state in CoreState:
        field = f"base.json: core.states.{state.value}"
        look = states.get(state.value)
        if not isinstance(look, dict) or ("image" not in look and "color" not in look):
            raise ValueError(f"{field} necesita \"image\" o \"color\"")
        piece = dict(common)
        piece.update(look)
        if "image" not in piece:
            color = piece.get("color")
            if not isinstance(color, dict) or not all(channel in color for channel in ("r", "g", "b")):
                raise ValueError(f"{field}.color necesita r, g y b")
            if "size" not in piece or not all(k in piece["size"] for k in ("w", "h")):
                raise ValueError(f"{field} necesita \"size\" (o core.size) con w y h")
        looks[state] = piece
    return looks


def create_bases(world: esper.World, base_info: dict, level_info: dict) -> list[int]:
    """Crea todas las bases de level_info["bases"]. Devuelve las entidades base.

    El modo del núcleo sale de level_info["core"] y vale para todas las bases del nivel.
    La configuración del núcleo se valida aunque el nivel no tenga bases.
    """
    core_mode = parse_core_mode(level_info)
    core_looks(base_info["core"])
    if core_mode == CoreMode.CYCLING:
        core_durations(base_info["core"])
    # Igual que el spawner: sin spawner.wander_scale, 1.0.
    wander_scale = (level_info.get("spawner") or {}).get("wander_scale", 1.0)
    bases = []
    for index, entry in enumerate(level_info.get("bases", [])):
        try:
            orientation = parse_orientation(entry["orientation"])
        except (KeyError, ValueError) as error:
            raise ValueError(f"nivel: base #{index}: {error}") from error
        pos = entry["pos"]
        bases.append(create_base(world, base_info, pygame.Vector2(pos["x"], pos["y"]), orientation,
                                 core_mode, wander_scale))
    return bases


def create_base(world: esper.World, base_info: dict, center: pygame.Vector2,
                orientation: BaseOrientation, core_mode: CoreMode = CoreMode.STATIC,
                wander_scale: float = 1.0) -> int:
    """Crea una base con centro en center (coordenadas de mundo): cuerpo, seis torretas y núcleo.

    base_info es assets/cfg/base.json. Ninguna pieza lleva CVelocity, así que los
    sistemas de movimiento y steering no las desplazan. core_mode y wander_scale
    configuran el núcleo (CBaseCore); wander_scale se usa para los E que lanza.
    """
    offsets = base_info["turret_offsets"]
    turrets_per_base = ServiceLocator.constants_service.turrets_per_base
    if len(offsets) != turrets_per_base:
        raise ValueError(f"base.json: turret_offsets debe tener {turrets_per_base} entradas, "
                         f"tiene {len(offsets)}")

    # El cuerpo se crea primero para que se dibuje debajo de las piezas.
    base = world.create_entity()
    _add_piece(world, base, base_info["body"], center, pygame.Vector2(0, 0), orientation,
               CollisionLayer.BASE)
    world.add_component(base, CTagBase())

    turrets = []
    for offset in offsets:
        turret = world.create_entity()
        _add_piece(world, turret, base_info["turret"], center,
                   pygame.Vector2(offset["x"], offset["y"]), orientation, CollisionLayer.BASE_TURRET)
        world.add_component(turret, CTagBaseTurret())
        world.add_component(turret, CBasePart(base))
        world.add_component(turret, _turret_state(world, turret, base_info["turret"], orientation))
        turrets.append(turret)

    core = _create_core(world, base, base_info["core"], center, orientation, core_mode, wander_scale)

    world.add_component(base, CBase(orientation, turrets, core))
    return base


def _create_core(world: esper.World, base: int, core_info: dict, center: pygame.Vector2,
                 orientation: BaseOrientation, core_mode: CoreMode, wander_scale: float) -> int:
    """Núcleo con su CBaseCore: abierto en STATIC, cerrado al empezar el ciclo en CYCLING."""
    looks = core_looks(core_info)
    if core_mode == CoreMode.CYCLING:
        durations = core_durations(core_info)
        state = CoreState.CLOSED
    else:
        durations = {}
        state = CoreState.OPEN
    core = world.create_entity()
    core_offset = core_info.get("offset", {"x": 0, "y": 0})
    _add_piece(world, core, looks[state], center,
               pygame.Vector2(core_offset["x"], core_offset["y"]), orientation, CollisionLayer.BASE_CORE)
    surfaces = {s: _piece_surface(look, orientation).surf for s, look in looks.items()}
    # El estado inicial usa la superficie ya agregada, para que CSurface y CBaseCore coincidan.
    surfaces[state] = world.component_for_entity(core, CSurface).surf
    world.add_component(core, CTagBaseCore())
    world.add_component(core, CBasePart(base))
    world.add_component(core, CBaseCore(base, core_mode, state, durations, surfaces, wander_scale))
    return core


def _turret_state(world: esper.World, turret: int, turret_info: dict,
                  orientation: BaseOrientation) -> CTurret:
    """CTurret con un intervalo sorteado en fire_interval y un desfase inicial al azar.

    La torreta se crea cerrada, con el aspecto de turret_info (color o image);
    abierta usa open_color u open_image.
    """
    interval_info = turret_info["fire_interval"]
    if not 0 < interval_info["min"] <= interval_info["max"]:
        raise ValueError("base.json: turret.fire_interval necesita 0 < min <= max")
    interval = random.uniform(interval_info["min"], interval_info["max"])
    open_info = dict(turret_info)
    open_info.pop("image", None)
    if "open_image" in turret_info:
        open_info["image"] = turret_info["open_image"]
    else:
        open_info["color"] = turret_info["open_color"]
    closed_surf = world.component_for_entity(turret, CSurface).surf
    open_surf = _piece_surface(open_info, orientation).surf
    return CTurret(turret_info["activation_distance"], interval, random.uniform(0, interval),
                   closed_surf, open_surf)


def _add_piece(world: esper.World, entity: int, piece_info: dict, center: pygame.Vector2,
               offset: pygame.Vector2, orientation: BaseOrientation, layer: CollisionLayer) -> None:
    """Agrega CSurface y CTransform a una pieza, rotada según la orientación.

    Si piece_info trae "image" se usa ese sprite; si no, un rectángulo del color
    configurado (mientras no estén los sprites). CTransform.pos es la esquina
    superior izquierda, como en el resto del juego.
    """
    surface = _piece_surface(piece_info, orientation)
    pos = center + rotate_offset(offset, orientation) - pygame.Vector2(surface.area.size) / 2
    world.add_component(entity, CTransform(pos))
    world.add_component(entity, surface)
    add_hitbox(world, entity, piece_info, layer, rotated=orientation == BaseOrientation.VERTICAL)


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
