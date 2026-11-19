from enum import Enum

import pygame


class CoreMode(Enum):
    """Comportamiento del núcleo en un nivel (bloque "core" del JSON del nivel, #27).

    - STATIC: siempre abierto y nunca lanza enemigos (LC-BAS-06.1).
    - CYCLING: se abre y se cierra; cada vez que termina de abrirse lanza un E (LC-BAS-06).
    """
    STATIC = "static"
    CYCLING = "cycling"


class CoreState(Enum):
    """Estados del núcleo. El valor es la clave que usa base.json en core.durations y core.states."""
    CLOSED = "closed"
    OPENING = "opening"
    OPEN = "open"
    CLOSING = "closing"


# Orden del ciclo en modo CYCLING.
NEXT_CORE_STATE = {
    CoreState.CLOSED: CoreState.OPENING,
    CoreState.OPENING: CoreState.OPEN,
    CoreState.OPEN: CoreState.CLOSING,
    CoreState.CLOSING: CoreState.CLOSED,
}


class CBaseCore:
    """Estado del núcleo de una base (LC-BAS-06, #27).

    - base: entidad de la base (la que lleva CBase). Si la base ya no existe o su
      CBase.core no apunta a este núcleo, system_base_core deja de actualizarlo.
    - mode: CoreMode del nivel.
    - state / time_in_state: estado actual y segundos que lleva en él.
    - durations: segundos de cada estado (solo se usan en CYCLING).
    - surfaces: aspecto de cada estado, ya rotado según la orientación de la base.
    - wander_scale: se pasa a create_enemy al lanzar el E (spawner.wander_scale del nivel).
    """

    def __init__(self, base: int, mode: CoreMode, state: CoreState,
                 durations: dict[CoreState, float], surfaces: dict[CoreState, pygame.Surface],
                 wander_scale: float = 1.0) -> None:
        self.base = base
        self.mode = mode
        self.state = state
        self.time_in_state = 0.0
        self.durations = durations
        self.surfaces = surfaces
        self.wander_scale = wander_scale
