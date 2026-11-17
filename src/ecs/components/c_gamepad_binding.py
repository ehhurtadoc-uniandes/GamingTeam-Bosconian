from enum import Enum


class GamepadSource(Enum):
    BUTTON = "BUTTON"
    AXIS = "AXIS"
    HAT = "HAT"


class CGamepadBinding:
    def __init__(self, source: GamepadSource, index: int, sign: int = 0, hat_x: int = 0,
                 hat_y: int = 0, dead_zone: float = 0.5) -> None:
        self.source = source
        self.index = index
        self.sign = sign
        self.hat_x = hat_x
        self.hat_y = hat_y
        self.dead_zone = dead_zone
