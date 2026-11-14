"""Creación del spawner de enemigos del nivel (#28)."""
import esper

from src.ecs.components.c_enemy_spawner import CEnemySpawner


def create_enemy_spawner(world: esper.World, level_info: dict) -> int | None:
    """Crea el spawner a partir del bloque "spawner" del nivel.

    Un nivel sin ese bloque no tiene spawner (p. ej. un nivel de prueba o el nivel jefe).
    Devuelve la entidad o None.
    """
    spawner_info = level_info.get("spawner")
    if spawner_info is None:
        return None
    entity = world.create_entity()
    world.add_component(entity, CEnemySpawner(spawner_info))
    return entity
