"""Creación de las entidades de entrada del motor."""
import esper
import pygame

from src.ecs.components.c_gamepad_binding import CGamepadBinding, GamepadSource
from src.ecs.components.c_input_command import CInputCommand


def create_input(world: esper.World, input_info: dict, gamepad_info: dict | None = None) -> None:
    """Crea un comando por cada tecla de assets/cfg/input.json.

    input_info asocia cada nombre de acción con una lista de nombres de tecla de pygame,
    así una acción puede tener varias teclas. Con gamepad_info (assets/cfg/gamepad.json)
    también crea los comandos del gamepad, con los mismos nombres de acción.
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
    if gamepad_info is not None:
        create_gamepad_input(world, gamepad_info)


def create_gamepad_input(world: esper.World, gamepad_info: dict) -> None:
    """Crea un comando por cada botón, eje y cruceta de gamepad.json.

    Cada comando lleva una "tecla" negativa única, para que una escena distinga de dónde
    viene cada acción (por ejemplo, flecha derecha y stick a la derecha a la vez).
    """
    dead_zone = gamepad_info["dead_zone"]
    next_key = -1

    def add(name: str, binding: CGamepadBinding) -> None:
        nonlocal next_key
        world.create_entity(CInputCommand(name, next_key), binding)
        next_key -= 1

    for name, buttons in gamepad_info.get("buttons", {}).items():
        for button in buttons:
            add(name, CGamepadBinding(GamepadSource.BUTTON, button))
    for name, axes in gamepad_info.get("axes", {}).items():
        for axis_info in axes:
            if axis_info["sign"] not in (-1, 1):
                raise ValueError(f"gamepad.json: sign de {name} debe ser -1 o 1")
            add(name, CGamepadBinding(GamepadSource.AXIS, axis_info["axis"], sign=axis_info["sign"],
                                      dead_zone=dead_zone))
    for name, hats in gamepad_info.get("hats", {}).items():
        for hat_info in hats:
            hat_x, hat_y = hat_info.get("x", 0), hat_info.get("y", 0)
            if hat_x == 0 and hat_y == 0:
                raise ValueError(f"gamepad.json: la cruceta de {name} necesita x o y distinto de cero")
            add(name, CGamepadBinding(GamepadSource.HAT, hat_info["hat"], hat_x=hat_x, hat_y=hat_y))
