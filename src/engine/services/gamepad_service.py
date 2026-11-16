import pygame


class GamepadService:
    def __init__(self) -> None:
        self._joysticks: dict[int, pygame.joystick.JoystickType] = {}

    @property
    def count(self) -> int:
        return len(self._joysticks)

    def open_connected(self) -> None:
        pygame.joystick.init()
        for device_index in range(pygame.joystick.get_count()):
            self._add(device_index)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.JOYDEVICEADDED:
            self._add(event.device_index)
        elif event.type == pygame.JOYDEVICEREMOVED:
            self._joysticks.pop(event.instance_id, None)

    def clear(self) -> None:
        self._joysticks.clear()

    def _add(self, device_index: int) -> None:
        try:
            joystick = pygame.joystick.Joystick(device_index)
        except pygame.error:
            return
        self._joysticks[joystick.get_instance_id()] = joystick
