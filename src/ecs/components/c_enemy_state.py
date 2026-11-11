from enum import Enum


class EnemyState(Enum):
    """Estados de la IA de los enemigos (patrón State, OBJ-08).

    - CHASE: persigue al jugador (I y P).
    - LEAVE: huye del jugador y desaparece al alejarse (I).
    - WANDER: se mueve al azar sin perseguir (P).
    - AIM: apunta al jugador una sola vez (E). Dura un frame.
    - STRAIGHT: va recto sin desviarse y desaparece al alejarse (E).
    """
    CHASE = "CHASE"
    LEAVE = "LEAVE"
    WANDER = "WANDER"
    AIM = "AIM"
    STRAIGHT = "STRAIGHT"


# Atributos de CSteering que cada estado puede sobrescribir al entrar.
STEERING_OVERRIDES = ("seek_weight", "flee_weight", "wander_strength", "max_force")


class CEnemyState:
    """Estado actual de la IA de un enemigo.

    - base_steering: valores de steering del tipo; al entrar a un estado se
      restauran y luego se aplican los del estado (ver STEERING_OVERRIDES).
    - states_info: configuración de cada estado (sale de enemies.json).
    - time_in_state: segundos desde que entró al estado actual.
    """

    def __init__(self, initial_state: EnemyState, base_steering: dict, states_info: dict) -> None:
        self.state = initial_state
        self.base_steering = dict(base_steering)
        self.states_info = states_info
        self.time_in_state = 0.0
        self.entered = False  # False hasta que el sistema aplique el estado inicial

    def info(self, state: EnemyState | None = None) -> dict:
        """Configuración del estado dado (o del actual)."""
        return self.states_info.get((state or self.state).value, {})
