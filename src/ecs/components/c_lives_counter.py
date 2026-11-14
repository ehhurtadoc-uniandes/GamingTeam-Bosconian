class CLivesCounter:
    """Texto con el total de vidas; solo se muestra si hay más de max_visible (LC-VID-03)."""

    def __init__(self, max_visible: int) -> None:
        self.max_visible = max_visible
