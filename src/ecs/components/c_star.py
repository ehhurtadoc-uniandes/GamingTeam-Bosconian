class CStar:
    """Una estrella del fondo.

    parallax: qué fracción del movimiento de la cámara sigue (0.5 = la mitad, se ve más lejos).
    visible y time_left: el parpadeo; cuando time_left llega a 0 se prende o se apaga.
    """

    def __init__(self, parallax: float, time_left: float, visible: bool = True) -> None:
        self.parallax = parallax
        self.time_left = time_left
        self.visible = visible
