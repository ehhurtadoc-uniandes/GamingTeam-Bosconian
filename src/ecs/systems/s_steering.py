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
from src.utils.wrap import wrapped_delta  


def truncate(vector: pygame.Vector2, max_length: float) -> pygame.Vector2:
    """Devuelve una copia del vector con longitud máxima max_length."""
    result = pygame.Vector2(vector)
    if result.length_squared() > max_length * max_length:
        result.scale_to_length(max_length)
    return result


def seek(to_target: pygame.Vector2, velocity: pygame.Vector2, max_speed: float) -> pygame.Vector2:
    """Fuerza para girar hacia el objetivo a velocidad máxima."""
    if to_target.length_squared() == 0:
        return pygame.Vector2(0, 0)
    desired = to_target.normalize() * max_speed
    return desired - velocity


def flee(to_target: pygame.Vector2, velocity: pygame.Vector2, max_speed: float) -> pygame.Vector2:
    """Fuerza para alejarse del objetivo a velocidad máxima (opuesto de seek)."""
    if to_target.length_squared() == 0:
        return pygame.Vector2(0, 0)
    desired = -to_target.normalize() * max_speed
    return desired - velocity


def wander(velocity: pygame.Vector2, wander_angle: float, max_speed: float) -> pygame.Vector2:
    """Fuerza lateral que desvía al enemigo según wander_angle.

    Si está quieto no hay dirección que desviar: usa wander_angle como rumbo
    para que un enemigo que solo vaga (P en WANDER) arranque igual.
    """
    if velocity.length_squared() == 0:
        return pygame.Vector2(1, 0).rotate_rad(wander_angle) * max_speed
    return velocity.normalize().rotate_rad(wander_angle) * max_speed - velocity


def steering_force(c_st: CSteering, position: pygame.Vector2, velocity: pygame.Vector2,
                   target: pygame.Vector2, world_size: pygame.Vector2 | None = None,
                   limit: bool = True) -> pygame.Vector2:
    """Combina seek, flee y wander según los pesos del componente.

    Con limit=True la fuerza se limita a max_force.
    """
    to_target = wrapped_delta(position, target, world_size)
    force = seek(to_target, velocity, c_st.max_speed) * c_st.seek_weight
    if c_st.flee_weight > 0:
        force += flee(to_target, velocity, c_st.max_speed) * c_st.flee_weight
    if c_st.wander_strength > 0:
        force += wander(velocity, c_st.wander_angle, c_st.max_speed) * c_st.wander_strength
    return truncate(force, c_st.max_force) if limit else force


def turn_towards(velocity: pygame.Vector2, desired: pygame.Vector2, max_turn_rad: float,
                 speed: float) -> pygame.Vector2:
    """Gira velocity hacia desired como máximo max_turn_rad y la deja con rapidez speed.

    Se usa con constant_speed: la rapidez no cambia, solo el rumbo. Si desired
    queda justo detrás, gira igual (no se queda trabado a 180°).
    """
    if desired.length_squared() == 0:
        return pygame.Vector2(velocity)
    if velocity.length_squared() == 0:
        return desired.normalize() * speed
    angle = velocity.angle_to(desired)  # grados, puede salir fuera de (-180, 180]
    angle = (angle + 180) % 360 - 180
    max_turn_deg = math.degrees(max_turn_rad)
    angle = max(-max_turn_deg, min(max_turn_deg, angle))
    return velocity.rotate(angle).normalize() * speed


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
        if c_st.constant_speed:
            # La rapidez es fija, así que la fuerza solo sirve para girar. Con un
            # simple reescalado, la parte de la fuerza paralela a la velocidad se
            # perdía y el enemigo giraba a ~1 rad/s sin importar max_force: pasaba
            # de largo al jugador y daba vueltas enormes. Aquí la tasa de giro es
            # max_force / max_speed (rad/s), la de un giro a aceleración max_force.
            force = steering_force(c_st, c_t.pos, c_v.vel, target, world_size, limit=False)
            c_st.last_force = truncate(force, c_st.max_force)
            max_turn = c_st.max_force / c_st.max_speed * delta_time if c_st.max_speed > 0 else 0.0
            c_v.vel = turn_towards(c_v.vel, c_v.vel + force, max_turn, c_st.max_speed)
        else:
            force = steering_force(c_st, c_t.pos, c_v.vel, target, world_size)
            c_st.last_force = force
            c_v.vel = truncate(c_v.vel + force * delta_time, c_st.max_speed)
