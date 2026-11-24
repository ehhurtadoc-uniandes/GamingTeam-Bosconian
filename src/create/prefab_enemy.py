"""Creación de entidades del área Enemigos e IA."""
import esper
import pygame

from src.create.prefab_hitbox import add_hitbox
from src.create.prefab_player import get_directional_frames
from src.create.prefab_square import create_square
from src.ecs.components.c_directional_sprite import CDirectionalSprite
from src.ecs.components.c_hitbox import CollisionLayer
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.c_enemy_state import CEnemyState, EnemyState
from src.ecs.components.c_steering import CSteering
from src.ecs.components.c_enemy import CEnemy, EnemyType


def create_enemy(world: esper.World, enemies_info: dict, pos: pygame.Vector2,
                 enemy_type: EnemyType, wander_scale: float = 1.0) -> int:
    """Crea una nave enemiga de tipo I, P o E.

    enemies_info es todo assets/cfg/enemies.json; se usa la entrada del tipo.
    wander_scale multiplica el desvío aleatorio de todos los estados para
    ajustarlo según la dificultad del nivel (LC-ENE-02.1). Mientras no estén
    los sprites, se dibuja como un cuadrado del color configurado.
    """
    info = enemies_info[enemy_type.value]
    states_info = _scale_wander(info["states"], wander_scale)

    if "image" in info:
        frames = get_directional_frames(info["image"], (info["size"]["w"], info["size"]["h"]))
        entity = world.create_entity(CTransform(pygame.Vector2(pos)), CVelocity(pygame.Vector2(0, 0)),
                                     CSurface.from_surface(frames[0]), CDirectionalSprite(frames))
    else:
        entity = create_square(world, info["size"], info["color"], pos)
    add_hitbox(world, entity, info, CollisionLayer.ENEMY)
    world.add_component(entity, CSteering(info["steering"]))
    world.add_component(entity, CEnemyState(EnemyState(info["initial_state"]), info["steering"], states_info))
    world.add_component(entity, CEnemy(enemy_type, info["points"]))
    return entity


def _scale_wander(states_info: dict, wander_scale: float) -> dict:
    """Copia de states_info con wander_strength multiplicado (no modifica la config cargada)."""
    scaled = {}
    for name, state in states_info.items():
        scaled[name] = dict(state)
        if "wander_strength" in state:
            scaled[name]["wander_strength"] = state["wander_strength"] * wander_scale
    return scaled
