from typing import Callable

import esper
import pygame

from src.ecs.components.c_input_command import CInputCommand, CommandPhase


def system_input(world: esper.World, event: pygame.event.Event,
                 do_action: Callable[[CInputCommand], None]) -> None:
    """Traduce las teclas en comandos. Es el único sistema que conoce las teclas."""
    if event.type == pygame.KEYDOWN:
        phase = CommandPhase.START
    elif event.type == pygame.KEYUP:
        phase = CommandPhase.END
    else:
        return
    c_input: CInputCommand
    for _, c_input in world.get_component(CInputCommand):
        if c_input.key == event.key:
            c_input.phase = phase
            do_action(c_input)
