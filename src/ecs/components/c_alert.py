from enum import Enum


class AlertState(Enum):
    """Condición de alerta del nivel (#29). El valor es la clave que usa alerts.json en sounds y hud.states.

    - GREEN: no salen enemigos del spawner ni de los núcleos (LC-ALE-02).
    - YELLOW: el spawner y los núcleos funcionan según el nivel (LC-ALE-03).
    - RED: enemigos más rápidos y apariciones más seguidas; ya no baja (LC-ALE-04).
    """
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class AlertSettings:
    """Tiempos (segundos de juego) y multiplicadores de la alerta, ya validados.

    Salen de assets/cfg/alerts.json y del bloque "alert" opcional del nivel (ver prefab_alert).
    """

    def __init__(self, green_duration: float, base_destroyed_green_duration: float, red_after: float,
                 red_speed_multiplier: float, red_rate_multiplier: float) -> None:
        self.green_duration = green_duration
        self.base_destroyed_green_duration = base_destroyed_green_duration
        self.red_after = red_after
        self.red_speed_multiplier = red_speed_multiplier
        self.red_rate_multiplier = red_rate_multiplier


class CAlert:
    """Alerta del nivel (#29). Hay una por nivel; la crea PlayScene al crear el nivel.

    - state: AlertState actual. Empieza en GREEN.
    - time_in_state: segundos de juego en el estado actual.
    - total_time: segundos de juego del nivel. No se detiene en el VERDE temporal.
    - temporary_green: True si el VERDE actual es el de una base destruida (dura
      base_destroyed_green_duration); False si es el VERDE inicial (dura green_duration).
    - bases_destroyed: destrucciones registradas por destroy_base que system_alert aún no
      procesó. Al recrear el nivel se crea una alerta nueva, así que los pendientes se descartan.
    - sounds: ruta del sonido de cada estado, que suena al llegar a él.
    """

    def __init__(self, settings: AlertSettings, sounds: dict[AlertState, str]) -> None:
        self.settings = settings
        self.sounds = sounds
        self.state = AlertState.GREEN
        self.time_in_state = 0.0
        self.total_time = 0.0
        self.temporary_green = False
        self.bases_destroyed = 0
