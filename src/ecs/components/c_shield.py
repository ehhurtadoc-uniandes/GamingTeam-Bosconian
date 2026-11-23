class CShield:
    def __init__(self, duration: float, aura: int) -> None:
        self.remaining = duration
        self.elapsed = 0.0
        self.aura = aura
