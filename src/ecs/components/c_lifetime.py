class CLifetime:
    """Segundos que le quedan a una entidad efímera (p. ej. una bala) antes de borrarse."""

    def __init__(self, remaining: float) -> None:
        self.remaining = remaining
