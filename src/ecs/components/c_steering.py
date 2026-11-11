import pygame


class CSteering:
    """Parámetros de steering de un enemigo.

    La velocidad del enemigo cambia por fuerzas (aceleración) en lugar de fijarse
    directamente, así que gira de forma progresiva en vez de apuntar de golpe.

    - max_speed: velocidad máxima (px/s). Debe ser un poco mayor que la del jugador (LC-ENE-02.2).
    - max_force: aceleración máxima (px/s²). Valores bajos giran más abierto.
    - seek_weight: peso de la persecución.
    - flee_weight: peso de la huida (tipo I al irse).
    - wander_strength: peso del desvío aleatorio. Más alto = se desvía más (LC-ENE-02.1).
    - wander_rate: qué tan rápido cambia el desvío (rad/s).
    - constant_speed: si es True, el steering solo cambia la dirección y la rapidez
      se mantiene en max_speed, para que nunca sea menor que la del jugador (LC-ENE-02.2).
    """

    def __init__(self, steering_info: dict) -> None:
        self.max_speed: float = steering_info["max_speed"]
        self.max_force: float = steering_info["max_force"]
        self.seek_weight: float = steering_info.get("seek_weight", 1.0)
        self.flee_weight: float = steering_info.get("flee_weight", 0.0)
        self.wander_strength: float = steering_info.get("wander_strength", 0.0)
        self.wander_rate: float = steering_info.get("wander_rate", 0.0)
        self.constant_speed: bool = steering_info.get("constant_speed", False)
        self.wander_angle: float = 0.0
        self.last_force = pygame.Vector2(0, 0)
