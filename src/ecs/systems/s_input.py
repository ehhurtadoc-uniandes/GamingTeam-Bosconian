from typing import Callable

import esper
import pygame

from src.ecs.components.c_gamepad_binding import CGamepadBinding, GamepadSource
from src.ecs.components.c_input_command import CInputCommand, CommandPhase

KEY_EVENTS = {pygame.KEYDOWN: CommandPhase.START, pygame.KEYUP: CommandPhase.END}
BUTTON_EVENTS = {pygame.JOYBUTTONDOWN: CommandPhase.START, pygame.JOYBUTTONUP: CommandPhase.END}
GAMEPAD_EVENTS = (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP, pygame.JOYAXISMOTION, pygame.JOYHATMOTION)


def _edge_phase(pressed: bool, c_input: CInputCommand) -> CommandPhase | None:
    active = c_input.phase == CommandPhase.START
    if pressed and not active:
        return CommandPhase.START
    if not pressed and active:
        return CommandPhase.END
    return None


def gamepad_phase(c_pad: CGamepadBinding, c_input: CInputCommand, event: pygame.event.Event) -> CommandPhase | None:
    if c_pad.source == GamepadSource.BUTTON:
        if event.type in BUTTON_EVENTS and event.button == c_pad.index:
            return BUTTON_EVENTS[event.type]
    elif c_pad.source == GamepadSource.AXIS:
        if event.type == pygame.JOYAXISMOTION and event.axis == c_pad.index:
            return _edge_phase(event.value * c_pad.sign > c_pad.dead_zone, c_input)
    elif c_pad.source == GamepadSource.HAT:
        if event.type == pygame.JOYHATMOTION and event.hat == c_pad.index:
            pressed = ((c_pad.hat_x != 0 and event.value[0] == c_pad.hat_x)
                       or (c_pad.hat_y != 0 and event.value[1] == c_pad.hat_y))
            return _edge_phase(pressed, c_input)
    return None


def system_input(world: esper.World, event: pygame.event.Event,
                 do_action: Callable[[CInputCommand], None]) -> None:
    """Traduce teclas y gamepad en comandos. Es el único sistema que conoce las teclas y los botones."""
    if event.type in KEY_EVENTS:
        c_input: CInputCommand
        for _, c_input in world.get_component(CInputCommand):
            if c_input.key == event.key:
                c_input.phase = KEY_EVENTS[event.type]
                do_action(c_input)
        return
    if event.type not in GAMEPAD_EVENTS:
        return
    c_pad: CGamepadBinding
    for _, (c_input, c_pad) in world.get_components(CInputCommand, CGamepadBinding):
        phase = gamepad_phase(c_pad, c_input, event)
        if phase is not None:
            c_input.phase = phase
            do_action(c_input)
