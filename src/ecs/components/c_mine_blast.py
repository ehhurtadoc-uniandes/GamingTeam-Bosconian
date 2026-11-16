class CMineBlast:
    """Explosión de una mina: mientras dura, todo lo que esté a menos de radius muere."""

    def __init__(self, radius: float) -> None:
        self.radius = radius
