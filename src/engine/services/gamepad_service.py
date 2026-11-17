import pygame

INPUT_EVENTS = (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP, pygame.JOYAXISMOTION, pygame.JOYHATMOTION)


class GamepadService:
    """Abre los mandos conectados y elige uno activo.

    Solo el mando activo controla el juego: si dos mandos compartieran los comandos, el stick
    en reposo de uno soltaría las direcciones que el otro mantiene. El activo es el primero que
    se conectó; si se desconecta, pasa a ser activo otro de los que quedan.
    """

    def __init__(self) -> None:
        self._joysticks: dict[int, pygame.joystick.JoystickType] = {}
        self._active: int | None = None

    @property
    def count(self) -> int:
        return len(self._joysticks)

    @property
    def active(self) -> int | None:
        return self._active

    def open_connected(self) -> None:
        pygame.joystick.init()
        for device_index in range(pygame.joystick.get_count()):
            self._add(device_index)

    def accepts(self, event: pygame.event.Event) -> bool:
        """Indica si la escena debe recibir el evento.

        Descarta la entrada y la desconexión de los mandos que no son el activo. Se consulta
        antes de handle_event, para que una desconexión se compare con el activo de ese momento.
        """
        if event.type in INPUT_EVENTS or event.type == pygame.JOYDEVICEREMOVED:
            return self._active is None or event.instance_id == self._active
        return True

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.JOYDEVICEADDED:
            self._add(event.device_index)
        elif event.type == pygame.JOYDEVICEREMOVED:
            self._joysticks.pop(event.instance_id, None)
            if event.instance_id == self._active:
                self._active = next(iter(self._joysticks), None)

    def clear(self) -> None:
        self._joysticks.clear()
        self._active = None

    def _add(self, device_index: int) -> None:
        try:
            joystick = pygame.joystick.Joystick(device_index)
        except pygame.error:
            return
        instance_id = joystick.get_instance_id()
        self._joysticks[instance_id] = joystick
        if self._active is None:
            self._active = instance_id
