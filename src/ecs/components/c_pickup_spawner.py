class CPickupSpawner:
    def __init__(self, interval: float, chance: float) -> None:
        self.interval = interval
        self.chance = chance
        self.timer = interval
