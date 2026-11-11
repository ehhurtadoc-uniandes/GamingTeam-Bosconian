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
        for key in keys:
            world.create_entity(CInputCommand(name, pygame.key.key_code(key)))
