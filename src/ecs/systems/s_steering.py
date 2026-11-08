"""Steering behaviours de los enemigos (LC-ENE-02).

Las funciones de cálculo son puras (no usan esper ni pantalla) para poder
probarlas aisladas y reutilizarlas en los estados de los enemigos I, P y E.
"""
import math
import random

import esper
import pygame

from src.ecs.components.c_steering import CSteering
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity


def truncate(vector: pygame.Vector2, max_length: float) -> pygame.Vector2:
    """Devuelve una copia del vector con longitud máxima max_length."""
    result = pygame.Vector2(vector)
    if result.length_squared() > max_length * max_length:
        result.scale_to_length(max_length)
    return result


def wrapped_delta(origin: pygame.Vector2, target: pygame.Vector2,
                  world_size: pygame.Vector2 | None = None) -> pygame.Vector2:
    """Vector de origin a target.

    Si se da world_size, el mundo se trata como toroidal (wraparound, RF-06) y
    se devuelve el camino más corto, que puede cruzar un borde.
    """
    delta = target - origin
    if world_size is not None:
        if abs(delta.x) > world_size.x / 2:
            delta.x -= math.copysign(world_size.x, delta.x)
        if abs(delta.y) > world_size.y / 2:
            delta.y -= math.copysign(world_size.y, delta.y)
    return delta


def seek(to_target: pygame.Vector2, velocity: pygame.Vector2, max_speed: float) -> pygame.Vector2:
    """Fuerza para girar hacia el objetivo a velocidad máxima."""
    if to_target.length_squared() == 0:
        return pygame.Vector2(0, 0)
    desired = to_target.normalize() * max_speed
    return desired - velocity


def wander(velocity: pygame.Vector2, wander_angle: float, max_speed: float) -> pygame.Vector2:
    """Fuerza lateral que desvía al enemigo según wander_angle."""
    if velocity.length_squared() == 0:
        return pygame.Vector2(0, 0)
    return velocity.normalize().rotate_rad(wander_angle) * max_speed - velocity


def steering_force(c_st: CSteering, position: pygame.Vector2, velocity: pygame.Vector2,
                   target: pygame.Vector2, world_size: pygame.Vector2 | None = None) -> pygame.Vector2:
    """Combina seek y wander según los pesos del componente y limita a max_force."""
    to_target = wrapped_delta(position, target, world_size)
    force = seek(to_target, velocity, c_st.max_speed) * c_st.seek_weight
    if c_st.wander_strength > 0:
        force += wander(velocity, c_st.wander_angle, c_st.max_speed) * c_st.wander_strength
    return truncate(force, c_st.max_force)


def system_steering(world: esper.World, delta_time: float, target: pygame.Vector2,
                    world_size: pygame.Vector2 | None = None,
                    rng: random.Random | None = None) -> None:
    """Aplica steering a todas las entidades con CSteering para perseguir target.

    No mueve la posición: eso lo hace el sistema de movimiento con CVelocity.
    """
    rng = rng or random
    components = world.get_components(CTransform, CVelocity, CSteering)
    c_t: CTransform
    c_v: CVelocity
    c_st: CSteering
    for _, (c_t, c_v, c_st) in components:
        if c_st.wander_rate > 0:
            c_st.wander_angle += rng.uniform(-1.0, 1.0) * c_st.wander_rate * delta_time
            c_st.wander_angle = max(-math.pi / 2, min(math.pi / 2, c_st.wander_angle))
        force = steering_force(c_st, c_t.pos, c_v.vel, target, world_size)
        c_st.last_force = force
        c_v.vel = truncate(c_v.vel + force * delta_time, c_st.max_speed)
