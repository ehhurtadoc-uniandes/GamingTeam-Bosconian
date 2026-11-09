"""Creación de entidades del área Enemigos e IA."""
import esper
import pygame

from src.create.prefab_square import create_square
from src.ecs.components.c_enemy_state import CEnemyState, EnemyState
from src.ecs.components.c_steering import CSteering
from src.ecs.components.tags.c_tag_enemy import CTagEnemy, EnemyType


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

    entity = create_square(world, info["size"], info["color"], pos)
    world.add_component(entity, CSteering(info["steering"]))
    world.add_component(entity, CEnemyState(EnemyState(info["initial_state"]), info["steering"], states_info))
    world.add_component(entity, CTagEnemy(enemy_type, info["points"]))
    return entity


def _scale_wander(states_info: dict, wander_scale: float) -> dict:
    """Copia de states_info con wander_strength multiplicado (no modifica la config cargada)."""
    scaled = {}
    for name, state in states_info.items():
        scaled[name] = dict(state)
        if "wander_strength" in state:
            scaled[name]["wander_strength"] = state["wander_strength"] * wander_scale
    return scaled
