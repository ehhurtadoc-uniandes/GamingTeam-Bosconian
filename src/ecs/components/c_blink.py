class CBlink:
    """Hace que la entidad aparezca y desaparezca cada interval segundos."""

    def __init__(self, interval: float) -> None:
        self.interval = interval
        self.time = 0.0
        self.visible = True
