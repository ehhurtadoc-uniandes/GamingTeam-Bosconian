"""Máquina de estados de los enemigos I, P y E (patrón State, OBJ-08).

Este sistema decide QUÉ hace cada enemigo (perseguir, huir, vagar, ir recto)
ajustando los pesos de CSteering. CÓMO se mueve lo resuelve system_steering,
así que este sistema debe ejecutarse antes que él en cada frame.

Transiciones:
- I: CHASE --(duration)--> LEAVE --(lejos o duration)--> se elimina
- P: CHASE --(duration)--> WANDER
- E: AIM --(inmediato)--> STRAIGHT --(ya pasó al jugador y está lejos, o duration)--> se elimina

Eliminar por alejarse no es morir: no hay explosión ni puntos (eso es del
sistema de combate, #16).
"""
import esper
import pygame

from src.ecs.components.c_enemy_state import STEERING_OVERRIDES, CEnemyState, EnemyState
from src.ecs.components.c_steering import CSteering
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_steering import wrapped_delta


def change_state(c_es: CEnemyState, c_st: CSteering, new_state: EnemyState) -> None:
    """Entra a new_state: reinicia el temporizador y aplica sus pesos de steering."""
    c_es.state = new_state
    c_es.time_in_state = 0.0
    c_es.entered = True
    info = c_es.info()
    for attr in STEERING_OVERRIDES:
        setattr(c_st, attr, info.get(attr, c_es.base_steering.get(attr, 0.0)))


def system_enemy_state(world: esper.World, delta_time: float, target: pygame.Vector2,
                       world_size: pygame.Vector2 | None = None) -> None:
    """Actualiza el estado de todos los enemigos con CEnemyState.

    target es la posición del jugador; world_size activa el cálculo con wraparound.
    """
    to_delete = []
    components = world.get_components(CTransform, CVelocity, CSteering, CEnemyState)
    c_t: CTransform
    c_v: CVelocity
    c_st: CSteering
    c_es: CEnemyState
    for entity, (c_t, c_v, c_st, c_es) in components:
        if not c_es.entered:
            change_state(c_es, c_st, c_es.state)
        c_es.time_in_state += delta_time
        to_target = wrapped_delta(c_t.pos, target, world_size)

        if c_es.state == EnemyState.CHASE:
            _do_chase_state(c_es, c_st)
        elif c_es.state == EnemyState.WANDER:
            pass  # P se queda vagando hasta que lo destruyan
        elif c_es.state == EnemyState.AIM:
            _do_aim_state(c_es, c_st, c_v, to_target)
        elif c_es.state in (EnemyState.LEAVE, EnemyState.STRAIGHT):
            if _should_despawn(c_es, c_v, to_target):
                to_delete.append(entity)

    for entity in to_delete:
        world.delete_entity(entity)


def _do_chase_state(c_es: CEnemyState, c_st: CSteering) -> None:
    info = c_es.info()
    if c_es.time_in_state >= info.get("duration", float("inf")):
        change_state(c_es, c_st, EnemyState(info["next"]))


def _do_aim_state(c_es: CEnemyState, c_st: CSteering, c_v: CVelocity,
                  to_target: pygame.Vector2) -> None:
    if to_target.length_squared() > 0:
        c_v.vel = to_target.normalize() * c_st.max_speed
    change_state(c_es, c_st, EnemyState.STRAIGHT)


def _should_despawn(c_es: CEnemyState, c_v: CVelocity, to_target: pygame.Vector2) -> bool:
    """True si el enemigo ya se fue: se aleja del jugador y está lejos, o se acabó el tiempo."""
    info = c_es.info()
    if c_es.time_in_state >= info.get("duration", float("inf")):
        return True
    moving_away = c_v.vel.dot(to_target) < 0
    return moving_away and to_target.length() >= info.get("despawn_distance", float("inf"))
