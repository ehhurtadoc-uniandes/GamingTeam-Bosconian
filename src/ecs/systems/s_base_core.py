"""Núcleo de las bases que se abre, se cierra y lanza enemigos E (LC-BAS-06, LC-TEN-04, #27).

En modo STATIC el núcleo queda abierto y este sistema no hace nada con él. En modo
CYCLING recorre CLOSED -> OPENING -> OPEN -> CLOSING -> CLOSED y, cada vez que pasa
de OPENING a OPEN, lanza un E centrado en el núcleo. Los lanzamientos no dependen del
jugador ni del spawner del nivel.
"""
import esper
import pygame

from src.create.prefab_enemy import create_enemy
from src.ecs.components.c_base import CBase
from src.ecs.components.c_base_core import CBaseCore, CoreMode, CoreState, NEXT_CORE_STATE
from src.ecs.components.c_enemy import EnemyType
from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_leaving_base import CLeavingBase
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform


def system_base_core(world: esper.World, delta_time: float, enemies_info: dict) -> list[int]:
    """Avanza el ciclo de cada núcleo CYCLING y lanza un E en cada apertura.

    enemies_info es assets/cfg/enemies.json. Devuelve los enemigos creados en este paso.
    El tiempo sobrante pasa al estado siguiente, así que un delta_time largo atraviesa
    varios estados sin perder ni duplicar lanzamientos. Va después de system_enemy_spawner
    y antes de system_enemy_state, para que el E nuevo procese AIM en el mismo paso.
    """
    created = []
    components = world.get_components(CTransform, CSurface, CBaseCore)
    c_t: CTransform
    c_s: CSurface
    c_core: CBaseCore
    for core, (c_t, c_s, c_core) in components:
        if c_core.mode != CoreMode.CYCLING or not _belongs_to_live_base(world, core, c_core):
            continue
        previous_state = c_core.state
        c_core.time_in_state += delta_time
        while c_core.time_in_state >= c_core.durations[c_core.state]:
            c_core.time_in_state -= c_core.durations[c_core.state]
            c_core.state = NEXT_CORE_STATE[c_core.state]
            if c_core.state == CoreState.OPEN:
                created.append(_launch_enemy(world, c_core.base, center_of_core(c_t, c_s),
                                             enemies_info, c_core.wander_scale))
        if c_core.state != previous_state:
            set_core_surface(world, core, c_core.surfaces[c_core.state])
    return created


def center_of_core(c_t: CTransform, c_s: CSurface) -> pygame.Vector2:
    return c_t.pos + pygame.Vector2(c_s.area.size) / 2


def set_core_surface(world: esper.World, core: int, surface: pygame.Surface) -> None:
    """Cambia el aspecto del núcleo sin mover su centro ni su hitbox, aunque cambie de tamaño."""
    c_t = world.component_for_entity(core, CTransform)
    c_s = world.component_for_entity(core, CSurface)
    shift = (pygame.Vector2(c_s.area.size) - pygame.Vector2(surface.get_size())) / 2
    c_s.surf = surface
    c_s.area = surface.get_rect()
    c_t.pos += shift
    if world.has_component(core, CHitBox):
        world.component_for_entity(core, CHitBox).offset -= shift


def _belongs_to_live_base(world: esper.World, core: int, c_core: CBaseCore) -> bool:
    """True si la base del núcleo existe y su CBase.core sigue siendo este núcleo."""
    if not world.entity_exists(core) or not world.entity_exists(c_core.base) \
            or not world.has_component(c_core.base, CBase):
        return False
    return world.component_for_entity(c_core.base, CBase).core == core


def _launch_enemy(world: esper.World, base: int, center: pygame.Vector2, enemies_info: dict,
                  wander_scale: float) -> int:
    # create_enemy recibe la esquina superior izquierda: se resta la mitad del tamaño del E.
    size = enemies_info[EnemyType.E.value]["size"]
    pos = center - pygame.Vector2(size["w"], size["h"]) / 2
    enemy = create_enemy(world, enemies_info, pos, EnemyType.E, wander_scale=wander_scale)
    # Nace dentro del cuerpo de su base: no debe rebotar contra ella hasta haber salido.
    world.add_component(enemy, CLeavingBase(base))
    return enemy
