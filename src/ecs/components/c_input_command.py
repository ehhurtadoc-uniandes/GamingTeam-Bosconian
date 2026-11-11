from enum import Enum


class CommandPhase(Enum):
    NA = 0
    START = 1
    END = 2


class CInputCommand:
    """Comando de entrada (patrón Command): asocia una tecla con un nombre de acción."""

    def __init__(self, name: str, key: int) -> None:
        self.name = name
        self.key = key
        self.phase = CommandPhase.NA
