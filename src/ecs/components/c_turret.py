from enum import Enum

import pygame


class TurretState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"


class CTurret:
    """Estado de una torreta de base (LC-BAS-05).

    - activation_distance: se abre si el jugador está más cerca que esto.
    - fire_interval: segundos entre disparos de ESTA torreta (cada una tiene el suyo).
    - time_to_fire: lo que falta para el próximo disparo; arranca con un desfase
      al azar para que las torretas de una base no disparen a la vez. Solo corre
      mientras la torreta está abierta.
    - closed_surf / open_surf: aspecto en cada estado; system_turret cambia el
      CSurface de la torreta al abrirse y al cerrarse.
    """

    def __init__(self, activation_distance: float, fire_interval: float, time_to_fire: float,
                 closed_surf: pygame.Surface, open_surf: pygame.Surface) -> None:
        self.state = TurretState.CLOSED
        self.activation_distance = activation_distance
        self.fire_interval = fire_interval
        self.time_to_fire = time_to_fire
        self.closed_surf = closed_surf
        self.open_surf = open_surf
