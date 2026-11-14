from src.ecs.components.tags.c_tag_enemy import EnemyType


class CEnemySpawner:
    """Hace aparecer enemigos durante el nivel (LC-ENE-01). Hay uno por nivel.

    Sale del bloque "spawner" del JSON del nivel, así cada nivel tiene su dificultad:

    - interval: segundos entre apariciones.
    - initial_delay: segundos antes de la primera.
    - max_alive: tope de enemigos vivos a la vez; si se llega, se espera al siguiente intervalo.
    - weights: probabilidad relativa de cada tipo, p. ej. {"I": 3, "P": 2, "E": 1}.
      Un tipo con peso 0 o ausente no aparece.
    - wander_scale: cuánto se desvían los enemigos de este nivel (LC-ENE-02.1).
      1 es lo de enemies.json; menos de 1 persiguen más directo.

    Los dejará el sistema de alertas (#29):
    - active: en alerta VERDE no salen enemigos.
    - rate_multiplier: en alerta ROJA salen al doble de ritmo (2.0).
    """

    def __init__(self, spawner_info: dict) -> None:
        self.interval: float = spawner_info["interval"]
        self.time_to_spawn: float = spawner_info.get("initial_delay", self.interval)
        self.max_alive: int = spawner_info["max_alive"]
        self.weights: dict[EnemyType, float] = {
            EnemyType(name): float(weight)
            for name, weight in spawner_info["weights"].items() if weight > 0
        }
        self.wander_scale: float = spawner_info.get("wander_scale", 1.0)
        self.active = True
        self.rate_multiplier = 1.0
        if self.interval <= 0:
            raise ValueError("spawner: interval debe ser mayor que 0")
        if not self.weights:
            raise ValueError("spawner: weights necesita al menos un tipo con peso mayor que 0")
