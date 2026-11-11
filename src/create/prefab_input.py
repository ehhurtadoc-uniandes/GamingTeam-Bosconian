"""Creación de las entidades de entrada del motor."""
import esper
import pygame

from src.ecs.components.c_input_command import CInputCommand


def create_input(world: esper.World, input_info: dict) -> None:
    """Crea un comando por cada tecla de assets/cfg/input.json.

    input_info asocia cada nombre de acción con una lista de nombres de tecla de pygame,
    así una acción puede tener varias teclas.
    """
    for name, keys in input_info.items():
        # Un string suelto se iteraría letra por letra y mapearía teclas equivocadas sin error.
        if not isinstance(keys, list):
            raise ValueError(f"input.json: {name} debe ser una lista de teclas")
        for key in keys:
            try:
                key_code = pygame.key.key_code(key)
            except ValueError as error:
                raise ValueError(f"input.json: tecla desconocida '{key}' en {name}") from error
            world.create_entity(CInputCommand(name, key_code))
